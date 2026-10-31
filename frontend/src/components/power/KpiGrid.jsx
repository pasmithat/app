import { Activity, Zap, IndianRupee, Building2, Fan, Gauge, AlertTriangle, Radar } from "lucide-react";
import { fmt, inr } from "./format";

const CARDS = [
  { k: "current_demand_kw", label: "Current demand", unit: "kW", icon: Zap, f: (v) => fmt(v, 1), id: "kpi-current-demand" },
  { k: "total_energy_kwh", label: "Energy (last 24 h)", unit: "kWh", icon: Activity, f: (v) => fmt(v, 0), id: "kpi-total-energy" },
  { k: "estimated_cost_inr", label: "Estimated cost (24 h)", unit: "", icon: IndianRupee, f: inr, id: "kpi-estimated-cost" },
  { k: "monitored_buildings", label: "Monitored buildings", unit: "", icon: Building2, f: (v) => fmt(v), id: "kpi-monitored-buildings" },
  { k: "operating_ac_units", label: "Operating AC units", unit: "", icon: Fan, f: (v) => fmt(v), id: "kpi-operating-ac" },
  { k: "capacity_utilization_pct", label: "Capacity utilisation", unit: "%", icon: Gauge, f: (v) => fmt(v, 1), id: "kpi-capacity-utilization" },
  { k: "overload_alerts", label: "Overload alerts", unit: "", icon: AlertTriangle, f: (v) => fmt(v), id: "kpi-overload-alerts", warn: true },
  { k: "abnormal_alerts", label: "Abnormal consumption", unit: "", icon: Radar, f: (v) => fmt(v), id: "kpi-abnormal-alerts", warn: true },
];

export const KpiGrid = ({ kpis, onJump }) => (
  <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="kpi-grid">
    {CARDS.map((c, i) => {
      const v = kpis?.[c.k];
      const hot = c.warn && v > 0;
      return (
        <button
          key={c.k}
          type="button"
          data-testid={c.id}
          onClick={() => c.warn && onJump?.("overload")}
          style={{ animationDelay: `${i * 40}ms` }}
          className={`reveal panel text-left p-4 group transition-colors hover:bg-[#1A2333] ${hot ? "border-orange-500/30" : ""} ${c.warn ? "cursor-pointer" : "cursor-default"}`}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="font-mono text-[10px] uppercase tracking-widest text-slate-500">{c.label}</span>
            <c.icon className={`h-4 w-4 ${hot ? "text-orange-400" : "text-slate-600 group-hover:text-cyan-400"} transition-colors`} />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span data-testid={`${c.id}-value`} className={`font-mono text-2xl sm:text-3xl font-semibold tracking-tight ${hot ? "text-orange-300" : "text-cyan-300"}`}>
              {kpis ? c.f(v) : "…"}
            </span>
            {c.unit && <span className="font-mono text-xs text-slate-500">{c.unit}</span>}
          </div>
          {c.k === "capacity_utilization_pct" && kpis && (
            <div className="mt-3 h-1 bg-slate-800 rounded overflow-hidden">
              <div className="h-full bg-cyan-400 transition-[width] duration-500" style={{ width: `${Math.min(100, v)}%` }} />
            </div>
          )}
        </button>
      );
    })}
  </div>
);
