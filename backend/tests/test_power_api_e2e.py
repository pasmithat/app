# E2E API regression tests for Power Monitoring (PART 22) against public URL
import os
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/power"
DEFAULTS = {"moderate_pct": 70, "high_pct": 85, "exceeded_pct": 100, "tariff_inr_per_kwh": 8}


def _env(key):
    with open("/app/backend/.env") as fh:
        for line in fh:
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"')


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(_env("MONGO_URL"))
    yield c[_env("DB_NAME")]
    c.close()


# --- Read endpoints ---
class TestRead:
    def test_overview(self, s):
        r = s.get(f"{API}/overview")
        assert r.status_code == 200
        d = r.json()
        k = d["kpis"]
        for key in ["current_demand_kw", "total_energy_kwh", "estimated_cost_inr", "monitored_buildings",
                    "operating_ac_units", "capacity_utilization_pct", "overload_alerts", "abnormal_alerts"]:
            assert key in k
        assert abs(k["estimated_cost_inr"] - k["total_energy_kwh"] * d["settings"]["tariff_inr_per_kwh"]) < 1
        assert len(d["data_quality"]["buildings_without_coordinates"]) == 1
        assert d["data_source_summary"].get("SIMULATED", 0) == k["monitored_buildings"]

    def test_zones(self, s):
        z = s.get(f"{API}/zones").json()["zones"]
        assert len(z) == 10
        assert {x["zone_name"] for x in z} >= {"Adyar", "T. Nagar", "Porur"}

    def test_zone_filter(self, s):
        d = s.get(f"{API}/buildings", params={"zone": "Adyar"}).json()
        assert d["count"] > 0 and all(b["zone_name"] == "Adyar" for b in d["buildings"])

    def test_invalid_zone(self, s):
        r = s.get(f"{API}/overview", params={"zone": "Bengaluru"})
        assert r.status_code == 400 and "Chennai" in r.json()["detail"]

    def test_unknown_building(self, s):
        r = s.get(f"{API}/buildings", params={"building_id": "CHN-XXX-99"})
        assert r.status_code == 404

    def test_alerts_expected(self, s):
        d = s.get(f"{API}/alerts").json()
        sev = {a["building_id"]: a["severity"] for a in d["overload"]}
        assert sev.get("CHN-ADY-01") == "exceeded"
        assert sev.get("CHN-TNG-01") == "high"
        assert sev.get("CHN-AMB-02") == "moderate"
        assert sev.get("CHN-ANN-01") == "moderate"
        rules = {(a["building_id"], a["rule"]) for a in d["abnormal"]}
        for bid in ["CHN-GND-01", "CHN-VEL-01", "CHN-PRG-01"]:
            assert (bid, "after_hours") in rules, bid
        for bid in ["CHN-VEL-01", "CHN-PRG-01"]:
            assert (bid, "unoccupied_high") in rules, bid
        assert ("CHN-PRG-01", "continuous_operation") in rules
        assert ("CHN-ANN-01", "unusual_daily_pattern") in rules
        assert any(r == "unexpected_increase" for _, r in rules)

    @pytest.mark.parametrize("h,code", [(24, 200), (168, 200), (0, 422), (200, 422)])
    def test_history(self, s, h, code):
        r = s.get(f"{API}/history", params={"hours": h})
        assert r.status_code == code
        if code == 200:
            assert 0 < len(r.json()["series"]) <= h

    def test_scenarios(self, s):
        sc = s.get(f"{API}/scenarios").json()["scenarios"]
        keys = [x["key"] for x in sc]
        assert keys == ["normal", "increased_ac_demand", "reduced_operating_hours", "energy_optimization",
                        "high_outdoor_temperature"]
        by = {x["key"]: x for x in sc}
        assert by["normal"]["comparison"]["demand_change_kw"] == 0
        assert by["high_outdoor_temperature"]["simulated"]["demand_kw"] > by["normal"]["simulated"]["demand_kw"]

    def test_sensor_interface(self, s):
        d = s.get(f"{API}/sensor-interface").json()
        assert d["http_endpoint"] == "POST /api/power/sensor-readings"
        assert "properties" in d["payload_schema"]


# --- Simulate formulas ---
class TestSimulate:
    def test_formula(self, s):
        ov = {"ac_units": 100, "ac_power_rating_kw": 2.0, "operating_hours": 10, "tariff_inr_per_kwh": 8,
              "available_capacity_kw": 400}
        d = s.post(f"{API}/simulate", json={"overrides": ov}).json()
        sim = d["simulated"]
        assert sim["demand_kw"] == 200 and sim["energy_kwh"] == 2000 and sim["cost_inr"] == 16000
        assert sim["utilization_pct"] == 50 and sim["severity"] == "normal"
        assert d["baseline_unchanged"] is True

    def test_temp_ignored_then_applied(self, s):
        base = s.post(f"{API}/simulate", json={}).json()["baseline"]["demand_kw"]
        d1 = s.post(f"{API}/simulate", json={"overrides": {"outdoor_temp_c": 45}}).json()
        assert d1["simulated"]["demand_kw"] == base
        d2 = s.post(f"{API}/simulate", json={"overrides": {"outdoor_temp_c": 45},
                                              "temperature_assumption": {"enabled": True}}).json()
        assert d2["simulated"]["demand_kw"] > base

    def test_overload_warning(self, s):
        d = s.post(f"{API}/simulate", json={"overrides": {"available_capacity_kw": 1}}).json()
        assert d["overload_warning"] is True and "CAPACITY OVERLOAD" in d["warnings"][0]

    @pytest.mark.parametrize("body", [{"overrides": {"ac_units": -1}}, {"overrides": {"available_capacity_kw": 0}},
                                      {"overrides": {"foo": 1}}, {"overrides": {"occupied_buildings": 9999}}])
    def test_validation(self, s, body):
        r = s.post(f"{API}/simulate", json=body)
        assert r.status_code == 422 and r.json()["detail"]

    def test_simulate_invalid_zone(self, s):
        assert s.post(f"{API}/simulate", json={"zone": "Bengaluru"}).status_code == 400

    def test_recommendations(self, s):
        d = s.post(f"{API}/recommendations", json={}).json()
        assert len(d["recommendations"]) > 0
        for r in d["recommendations"]:
            assert r["why"] and r["requires_human_approval"] is True and r["automatic_control"] is False

    def test_recommendations_scoped(self, s):
        d = s.post(f"{API}/recommendations", json={"building_id": "CHN-PRG-01"}).json()
        assert all(r["building_id"] == "CHN-PRG-01" for r in d["recommendations"])


# --- Thresholds (restored afterwards) ---
class TestThresholds:
    def test_put_changes_severity_and_restore(self, s):
        try:
            r = s.put(f"{API}/thresholds", json={"moderate_pct": 10, "high_pct": 20, "exceeded_pct": 30,
                                                 "tariff_inr_per_kwh": 10})
            assert r.status_code == 200
            assert s.get(f"{API}/thresholds").json()["moderate_pct"] == 10
            ov = s.get(f"{API}/alerts").json()["overload"]
            assert len(ov) > 4
            o = s.get(f"{API}/overview").json()["kpis"]
            assert abs(o["estimated_cost_inr"] - o["total_energy_kwh"] * 10) < 1
        finally:
            assert s.put(f"{API}/thresholds", json=DEFAULTS).status_code == 200
        t = s.get(f"{API}/thresholds").json()
        assert all(t[k] == v for k, v in DEFAULTS.items())

    @pytest.mark.parametrize("body", [{"moderate_pct": 90, "high_pct": 85, "exceeded_pct": 100, "tariff_inr_per_kwh": 8},
                                      {"moderate_pct": 70, "high_pct": 85, "exceeded_pct": 100, "tariff_inr_per_kwh": -1},
                                      {"moderate_pct": 70}])
    def test_put_invalid(self, s, body):
        assert s.put(f"{API}/thresholds", json=body).status_code == 422


# --- Sensor readings (cleaned up) ---
class TestSensor:
    def test_sensor_override_and_cleanup(self, s, mongo):
        try:
            r = s.post(f"{API}/sensor-readings", json={
                "building_id": "CHN-GND-01", "timestamp": "2030-01-01T12:00:00+05:30", "current_demand_kw": 5.5,
                "ac_units_operating": 2, "occupancy_status": "occupied", "device_id": "TEST_dev"})
            assert r.status_code == 201 and r.json()["data_source"] == "IOT_SENSOR"
            b = s.get(f"{API}/buildings", params={"building_id": "CHN-GND-01"}).json()["buildings"][0]
            assert b["data_source"] == "IOT_SENSOR" and b["current_demand_kw"] == 5.5
            assert s.get(f"{API}/overview").json()["data_source_summary"].get("IOT_SENSOR") == 1
        finally:
            mongo.power_sensor_readings.delete_many({"device_id": {"$regex": "^TEST_"}})
        b = s.get(f"{API}/buildings", params={"building_id": "CHN-GND-01"}).json()["buildings"][0]
        assert b["data_source"] == "SIMULATED"

    @pytest.mark.parametrize("body,code", [
        ({"building_id": "CHN-NOPE", "timestamp": "2030-01-01T12:00:00+05:30", "current_demand_kw": 1,
          "ac_units_operating": 1, "device_id": "TEST_x"}, 404),
        ({"building_id": "CHN-GND-01", "timestamp": "2030-01-01T12:00:00", "current_demand_kw": 1,
          "ac_units_operating": 1, "device_id": "TEST_x"}, 422),
        ({"building_id": "CHN-GND-01", "timestamp": "notadate", "current_demand_kw": 1,
          "ac_units_operating": 1, "device_id": "TEST_x"}, 422),
        ({"building_id": "CHN-GND-01", "timestamp": "2030-01-01T12:00:00+05:30", "current_demand_kw": 1,
          "ac_units_operating": 99999, "device_id": "TEST_x"}, 422),
    ])
    def test_sensor_invalid(self, s, mongo, body, code):
        try:
            assert s.post(f"{API}/sensor-readings", json=body).status_code == code
        finally:
            mongo.power_sensor_readings.delete_many({"device_id": {"$regex": "^TEST_"}})
