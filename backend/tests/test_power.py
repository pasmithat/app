import os
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import power_engine as pe  # noqa: E402

S = dict(pe.DEFAULT_SETTINGS)


def _api():
    env = Path(__file__).resolve().parents[2] / "frontend" / ".env"
    for line in env.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip() + "/api/power"
    raise RuntimeError("REACT_APP_BACKEND_URL missing")


API = os.environ.get("POWER_API") or _api()


@pytest.fixture(scope="module")
def ds():
    return pe.load_dataset()


class TestFormulas:
    def test_demand(self):
        assert pe.total_demand_kw(10, 2.5) == 25

    def test_energy(self):
        assert pe.energy_kwh(25, 8) == 200

    def test_cost(self):
        assert pe.cost_inr(200, 8) == 1600

    def test_utilization(self):
        assert pe.utilization_pct(85, 100) == 85
        with pytest.raises(ValueError):
            pe.utilization_pct(10, 0)

    @pytest.mark.parametrize("u,sev", [(69.9, "normal"), (70, "moderate"), (84.9, "moderate"), (85, "high"),
                                       (100, "high"), (100.1, "exceeded")])
    def test_severity_bands(self, u, sev):
        assert pe.severity(u, S) == sev

    def test_configurable_thresholds(self):
        assert pe.severity(65, {**S, "moderate_pct": 60}) == "moderate"
        with pytest.raises(ValueError):
            pe.validate_settings({**S, "moderate_pct": 90})


class TestData:
    def test_chennai_only(self, ds):
        assert {r["zone_name"] for r in ds.records} == set(pe.CHENNAI_ZONES)
        assert any("outside the Chennai" in r["reason"] for r in ds.rejected)

    def test_invalid_rows_rejected(self, ds):
        reasons = " ".join(r["reason"] for r in ds.rejected)
        assert "negative" in reasons and "missing" in reasons

    def test_all_simulated_labelled(self, ds):
        assert {r["data_source"] for r in ds.records} == {"SIMULATED"}

    @pytest.mark.parametrize("field,val,msg", [("current_demand_kw", "", "missing"), ("current_demand_kw", "abc", "non-numeric"),
                                               ("available_capacity_kw", "0", "> 0"), ("zone_name", "Mumbai", "outside"),
                                               ("latitude", "19.07", "outside Chennai")])
    def test_parse_row_invalid(self, ds, field, val, msg):
        row = {k: str(v) for k, v in ds.records[0].items() if k != "ts"}
        row[field] = val
        rec, err = pe.parse_row(row)
        assert rec is None and msg in err

    def test_missing_coordinates_allowed(self, ds):
        snaps = pe.all_snapshots(ds, S)
        assert [s["building_id"] for s in snaps if s["latitude"] is None] == ["CHN-SHO-02"]


class TestDetection:
    def test_overload(self, ds):
        al = pe.overload_alerts(pe.all_snapshots(ds, S), S)
        sev = {a["building_id"]: a["severity"] for a in al}
        assert sev["CHN-ADY-01"] == "exceeded" and sev["CHN-TNG-01"] == "high" and sev["CHN-AMB-02"] == "moderate"
        assert all("fault" in a["note"] for a in al)

    def test_abnormal_rules(self, ds):
        rules = {(a["building_id"], a["rule"]) for a in pe.abnormal_alerts(ds, pe.all_snapshots(ds, S))}
        for expected in [("CHN-GND-01", "after_hours"), ("CHN-VEL-01", "unoccupied_high"),
                         ("CHN-ADY-01", "unexpected_increase"), ("CHN-PRG-01", "continuous_operation"),
                         ("CHN-ANN-01", "unusual_daily_pattern")]:
            assert expected in rules

    def test_24h_buildings_not_flagged_continuous(self, ds):
        rules = {(a["building_id"], a["rule"]) for a in pe.abnormal_alerts(ds, pe.all_snapshots(ds, S))}
        assert ("CHN-ADY-01", "continuous_operation") not in rules

    def test_sensor_override(self, ds):
        sensor = {"timestamp": "2099-01-01T10:00:00+05:30", "current_demand_kw": 10.0, "ac_units_operating": 3}
        snap = [s for s in pe.all_snapshots(ds, S, {"CHN-TNG-02": sensor}) if s["building_id"] == "CHN-TNG-02"][0]
        assert snap["data_source"] == "IOT_SENSOR" and snap["current_demand_kw"] == 10.0


class TestSimulation:
    BASE = {"outdoor_temp_c": 35, "ac_units": 100, "ac_power_rating_kw": 2.0, "operating_hours": 10,
            "occupied_buildings": 3, "tariff_inr_per_kwh": 8, "available_capacity_kw": 250}

    def test_math(self):
        r = pe.simulate(self.BASE, {"ac_units": 150}, S)
        assert r["baseline"]["demand_kw"] == 200 and r["simulated"]["demand_kw"] == 300
        assert r["simulated"]["energy_kwh"] == 3000 and r["simulated"]["cost_inr"] == 24000
        assert r["comparison"]["demand_change_pct"] == 50 and r["comparison"]["cost_difference_inr"] == 8000
        assert r["simulated"]["utilization_pct"] == 120 and r["overload_warning"]

    def test_temperature_ignored_without_assumption(self):
        r = pe.simulate(self.BASE, {"outdoor_temp_c": 45}, S)
        assert r["simulated"]["demand_kw"] == r["baseline"]["demand_kw"]

    def test_temperature_with_assumption(self):
        t = {"enabled": True, "demand_change_pct_per_c": 3, "reference_temp_c": 35}
        assert pe.simulate(self.BASE, {"outdoor_temp_c": 45}, S, t)["simulated"]["demand_kw"] == 260

    def test_baseline_integrity(self, ds):
        fp = ds.fingerprint
        snaps = pe.all_snapshots(ds, S)
        base = pe.baseline_inputs(snaps, S)
        copy = dict(base)
        pe.simulate(base, {"ac_units": 99999, "operating_hours": 24}, S)
        pe.scenarios(base, S)
        assert base == copy and ds.compute_fingerprint() == fp

    def test_scenarios(self, ds):
        sc = {s["key"]: s for s in pe.scenarios(pe.baseline_inputs(pe.all_snapshots(ds, S), S), S)}
        assert sc["normal"]["comparison"]["demand_change_kw"] == 0
        assert sc["increased_ac_demand"]["comparison"]["demand_change_kw"] > 0
        assert sc["reduced_operating_hours"]["comparison"]["energy_change_kwh"] < 0
        assert sc["energy_optimization"]["comparison"]["cost_difference_inr"] < 0
        assert sc["high_outdoor_temperature"]["comparison"]["demand_change_kw"] > 0

    def test_recommendations_explained(self, ds):
        recs = pe.recommendations(ds, pe.all_snapshots(ds, S), S)
        assert recs and all(r["why"] and r["requires_human_approval"] and not r["automatic_control"] for r in recs)
        assert {"adjust_schedule", "reduce_unoccupied", "review_capacity", "efficient_equipment",
                "optimize_occupancy"} <= {r["type"] for r in recs}


class TestAPI:
    def test_overview(self):
        d = requests.get(f"{API}/overview").json()
        assert d["kpis"]["monitored_buildings"] == 30 and d["data_quality"]["rows_rejected"] == 3

    def test_zones(self):
        z = requests.get(f"{API}/zones").json()["zones"]
        assert [x["zone_name"] for x in z] == list(pe.CHENNAI_ZONES)

    def test_zone_filter_and_invalid_zone(self):
        b = requests.get(f"{API}/buildings", params={"zone": "Adyar"}).json()["buildings"]
        assert b and all(x["zone_name"] == "Adyar" for x in b)
        r = requests.get(f"{API}/buildings", params={"zone": "Bengaluru"})
        assert r.status_code == 400 and "Chennai" in r.json()["detail"]

    def test_unknown_building(self):
        assert requests.get(f"{API}/alerts", params={"building_id": "NOPE"}).status_code == 404

    def test_alerts_and_history(self):
        a = requests.get(f"{API}/alerts").json()
        assert a["overload"] and a["abnormal"] and a["detection_method"] == "rule-based"
        h = requests.get(f"{API}/history", params={"hours": 48}).json()["series"]
        assert len(h) == 48
        assert requests.get(f"{API}/history", params={"hours": 500}).status_code == 422

    def test_simulate_and_validation(self):
        r = requests.post(f"{API}/simulate", json={"zone": "Guindy", "overrides": {"operating_hours": 5}}).json()
        assert r["baseline_unchanged"] and r["simulated"]["inputs"]["operating_hours"] == 5
        bad = requests.post(f"{API}/simulate", json={"overrides": {"operating_hours": 30, "ac_power_rating_kw": -1}})
        assert bad.status_code == 422 and "operating_hours" in bad.json()["detail"]
        assert requests.post(f"{API}/simulate", json={"overrides": {"occupied_buildings": 999}}).status_code == 422
        assert requests.post(f"{API}/simulate", json={"overrides": {"foo": 1}}).status_code == 422

    def test_recommendations(self):
        r = requests.post(f"{API}/recommendations", json={"zone": "Perungudi"}).json()
        assert r["recommendations"] and all(x["zone_name"] == "Perungudi" for x in r["recommendations"])

    def test_thresholds_validation(self):
        r = requests.put(f"{API}/thresholds", json={"moderate_pct": 90, "high_pct": 85, "exceeded_pct": 100,
                                                    "tariff_inr_per_kwh": 8})
        assert r.status_code == 422

    def test_sensor_validation(self):
        r = requests.post(f"{API}/sensor-readings", json={"building_id": "CHN-TNG-02", "timestamp": "bad",
                                                          "current_demand_kw": -5, "ac_units_operating": 1,
                                                          "device_id": "x"})
        assert r.status_code == 422
