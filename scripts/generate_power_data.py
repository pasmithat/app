"""Generate SIMULATED Chennai AC power monitoring demo data (hourly, 7 days)."""
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
OUT = Path(__file__).resolve().parent.parent / "data" / "sample" / "chennai_power_monitoring.csv"

ZONES = {
    "T. Nagar": ("TNG", 13.0418, 80.2341), "Anna Nagar": ("ANN", 13.0850, 80.2101),
    "Velachery": ("VEL", 12.9815, 80.2180), "Guindy": ("GND", 13.0067, 80.2206),
    "Adyar": ("ADY", 13.0012, 80.2565), "Tambaram": ("TBM", 12.9249, 80.1000),
    "Perungudi": ("PRG", 12.9654, 80.2461), "Sholinganallur": ("SHO", 12.9010, 80.2279),
    "Ambattur": ("AMB", 13.1143, 80.1548), "Porur": ("POR", 13.0382, 80.1565),
}
TYPES = {
    "office": ("Commercial Office", (8, 20), (40, 90), (2.0, 3.0)),
    "retail": ("Retail Complex", (10, 23), (50, 110), (2.2, 3.2)),
    "residential": ("Residential Tower", (0, 24), (60, 120), (1.5, 2.0)),
    "hospital": ("Hospital", (0, 24), (40, 80), (2.5, 3.5)),
    "school": ("School Campus", (8, 16), (20, 45), (1.6, 2.2)),
    "itpark": ("IT Park Block", (9, 21), (80, 140), (3.5, 4.5)),
}
ZONE_TYPES = {
    "T. Nagar": ["retail", "office", "residential"], "Anna Nagar": ["residential", "hospital", "school"],
    "Velachery": ["itpark", "retail", "residential"], "Guindy": ["office", "itpark", "school"],
    "Adyar": ["hospital", "residential", "school"], "Tambaram": ["school", "residential", "retail"],
    "Perungudi": ["itpark", "office", "residential"], "Sholinganallur": ["itpark", "residential", "school"],
    "Ambattur": ["office", "retail", "residential"], "Porur": ["hospital", "office", "residential"],
}
COLUMNS = ["timestamp", "building_id", "zone_name", "building_name", "latitude", "longitude", "ac_units",
           "ac_units_operating", "ac_power_rating_kw", "operating_hours", "energy_consumption_kwh",
           "current_demand_kw", "available_capacity_kw", "occupancy_status", "scheduled_start_hour",
           "scheduled_end_hour", "data_source"]


def base_frac(btype, hour, in_sched):
    if btype == "residential":
        return 0.65 if (hour >= 21 or hour < 6) else (0.35 if hour >= 17 else 0.2)
    if btype == "hospital":
        return 0.55 + (0.15 if 11 <= hour <= 17 else 0)
    if in_sched:
        return 0.62 + (0.15 if 12 <= hour <= 16 else 0)
    return 0.0


def main():
    rng = random.Random(22)
    now = datetime.now(IST)
    end = now.replace(hour=22, minute=0, second=0, microsecond=0)
    if end > now:
        end -= timedelta(days=1)
    hours = [end - timedelta(hours=h) for h in range(167, -1, -1)]
    rows = []
    for zone, (code, lat0, lng0) in ZONES.items():
        for i, btype in enumerate(ZONE_TYPES[zone]):
            label, (s, e), urange, rrange = TYPES[btype]
            bid = f"CHN-{code}-{i + 1:02d}"
            units = rng.randint(*urange)
            rating = round(rng.uniform(*rrange), 2)
            installed = units * rating
            cap_factor = rng.uniform(1.15, 1.45)
            if bid == "CHN-ADY-01":
                cap_factor = 0.95
            if bid == "CHN-TNG-01":
                cap_factor = 0.69
            if bid == "CHN-AMB-02":
                cap_factor = 0.83
            capacity = round(installed * cap_factor, 1)
            lat, lng = round(lat0 + rng.uniform(-0.008, 0.008), 5), round(lng0 + rng.uniform(-0.008, 0.008), 5)
            if bid == "CHN-SHO-02":
                lat = lng = ""
            for idx, ts in enumerate(hours):
                hr = ts.hour
                in_sched = s <= hr < e
                last_day = idx >= len(hours) - 24
                f = base_frac(btype, hr, in_sched)
                if f > 0:
                    f += rng.uniform(-0.05, 0.05)
                occ = "occupied" if (in_sched or btype in ("residential", "hospital")) else "unoccupied"
                is_last = idx == len(hours) - 1
                if bid == "CHN-GND-01" and last_day and hr in (20, 21, 22):
                    f, occ = 0.5, "unknown"
                if bid == "CHN-VEL-01" and last_day and hr in (21, 22):
                    f, occ = 0.55, "unoccupied"
                if bid == "CHN-ADY-01" and is_last:
                    f = 1.0
                if bid == "CHN-TNG-01" and is_last:
                    f = 0.63
                if bid == "CHN-AMB-02" and is_last:
                    f = 0.63
                if bid == "CHN-PRG-01" and not in_sched:
                    f = 0.45 + rng.uniform(0, 0.05)
                if bid == "CHN-ANN-01" and last_day:
                    f = min(1.0, f * 1.5)
                f = max(0.0, min(1.0, f))
                op = round(units * f)
                demand = round(op * rating, 2)
                op_hours = 1.0 if op > 0 else 0.0
                rows.append([ts.isoformat(), bid, zone, f"{zone} {label} {i + 1} (Demo)", lat, lng, units, op,
                             rating, op_hours, round(demand * op_hours, 2), demand, capacity, occ, s, e,
                             "SIMULATED"])
    first = (hours[0] - timedelta(hours=1)).isoformat()
    rows.append([first, "BLR-KRM-01", "Bengaluru", "Koramangala Office (Demo)", 12.9352, 77.6245, 50, 30, 2.5,
                 1.0, 75.0, 75.0, 150.0, "occupied", 8, 20, "SIMULATED"])
    rows.append([first, "CHN-TBM-01", "Tambaram", "Tambaram School Campus 1 (Demo)", 12.92, 80.1, 30, 10, 2.0,
                 1.0, -12.0, -12.0, 90.0, "occupied", 8, 16, "SIMULATED"])
    rows.append([first, "CHN-POR-01", "Porur", "Porur Hospital 1 (Demo)", 13.04, 80.16, 60, 30, 3.0, 1.0,
                 "", "", 250.0, "occupied", 0, 24, "SIMULATED"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
