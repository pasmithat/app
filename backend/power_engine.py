"""Pure, side-effect-free power monitoring calculations for Chennai buildings."""
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample" / "chennai_power_monitoring.csv"

CHENNAI_ZONES = {
    "T. Nagar": (13.0418, 80.2341), "Anna Nagar": (13.0850, 80.2101), "Velachery": (12.9815, 80.2180),
    "Guindy": (13.0067, 80.2206), "Adyar": (13.0012, 80.2565), "Tambaram": (12.9249, 80.1000),
    "Perungudi": (12.9654, 80.2461), "Sholinganallur": (12.9010, 80.2279), "Ambattur": (13.1143, 80.1548),
    "Porur": (13.0382, 80.1565),
}
CHENNAI_BOUNDS = (12.75, 13.35, 79.95, 80.40)
DATA_SOURCES = {"SIMULATED", "IOT_SENSOR"}
OCCUPANCY = {"occupied", "unoccupied", "unknown"}
DEFAULT_SETTINGS = {"moderate_pct": 70.0, "high_pct": 85.0, "exceeded_pct": 100.0, "tariff_inr_per_kwh": 8.0}
RULES = {"increase_ratio": 1.3, "increase_min_kw": 10.0, "unoccupied_load_ratio": 0.25,
         "after_hours_load_ratio": 0.10, "continuous_hours": 24, "daily_energy_ratio": 1.35}
BASELINE_OUTDOOR_TEMP_C = 35.0
NUMERIC = ["ac_units", "ac_units_operating", "ac_power_rating_kw", "operating_hours", "energy_consumption_kwh",
           "current_demand_kw", "available_capacity_kw", "scheduled_start_hour", "scheduled_end_hour"]
INTS = {"ac_units", "ac_units_operating", "scheduled_start_hour", "scheduled_end_hour"}


class ScopeError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


# ---------- core formulas ----------
def total_demand_kw(ac_units, rating_kw):
    return ac_units * rating_kw


def energy_kwh(demand_kw, hours):
    return demand_kw * hours


def cost_inr(kwh, tariff):
    return kwh * tariff


def utilization_pct(demand_kw, capacity_kw):
    if capacity_kw is None or capacity_kw <= 0:
        raise ValueError("Available capacity must be greater than 0 kW")
    return demand_kw / capacity_kw * 100


def severity(util, settings):
    if util < settings["moderate_pct"]:
        return "normal"
    if util < settings["high_pct"]:
        return "moderate"
    if util <= settings["exceeded_pct"]:
        return "high"
    return "exceeded"


def validate_settings(s):
    if not (0 < s["moderate_pct"] < s["high_pct"] <= s["exceeded_pct"] <= 200):
        raise ValueError("Thresholds must satisfy 0 < moderate < high <= exceeded <= 200")
    if s["tariff_inr_per_kwh"] < 0:
        raise ValueError("Tariff cannot be negative")


def in_schedule(hour, start, end):
    return start <= hour < end


# ---------- data loading / validation ----------
def parse_row(row):
    rec = {}
    for key in ["timestamp", "building_id", "zone_name", "building_name", "occupancy_status", "data_source"]:
        val = (row.get(key) or "").strip()
        if not val:
            return None, f"missing {key}"
        rec[key] = val
    if rec["zone_name"] not in CHENNAI_ZONES:
        return None, f"zone '{rec['zone_name']}' is outside the Chennai monitored zones"
    if rec["data_source"] not in DATA_SOURCES:
        return None, f"unknown data_source '{rec['data_source']}'"
    if rec["occupancy_status"] not in OCCUPANCY:
        return None, f"invalid occupancy_status '{rec['occupancy_status']}'"
    try:
        rec["ts"] = datetime.fromisoformat(rec["timestamp"])
    except ValueError:
        return None, "invalid timestamp"
    for key in NUMERIC:
        raw = (row.get(key) or "").strip()
        if raw == "":
            return None, f"missing {key}"
        try:
            num = float(raw)
        except ValueError:
            return None, f"non-numeric {key}"
        if num < 0:
            return None, f"negative {key}"
        rec[key] = int(num) if key in INTS else num
    if rec["available_capacity_kw"] <= 0:
        return None, "available_capacity_kw must be > 0"
    if rec["ac_units_operating"] > rec["ac_units"]:
        return None, "ac_units_operating exceeds ac_units"
    if rec["operating_hours"] > 1:
        return None, "operating_hours exceeds the 1-hour interval"
    lat, lng = (row.get("latitude") or "").strip(), (row.get("longitude") or "").strip()
    rec["latitude"] = rec["longitude"] = None
    if lat and lng:
        try:
            la, lo = float(lat), float(lng)
        except ValueError:
            return None, "invalid coordinates"
        if not (CHENNAI_BOUNDS[0] <= la <= CHENNAI_BOUNDS[1] and CHENNAI_BOUNDS[2] <= lo <= CHENNAI_BOUNDS[3]):
            return None, "coordinates outside Chennai"
        rec["latitude"], rec["longitude"] = la, lo
    return rec, None


class Dataset:
    def __init__(self, rows):
        self.records, self.rejected = [], []
        for n, row in enumerate(rows, start=2):
            rec, err = parse_row(row)
            if err:
                self.rejected.append({"row": n, "building_id": row.get("building_id"), "reason": err})
            else:
                self.records.append(rec)
        self.records.sort(key=lambda r: (r["building_id"], r["ts"]))
        self.by_building = defaultdict(list)
        for r in self.records:
            self.by_building[r["building_id"]].append(r)
        self.end = max(r["ts"] for r in self.records)
        self.hour_baseline = self._hour_baseline()
        self.fingerprint = self.compute_fingerprint()

    def _hour_baseline(self):
        cutoff = self.end - timedelta(hours=23)
        sums = defaultdict(lambda: defaultdict(list))
        for bid, recs in self.by_building.items():
            for r in recs:
                if r["ts"] < cutoff:
                    sums[bid][r["ts"].hour].append(r["current_demand_kw"])
        return {bid: {h: sum(v) / len(v) for h, v in hrs.items()} for bid, hrs in sums.items()}

    def compute_fingerprint(self):
        payload = [{k: v for k, v in r.items() if k != "ts"} for r in self.records]
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def load_dataset(path=DATA_PATH):
    with open(path, newline="") as fh:
        return Dataset(list(csv.DictReader(fh)))


# ---------- snapshots ----------
def building_snapshot(ds, bid, settings, sensor=None):
    recs = ds.by_building[bid]
    last = recs[-1]
    last24 = recs[-24:]
    snap = {
        "building_id": bid, "building_name": last["building_name"], "zone_name": last["zone_name"],
        "latitude": last["latitude"], "longitude": last["longitude"], "ac_units": last["ac_units"],
        "ac_units_operating": last["ac_units_operating"], "ac_power_rating_kw": last["ac_power_rating_kw"],
        "current_demand_kw": last["current_demand_kw"], "available_capacity_kw": last["available_capacity_kw"],
        "occupancy_status": last["occupancy_status"], "scheduled_start_hour": last["scheduled_start_hour"],
        "scheduled_end_hour": last["scheduled_end_hour"], "data_source": last["data_source"],
        "as_of": last["timestamp"], "hour": last["ts"].hour,
        "daily_energy_kwh": round(sum(r["energy_consumption_kwh"] for r in last24), 2),
        "daily_operating_hours": round(sum(r["operating_hours"] for r in last24), 2),
    }
    if sensor:
        snap.update({"current_demand_kw": sensor["current_demand_kw"],
                     "ac_units_operating": sensor["ac_units_operating"], "data_source": "IOT_SENSOR",
                     "as_of": sensor["timestamp"], "hour": datetime.fromisoformat(sensor["timestamp"]).hour})
        if sensor.get("occupancy_status"):
            snap["occupancy_status"] = sensor["occupancy_status"]
    snap["installed_ac_load_kw"] = round(snap["ac_units"] * snap["ac_power_rating_kw"], 2)
    snap["operating_status"] = "Operating" if snap["ac_units_operating"] > 0 else "Off"
    util = utilization_pct(snap["current_demand_kw"], snap["available_capacity_kw"])
    snap["utilization_pct"] = round(util, 2)
    snap["severity"] = severity(util, settings)
    snap["daily_cost_inr"] = round(cost_inr(snap["daily_energy_kwh"], settings["tariff_inr_per_kwh"]), 2)
    return snap


def all_snapshots(ds, settings, sensors=None):
    sensors = sensors or {}
    out = []
    for bid in sorted(ds.by_building):
        s = sensors.get(bid)
        use = s if s and datetime.fromisoformat(s["timestamp"]) > ds.by_building[bid][-1]["ts"] else None
        out.append(building_snapshot(ds, bid, settings, use))
    return out


def validate_scope(ds, zone=None, building_id=None):
    if zone and zone not in CHENNAI_ZONES:
        raise ScopeError(400, f"Zone '{zone}' is not a monitored Chennai zone. Valid zones: "
                              + ", ".join(CHENNAI_ZONES))
    if building_id and building_id not in ds.by_building:
        raise ScopeError(404, f"Building '{building_id}' not found in Chennai monitoring data")


def filter_scope(snaps, zone=None, building_id=None):
    return [s for s in snaps if (not zone or s["zone_name"] == zone)
            and (not building_id or s["building_id"] == building_id)]


# ---------- alerts ----------
SEVERITY_TEXT = {
    "moderate": ("Demand is {u}% of configured capacity (moderate band {m}–{h}%).",
                 "Monitor the demand trend and avoid adding new cooling load during peak hours."),
    "high": ("Demand is {u}% of configured capacity (high band {h}–{x}%).",
             "Stagger AC start times and review load scheduling; ask the facility electrician to review the "
             "capacity margin."),
    "exceeded": ("Demand is {u}% of configured capacity, above the {x}% limit.",
                 "With on-site approval, reduce non-essential AC load and have a licensed electrician review the "
                 "supply capacity and protection settings."),
}
FAULT_NOTE = "High utilisation alone does not indicate an electrical fault."


def overload_alerts(snaps, settings):
    out = []
    for s in snaps:
        if s["severity"] == "normal":
            continue
        reason, action = SEVERITY_TEXT[s["severity"]]
        fmt = {"u": s["utilization_pct"], "m": settings["moderate_pct"], "h": settings["high_pct"],
               "x": settings["exceeded_pct"]}
        out.append({"id": f"OVL-{s['building_id']}", "type": "overload", "severity": s["severity"],
                    "building_id": s["building_id"], "building_name": s["building_name"],
                    "zone_name": s["zone_name"], "current_demand_kw": s["current_demand_kw"],
                    "available_capacity_kw": s["available_capacity_kw"], "utilization_pct": s["utilization_pct"],
                    "reason": reason.format(**fmt), "recommended_action": action, "note": FAULT_NOTE,
                    "data_source": s["data_source"]})
    order = {"exceeded": 0, "high": 1, "moderate": 2}
    return sorted(out, key=lambda a: (order[a["severity"]], -a["utilization_pct"]))


def _alert(s, rule, sev, reason, action, evidence):
    return {"id": f"ABN-{rule}-{s['building_id']}", "type": "abnormal", "rule": rule, "severity": sev,
            "building_id": s["building_id"], "building_name": s["building_name"], "zone_name": s["zone_name"],
            "reason": reason, "recommended_action": action, "evidence": evidence,
            "detection_method": "rule-based", "data_source": s["data_source"]}


def abnormal_alerts_for(ds, s):
    recs = ds.by_building[s["building_id"]]
    out = []
    installed = s["installed_ac_load_kw"] or 1
    demand = s["current_demand_kw"]
    start, end = s["scheduled_start_hour"], s["scheduled_end_hour"]
    sched = f"{start:02d}:00–{end:02d}:00"
    if not in_schedule(s["hour"], start, end) and demand > RULES["after_hours_load_ratio"] * installed:
        out.append(_alert(s, "after_hours", "high",
                          f"{s['ac_units_operating']} AC units drawing {demand} kW at {s['hour']:02d}:00, outside "
                          f"the operating schedule {sched}.",
                          "Verify whether after-hours cooling is required and adjust the AC schedule.",
                          {"hour": s["hour"], "schedule": sched, "demand_kw": demand}))
    if s["occupancy_status"] == "unoccupied" and demand > RULES["unoccupied_load_ratio"] * installed:
        pct = round(demand / installed * 100, 1)
        out.append(_alert(s, "unoccupied_high", "high",
                          f"Building reported unoccupied but AC load is {pct}% of installed capacity ({demand} kW).",
                          "Check for AC units left running in empty areas.",
                          {"occupancy": "unoccupied", "load_pct_of_installed": pct}))
    base = ds.hour_baseline.get(s["building_id"], {}).get(s["hour"])
    if base is not None and demand > base * RULES["increase_ratio"] and demand - base >= RULES["increase_min_kw"]:
        cmp = f"{round(demand / base, 2)}× the" if base else "above the"
        out.append(_alert(s, "unexpected_increase", "moderate",
                          f"Current demand {demand} kW is {cmp} expected baseline of {round(base, 1)} kW for "
                          f"{s['hour']:02d}:00 (same-hour average of previous days).",
                          "Investigate recent changes in equipment, occupancy or set-points.",
                          {"baseline_kw": round(base, 2), "current_kw": demand}))
    streak = 0
    for r in reversed(recs):
        if r["ac_units_operating"] > 0:
            streak += 1
        else:
            break
    full_day = end - start >= 24
    if not full_day and streak >= RULES["continuous_hours"]:
        out.append(_alert(s, "continuous_operation", "moderate",
                          f"AC has run continuously for {streak} hours although the schedule is {sched}.",
                          "Confirm whether continuous operation is needed; schedule off-periods if not.",
                          {"continuous_hours": streak, "schedule": sched}))
    prior = [r["energy_consumption_kwh"] for r in recs[:-24]]
    days = len(prior) // 24
    if days >= 3:
        avg_day = sum(prior[-days * 24:]) / days
        if avg_day > 0 and s["daily_energy_kwh"] > avg_day * RULES["daily_energy_ratio"]:
            out.append(_alert(s, "unusual_daily_pattern", "moderate",
                              f"Last 24 h energy {s['daily_energy_kwh']} kWh is "
                              f"{round(s['daily_energy_kwh'] / avg_day, 2)}× the {days}-day average "
                              f"({round(avg_day, 1)} kWh).",
                              "Review the building's energy pattern for the last day.",
                              {"last_24h_kwh": s["daily_energy_kwh"], "avg_daily_kwh": round(avg_day, 2)}))
    if s["occupancy_status"] == "unknown":
        for a in out:
            a["evidence"]["occupancy_note"] = "Occupancy unknown – occupancy-based rule not evaluated."
    return out


def abnormal_alerts(ds, snaps):
    return [a for s in snaps for a in abnormal_alerts_for(ds, s)]


# ---------- aggregation ----------
def summarize(snaps, settings):
    demand = sum(s["current_demand_kw"] for s in snaps)
    energy = sum(s["daily_energy_kwh"] for s in snaps)
    cap = sum(s["available_capacity_kw"] for s in snaps)
    return {"current_demand_kw": round(demand, 2), "total_energy_kwh": round(energy, 2),
            "estimated_cost_inr": round(cost_inr(energy, settings["tariff_inr_per_kwh"]), 2),
            "monitored_buildings": len(snaps),
            "operating_ac_units": sum(s["ac_units_operating"] for s in snaps),
            "installed_ac_units": sum(s["ac_units"] for s in snaps),
            "available_capacity_kw": round(cap, 2),
            "capacity_utilization_pct": round(utilization_pct(demand, cap), 2) if cap else 0.0}


def zone_summaries(snaps, settings):
    out = []
    for zone, (lat, lng) in CHENNAI_ZONES.items():
        zs = [s for s in snaps if s["zone_name"] == zone]
        summ = summarize(zs, settings) if zs else None
        out.append({"zone_name": zone, "latitude": lat, "longitude": lng, **(summ or {}),
                    "severity": severity(summ["capacity_utilization_pct"], settings) if summ else "normal",
                    "high_demand_buildings": sum(1 for s in zs if s["severity"] in ("high", "exceeded"))})
    return out


def history(ds, bids, hours):
    end = ds.end
    start = end - timedelta(hours=hours - 1)
    buckets = defaultdict(lambda: {"demand_kw": 0.0, "energy_kwh": 0.0, "capacity_kw": 0.0, "baseline_kw": 0.0})
    for bid in bids:
        for r in ds.by_building[bid]:
            if r["ts"] < start:
                continue
            b = buckets[r["timestamp"]]
            b["demand_kw"] += r["current_demand_kw"]
            b["energy_kwh"] += r["energy_consumption_kwh"]
            b["capacity_kw"] += r["available_capacity_kw"]
            b["baseline_kw"] += ds.hour_baseline.get(bid, {}).get(r["ts"].hour, 0.0)
    out = []
    for ts in sorted(buckets):
        b = buckets[ts]
        out.append({"timestamp": ts, **{k: round(v, 2) for k, v in b.items()},
                    "utilization_pct": round(b["demand_kw"] / b["capacity_kw"] * 100, 2) if b["capacity_kw"] else 0})
    return out


# ---------- simulation ----------
def baseline_inputs(snaps, settings):
    op_units = sum(s["ac_units_operating"] for s in snaps)
    if op_units:
        rating = sum(s["ac_units_operating"] * s["ac_power_rating_kw"] for s in snaps) / op_units
    else:
        total = sum(s["ac_units"] for s in snaps) or 1
        rating = sum(s["ac_units"] * s["ac_power_rating_kw"] for s in snaps) / total
    hours = sum(s["daily_operating_hours"] for s in snaps) / len(snaps) if snaps else 0
    return {"outdoor_temp_c": BASELINE_OUTDOOR_TEMP_C, "ac_units": op_units,
            "ac_power_rating_kw": round(rating, 2), "operating_hours": round(hours, 2),
            "occupied_buildings": sum(1 for s in snaps if s["occupancy_status"] == "occupied"),
            "tariff_inr_per_kwh": settings["tariff_inr_per_kwh"],
            "available_capacity_kw": round(sum(s["available_capacity_kw"] for s in snaps), 2)}


def compute_case(inp, settings, temp=None):
    demand = total_demand_kw(inp["ac_units"], inp["ac_power_rating_kw"])
    factor = 1.0
    if temp and temp.get("enabled"):
        factor = max(0.0, 1 + temp["demand_change_pct_per_c"] / 100 * (inp["outdoor_temp_c"] - temp["reference_temp_c"]))
    demand *= factor
    kwh = energy_kwh(demand, inp["operating_hours"])
    util = utilization_pct(demand, inp["available_capacity_kw"])
    return {"inputs": dict(inp), "demand_kw": round(demand, 2), "energy_kwh": round(kwh, 2),
            "cost_inr": round(cost_inr(kwh, inp["tariff_inr_per_kwh"]), 2), "utilization_pct": round(util, 2),
            "severity": severity(util, settings), "temperature_factor": round(factor, 4)}


def simulate(base_inp, overrides, settings, temp=None):
    sim_inp = {**base_inp, **{k: v for k, v in overrides.items() if v is not None}}
    base = compute_case(base_inp, settings)
    sim = compute_case(sim_inp, settings, temp)
    dd = sim["demand_kw"] - base["demand_kw"]
    warnings = []
    if sim["severity"] == "exceeded":
        warnings.append(f"CAPACITY OVERLOAD: simulated demand {sim['demand_kw']} kW exceeds "
                        f"{settings['exceeded_pct']}% of available capacity ({sim_inp['available_capacity_kw']} kW).")
    elif sim["severity"] == "high":
        warnings.append(f"High utilisation: simulated demand is {sim['utilization_pct']}% of capacity.")
    assumptions = ["Baseline = current snapshot (operating AC units, weighted rating, average daily operating hours "
                   "per building) — it differs from the measured 24 h energy total.",
                   "Total Power Demand = AC units × power rating (kW).",
                   "Energy = Demand × operating hours; Cost = Energy × tariff.",
                   "Occupied buildings is informational and does not change the demand formula."]
    if temp and temp.get("enabled"):
        assumptions.append(f"Scenario assumption: demand changes {temp['demand_change_pct_per_c']}% per °C relative "
                           f"to {temp['reference_temp_c']} °C (not a validated physical model).")
    else:
        assumptions.append("Outdoor temperature does not change demand (no temperature model enabled).")
    return {"baseline": base, "simulated": sim,
            "comparison": {"demand_change_kw": round(dd, 2),
                           "demand_change_pct": round(dd / base["demand_kw"] * 100, 2) if base["demand_kw"] else None,
                           "energy_change_kwh": round(sim["energy_kwh"] - base["energy_kwh"], 2),
                           "cost_difference_inr": round(sim["cost_inr"] - base["cost_inr"], 2)},
            "overload_warning": sim["severity"] == "exceeded", "warnings": warnings, "assumptions": assumptions}


HIGH_TEMP_ASSUMPTION = {"enabled": True, "demand_change_pct_per_c": 3.0, "reference_temp_c": BASELINE_OUTDOOR_TEMP_C}
SCENARIOS = {
    "normal": ("Normal operating scenario", lambda b: {}, None),
    "increased_ac_demand": ("Increased AC demand (+25% units)", lambda b: {"ac_units": round(b["ac_units"] * 1.25)}, None),
    "reduced_operating_hours": ("Reduced operating hours (−3 h)",
                                lambda b: {"operating_hours": max(1.0, b["operating_hours"] - 3)}, None),
    "energy_optimization": ("Energy optimisation (−20% rating, −2 h)",
                            lambda b: {"ac_power_rating_kw": round(b["ac_power_rating_kw"] * 0.8, 4),
                                       "operating_hours": max(1.0, b["operating_hours"] - 2)}, None),
    "high_outdoor_temperature": ("High outdoor temperature (42 °C)", lambda b: {"outdoor_temp_c": 42.0},
                                 HIGH_TEMP_ASSUMPTION),
}


def scenarios(base_inp, settings):
    out = []
    for key, (label, fn, temp) in SCENARIOS.items():
        r = simulate(base_inp, fn(base_inp), settings, temp)
        out.append({"key": key, "label": label, **r})
    return out


# ---------- recommendations ----------
def recommendations(ds, snaps, settings):
    recs = []
    alerts = {(a["building_id"], a["rule"]): a for a in abnormal_alerts(ds, snaps)}
    tariff = settings["tariff_inr_per_kwh"]

    def add(kind, title, s, priority, why, evidence, saving=None, saving_note=None):
        recs.append({"id": f"REC-{kind}-{s['building_id']}", "type": kind, "title": title,
                     "building_id": s["building_id"], "building_name": s["building_name"], "zone_name": s["zone_name"],
                     "priority": priority, "why": why, "evidence": evidence,
                     "estimated_saving_kwh_per_day": saving,
                     "estimated_saving_inr_per_day": round(saving * tariff, 2) if saving else None,
                     "saving_assumption": saving_note, "requires_human_approval": True,
                     "automatic_control": False, "data_source": s["data_source"]})

    for s in snaps:
        bid = s["building_id"]
        if (bid, "after_hours") in alerts:
            a = alerts[(bid, "after_hours")]
            add("adjust_schedule", "Adjust AC operating schedule", s, "high", a["reason"], a["evidence"],
                round(s["current_demand_kw"], 2), "Assumes one avoidable after-hours hour per day at current demand.")
        if (bid, "unoccupied_high") in alerts:
            a = alerts[(bid, "unoccupied_high")]
            add("reduce_unoccupied", "Reduce unnecessary operation in unoccupied building", s, "high",
                a["reason"], a["evidence"])
        for rule in ("unexpected_increase", "unusual_daily_pattern"):
            if (bid, rule) in alerts:
                a = alerts[(bid, rule)]
                add(f"investigate_{rule}", "Investigate abnormal consumption", s, "medium", a["reason"], a["evidence"])
        if s["severity"] in ("high", "exceeded"):
            add("review_capacity", "Review electrical capacity", s, "high" if s["severity"] == "exceeded" else "medium",
                f"Current demand {s['current_demand_kw']} kW is {s['utilization_pct']}% of configured capacity "
                f"{s['available_capacity_kw']} kW. {FAULT_NOTE}",
                {"utilization_pct": s["utilization_pct"], "severity": s["severity"]})
        if s["ac_power_rating_kw"] >= 3.5 and s["daily_operating_hours"] >= 12:
            saving = round(s["daily_energy_kwh"] * 0.2, 2)
            add("efficient_equipment", "Consider energy-efficient AC equipment", s, "low",
                f"Average unit rating is {s['ac_power_rating_kw']} kW and AC ran {s['daily_operating_hours']} h in "
                f"the last 24 h ({s['daily_energy_kwh']} kWh).",
                {"rating_kw": s["ac_power_rating_kw"], "daily_operating_hours": s["daily_operating_hours"]},
                saving, "Assumes 20% lower consumption from higher-efficiency units (illustrative).")
        if (bid, "continuous_operation") in alerts:
            a = alerts[(bid, "continuous_operation")]
            add("optimize_occupancy", "Optimise cooling schedule according to occupancy", s, "medium",
                a["reason"], a["evidence"])
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(recs, key=lambda r: order[r["priority"]])
