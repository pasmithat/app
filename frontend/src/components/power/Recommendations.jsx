import { useEffect, useState } from "react";
import { Hand, Lightbulb } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, inr } from "./format";

const PRIO = {
  high: "text-red-300 border-red-500/40 bg-red-500/10",
  medium: "text-orange-300 border-orange-500/40 bg-orange-500/10",
  low: "text-slate-300 border-slate-600 bg-slate-700/20",
};

const RecCard = ({ r }) => (
  <div className="panel p-4 flex flex-col gap-3" data-testid={`recommendation-${r.id}`}>
    <div className="flex items-start justify-between gap-2">
      <div>
        <div className="font-display font-bold text-slate-100">{r.title}</div>
        <div className="text-xs text-slate-500">{r.building_name} · {r.zone_name}</div>
      </div>
      <span className={`font-mono text-[10px] uppercase px-2 py-0.5 rounded border ${PRIO[r.priority]}`}>{r.priority}</span>
    </div>
    <div className="rounded border border-cyan-500/20 bg-cyan-500/5 p-3" data-testid={`recommendation-why-${r.id}`}>
      <div className="font-mono text-[10px] uppercase tracking-widest text-cyan-400 mb-1">Why this was generated</div>
      <p className="text-sm text-slate-300">{r.why}</p>
    </div>
    {r.estimated_saving_kwh_per_day && (
      <p className="font-mono text-xs text-emerald-300">
        Potential saving ≈ {fmt(r.estimated_saving_kwh_per_day, 0)} kWh/day ({inr(r.estimated_saving_inr_per_day)})
        <span className="block text-[10px] text-slate-500 font-sans mt-0.5">{r.saving_assumption}</span>
      </p>
    )}
    <div className="flex items-center gap-1.5 text-[11px] text-amber-300/90 font-mono mt-auto">
      <Hand className="h-3.5 w-3.5" /> Requires human approval · no automatic control
    </div>
  </div>
);

export const Recommendations = ({ scope, refresh }) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.post("/recommendations", scope).then((r) => setData(r.data)).catch((e) => setError(errMsg(e)));
  }, [scope, refresh]);

  if (error) return <div className="panel p-4 text-red-300 text-sm">{error}</div>;
  if (!data) return <div className="panel p-6 text-slate-500 text-sm">Loading recommendations…</div>;
  return (
    <div className="space-y-4" data-testid="smart-recommendations-panel">
      <div className="panel p-3 flex gap-2 text-xs text-slate-400" data-testid="recommendation-policy">
        <Lightbulb className="h-4 w-4 text-cyan-400 shrink-0" /> {data.policy}
      </div>
      {data.recommendations.length === 0 && (
        <div className="panel p-6 text-center text-sm text-slate-500" data-testid="recommendations-empty">No recommendations for this scope — consumption looks normal.</div>
      )}
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
        {data.recommendations.map((r) => <RecCard key={r.id} r={r} />)}
      </div>
    </div>
  );
};
