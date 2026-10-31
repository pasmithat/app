import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowRight, Database } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { SimBadge, SectionHead } from "@/components/power/Badges";
import { KpiGrid } from "@/components/power/KpiGrid";
import { ZoneSelector } from "@/components/power/ZoneSelector";
import { PowerMap } from "@/components/power/PowerMap";
import { ZoneDemandChart } from "@/components/power/ZoneDemandChart";
import { HistoryChart } from "@/components/power/HistoryChart";
import { BuildingsTable } from "@/components/power/BuildingsTable";
import { AlertsPanel } from "@/components/power/AlertsPanel";
import { ThresholdConfig } from "@/components/power/ThresholdConfig";
import { WhatIfSimulator } from "@/components/power/WhatIfSimulator";
import { ScenarioCompare } from "@/components/power/ScenarioCompare";
import { Recommendations } from "@/components/power/Recommendations";

const usePowerData = (zone, buildingId, hours) => {
  const [tick, setTick] = useState(0);
  const [map, setMap] = useState({ buildings: [], zones: [] });
  const [d, setD] = useState({});
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);
  const scope = useMemo(() => ({ ...(zone && { zone }), ...(buildingId && { building_id: buildingId }) }), [zone, buildingId]);

  useEffect(() => {
    Promise.all([api.get("/buildings"), api.get("/zones")])
      .then(([b, z]) => setMap({ buildings: b.data.buildings, zones: z.data.zones }))
      .catch((e) => setError(errMsg(e)));
  }, [tick]);

  useEffect(() => {
    Promise.all([api.get("/overview", { params: scope }), api.get("/buildings", { params: scope }), api.get("/alerts", { params: scope })])
      .then(([o, b, a]) => { setD({ overview: o.data, buildings: b.data.buildings, alerts: a.data }); setError(null); })
      .catch((e) => setError(errMsg(e)));
  }, [scope, tick]);

  useEffect(() => {
    api.get("/history", { params: { ...scope, hours } }).then((r) => setHistory(r.data.series)).catch((e) => setError(errMsg(e)));
  }, [scope, hours, tick]);

  return { scope, map, ...d, history, error, refresh: useCallback(() => setTick((t) => t + 1), []), tick };
};

const Hero = ({ overview }) => (
  <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
    <div>
      <div className="font-mono text-[11px] uppercase tracking-[0.25em] text-cyan-400 mb-2">Stage 03 · Chennai</div>
      <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight" data-testid="power-page-title">Power Monitoring</h1>
      <p className="text-slate-400 mt-3 max-w-2xl text-sm sm:text-base">
        AC electricity demand, capacity utilisation, overload and abnormal-use detection for monitored Chennai buildings.
      </p>
    </div>
    <div className="flex flex-col items-start lg:items-end gap-2">
      <SimBadge source={overview?.data_source_summary?.IOT_SENSOR ? "IOT_SENSOR" : "SIMULATED"} testId="page-data-source-badge" />
      <span className="font-mono text-[11px] text-slate-500" data-testid="data-as-of">
        Snapshot {overview ? `${new Date(overview.as_of).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })} IST` : "…"}
      </span>
      {overview && (
        <span className="font-mono text-[11px] text-slate-500 flex items-center gap-1.5" data-testid="data-quality-summary">
          <Database className="h-3 w-3" /> {overview.data_quality.rows_loaded} rows · {overview.data_quality.rows_rejected} rejected (invalid / non-Chennai)
          · sensors: {overview.data_source_summary.IOT_SENSOR || 0}
        </span>
      )}
    </div>
  </div>
);

export default function PowerMonitoring() {
  const [zone, setZone] = useState(null);
  const [buildingId, setBuildingId] = useState(null);
  const [hours, setHours] = useState(24);
  const p = usePowerData(zone, buildingId, hours);
  const loc = useLocation();

  useEffect(() => {
    if (loc.hash && p.overview) {
      document.getElementById(loc.hash.slice(1))?.scrollIntoView({ behavior: "smooth" });
    }
  }, [loc.hash, p.overview]);

  const pickZone = (z) => { setZone(z); setBuildingId(null); };
  const pickBuilding = (b) => { setZone(b.zone_name); setBuildingId(b.building_id); };
  const jump = (id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  const selectedName = buildingId && p.map.buildings.find((b) => b.building_id === buildingId)?.building_name;

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-10 space-y-14" data-testid="power-monitoring-page">
      <Hero overview={p.overview} />
      {p.error && <div className="panel p-3 border-red-500/40 text-red-300 text-sm" data-testid="power-error">{p.error}</div>}

      <section className="space-y-5">
        <ZoneSelector zone={zone} buildingName={selectedName} onZone={pickZone} onClear={() => pickZone(null)} />
        <KpiGrid kpis={p.overview?.kpis} onJump={jump} />
      </section>

      <section>
        <SectionHead id="map" kicker="Spatial" title="Chennai power monitoring map" />
        <div className="grid lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <PowerMap buildings={p.map.buildings} zones={p.map.zones} zone={zone} buildingId={buildingId} onBuilding={pickBuilding} onZone={pickZone} />
          </div>
          <ZoneDemandChart zones={p.map.zones} zone={zone} onZone={pickZone} />
        </div>
      </section>

      <section>
        <SectionHead id="ac" kicker="AC monitoring" title={`Buildings${zone ? ` · ${zone}` : " · all zones"} (${p.buildings?.length ?? 0})`} />
        <div className="space-y-4">
          <HistoryChart series={p.history} hours={hours} onHours={setHours} />
          <BuildingsTable buildings={p.buildings || []} buildingId={buildingId} onSelect={pickBuilding} />
        </div>
      </section>

      <section>
        <SectionHead id="overload" kicker="Stage 04 · Detection" title="Overload & abnormal consumption alerts" />
        <div className="grid lg:grid-cols-4 gap-4">
          <div className="lg:col-span-3"><AlertsPanel alerts={p.alerts} onSelect={(a) => pickBuilding({ zone_name: a.zone_name, building_id: a.building_id })} /></div>
          <ThresholdConfig settings={p.overview?.settings} onSaved={p.refresh} />
        </div>
      </section>

      <section>
        <SectionHead id="whatif" kicker="Stage 05 · Simulation" title="What-if power simulation" />
        <WhatIfSimulator key={`${JSON.stringify(p.scope)}-${p.tick}`} scope={p.scope} buildingsCount={p.overview?.kpis.monitored_buildings ?? 0} />
      </section>

      <section>
        <SectionHead id="twin" kicker="Climate Digital Twin" title="Intervention scenarios: demand, energy & cost" />
        <ScenarioCompare key={p.tick} scope={p.scope} />
      </section>

      <section>
        <SectionHead id="recommendations" kicker="Stage 06 · Advisory" title="Smart energy recommendations" />
        <Recommendations scope={p.scope} refresh={p.tick} />
      </section>

      <Link to="/emergency" data-testid="next-stage-emergency" className="panel p-5 flex items-center justify-between hover:bg-[#1A2333] transition-colors group">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-widest text-slate-500">Next stage 07</div>
          <div className="font-display text-xl font-bold">Emergency Priority Planning</div>
        </div>
        <ArrowRight className="h-5 w-5 text-cyan-400 group-hover:translate-x-1 transition-transform" />
      </Link>
    </div>
  );
}
