from datetime import datetime, timezone
from typing import Literal, Optional
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

import power_engine as pe

router = APIRouter(prefix="/api/power", tags=["power"])
STATE = {"ds": None, "db": None}


def init(db):
    STATE["db"] = db
    STATE["ds"] = pe.load_dataset()


def ds():
    return STATE["ds"]


async def get_settings():
    doc = await STATE["db"].power_settings.find_one({"key": "global"}, {"_id": 0, "key": 0})
    return {**pe.DEFAULT_SETTINGS, **(doc or {})}


async def latest_sensors():
    pipeline = [{"$sort": {"ts_utc": -1}}, {"$group": {"_id": "$building_id", "doc": {"$first": "$$ROOT"}}}]
    out = {}
    async for row in STATE["db"].power_sensor_readings.aggregate(pipeline):
        doc = row["doc"]
        doc.pop("_id", None)
        doc.pop("ts_utc", None)
        out[row["_id"]] = doc
    return out


async def scoped(zone, building_id):
    try:
        pe.validate_scope(ds(), zone, building_id)
    except pe.ScopeError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    settings = await get_settings()
    snaps = pe.all_snapshots(ds(), settings, await latest_sensors())
    return settings, pe.filter_scope(snaps, zone, building_id)


def source_summary(snaps):
    counts = {}
    for s in snaps:
        counts[s["data_source"]] = counts.get(s["data_source"], 0) + 1
    return counts


@router.get("/overview")
async def overview(zone: Optional[str] = None, building_id: Optional[str] = None):
    settings, snaps = await scoped(zone, building_id)
    ovl = pe.overload_alerts(snaps, settings)
    abn = pe.abnormal_alerts(ds(), snaps)
    return {"scope": {"zone": zone, "building_id": building_id}, "as_of": ds().end.isoformat(),
            "kpis": {**pe.summarize(snaps, settings), "overload_alerts": len(ovl), "abnormal_alerts": len(abn)},
            "severity_counts": {k: sum(1 for s in snaps if s["severity"] == k)
                                for k in ("normal", "moderate", "high", "exceeded")},
            "settings": settings, "data_source_summary": source_summary(snaps),
            "data_quality": {"rows_loaded": len(ds().records), "rows_rejected": len(ds().rejected),
                             "rejected": ds().rejected,
                             "buildings_without_coordinates": [s["building_id"] for s in snaps
                                                               if s["latitude"] is None]},
            "baseline_fingerprint": ds().fingerprint}


@router.get("/zones")
async def zones():
    settings, snaps = await scoped(None, None)
    return {"zones": pe.zone_summaries(snaps, settings), "city": "Chennai"}


@router.get("/buildings")
async def buildings(zone: Optional[str] = None, building_id: Optional[str] = None):
    _, snaps = await scoped(zone, building_id)
    return {"buildings": snaps, "count": len(snaps), "data_source_summary": source_summary(snaps)}


@router.get("/alerts")
async def alerts(zone: Optional[str] = None, building_id: Optional[str] = None):
    settings, snaps = await scoped(zone, building_id)
    return {"overload": pe.overload_alerts(snaps, settings), "abnormal": pe.abnormal_alerts(ds(), snaps),
            "thresholds": settings, "rules": pe.RULES, "detection_method": "rule-based",
            "note": pe.FAULT_NOTE}


@router.get("/history")
async def history(zone: Optional[str] = None, building_id: Optional[str] = None,
                  hours: int = Query(24, ge=1, le=168)):
    _, snaps = await scoped(zone, building_id)
    return {"hours": hours, "series": pe.history(ds(), [s["building_id"] for s in snaps], hours)}


class Overrides(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outdoor_temp_c: Optional[float] = Field(None, ge=-10, le=60)
    ac_units: Optional[int] = Field(None, ge=0, le=100000)
    ac_power_rating_kw: Optional[float] = Field(None, gt=0, le=100)
    operating_hours: Optional[float] = Field(None, ge=0, le=24)
    occupied_buildings: Optional[int] = Field(None, ge=0)
    tariff_inr_per_kwh: Optional[float] = Field(None, ge=0, le=100)
    available_capacity_kw: Optional[float] = Field(None, gt=0, le=10_000_000)


class TempAssumption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    demand_change_pct_per_c: float = Field(3.0, ge=0, le=20)
    reference_temp_c: float = Field(pe.BASELINE_OUTDOOR_TEMP_C, ge=20, le=45)


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zone: Optional[str] = None
    building_id: Optional[str] = None
    overrides: Overrides = Field(default_factory=Overrides)
    temperature_assumption: TempAssumption = Field(default_factory=TempAssumption)


@router.post("/simulate")
async def simulate(req: SimulateRequest):
    settings, snaps = await scoped(req.zone, req.building_id)
    ov = req.overrides.model_dump()
    if ov["occupied_buildings"] is not None and ov["occupied_buildings"] > len(snaps):
        raise HTTPException(status_code=422, detail=f"occupied_buildings ({ov['occupied_buildings']}) cannot exceed "
                                                    f"monitored buildings in scope ({len(snaps)})")
    before = ds().compute_fingerprint()
    base = pe.baseline_inputs(snaps, settings)
    result = pe.simulate(base, ov, settings, req.temperature_assumption.model_dump())
    after = ds().compute_fingerprint()
    return {**result, "scope": {"zone": req.zone, "building_id": req.building_id},
            "baseline_fingerprint_before": before, "baseline_fingerprint_after": after,
            "baseline_unchanged": before == after == ds().fingerprint, "data_source_summary": source_summary(snaps)}


@router.get("/scenarios")
async def scenarios(zone: Optional[str] = None, building_id: Optional[str] = None):
    settings, snaps = await scoped(zone, building_id)
    return {"scenarios": pe.scenarios(pe.baseline_inputs(snaps, settings), settings),
            "note": "Electrical scenarios are independent of the heat intervention simulator; only the "
                    "high-temperature scenario uses an explicit, documented demand assumption."}


class ScopeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zone: Optional[str] = None
    building_id: Optional[str] = None


@router.post("/recommendations")
async def recommendations(req: ScopeRequest):
    settings, snaps = await scoped(req.zone, req.building_id)
    return {"recommendations": pe.recommendations(ds(), snaps, settings),
            "policy": "Recommendations are advisory. No AC unit or electrical equipment is switched or controlled "
                      "automatically; any action requires authorised hardware and explicit human approval."}


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    moderate_pct: float = Field(gt=0, le=200)
    high_pct: float = Field(gt=0, le=200)
    exceeded_pct: float = Field(gt=0, le=200)
    tariff_inr_per_kwh: float = Field(ge=0, le=100)


@router.get("/thresholds")
async def get_thresholds():
    return {**await get_settings(), "defaults": pe.DEFAULT_SETTINGS}


@router.put("/thresholds")
async def put_thresholds(body: SettingsUpdate):
    data = body.model_dump()
    try:
        pe.validate_settings(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await STATE["db"].power_settings.update_one({"key": "global"}, {"$set": data}, upsert=True)
    return {**data, "defaults": pe.DEFAULT_SETTINGS}


class SensorReading(BaseModel):
    model_config = ConfigDict(extra="forbid")
    building_id: str
    timestamp: str
    current_demand_kw: float = Field(ge=0, le=100000)
    ac_units_operating: int = Field(ge=0)
    occupancy_status: Optional[Literal["occupied", "unoccupied", "unknown"]] = None
    device_id: str = Field(min_length=1, max_length=100)

    @field_validator("timestamp")
    @classmethod
    def check_ts(cls, v):
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            raise ValueError("timestamp must include a timezone offset, e.g. +05:30")
        return dt.isoformat()


@router.post("/sensor-readings", status_code=201)
async def ingest_reading(r: SensorReading):
    if r.building_id not in ds().by_building:
        raise HTTPException(status_code=404, detail=f"Building '{r.building_id}' not found")
    units = ds().by_building[r.building_id][-1]["ac_units"]
    if r.ac_units_operating > units:
        raise HTTPException(status_code=422, detail=f"ac_units_operating exceeds installed units ({units})")
    doc = {"id": str(uuid.uuid4()), **r.model_dump(), "data_source": "IOT_SENSOR"}
    ts = datetime.fromisoformat(r.timestamp)
    await STATE["db"].power_sensor_readings.insert_one({**doc, "ts_utc": ts.astimezone(timezone.utc)})
    applied = ts > ds().by_building[r.building_id][-1]["ts"]
    return {**doc, "applied": applied,
            "message": "Reading replaces the simulated snapshot" if applied else
            "Stored, but older than the current dataset snapshot, so it is not applied"}


@router.get("/sensor-interface")
async def sensor_interface():
    return {"status": "ready_for_authorised_sensors", "connected_sensors": 0,
            "http_endpoint": "POST /api/power/sensor-readings",
            "mqtt_topic_pattern": "urbanshield/chennai/{zone}/{building_id}/power",
            "payload_schema": SensorReading.model_json_schema(),
            "note": "An MQTT bridge can forward authorised sensor messages to the HTTP endpoint. Sensor readings "
                    "newer than the demo dataset replace the simulated snapshot and are labelled IOT_SENSOR."}
