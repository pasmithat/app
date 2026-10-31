import { useEffect, useState } from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from "recharts";
import { api, errMsg } from "@/lib/api";
import { SevBadge } from "./Badges";
import { fmt, inr, signed } from "./format";

export const ScenarioCompare = ({ scope }) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get("/scenarios", { params: scope }).then((r) => setData(r.data)).catch((e) => setError(errMsg(e)));
  }, [scope]);

  if (error) return <div className="panel p-4 text-red-300 text-sm">{error}</div>;
  if (!data) return <div className="panel p-6 text-slate-500 text-sm">Loading scenarios…</div>;
  const chart = data.scenarios.map((s) => ({ name: s.label.split(" (")[0], before: s.baseline.demand_kw, after: s.simulated.demand_kw }));
  return (
    <div className="space-y-4" data-testid="scenario-comparison-matrix">
      <div className="panel overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="font-mono text-[10px] uppercase tracking-wider text-slate-500 border-b border-slate-800">
              {["Scenario", "Demand before → after", "Energy before → after", "Cost before → after", "Δ Cost", "Utilisation"].map((h) => (
                <th key={h} className="text-left px-4 py-3 whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.scenarios.map((s) => (
              <tr key={s.key} className="border-b border-slate-800/60 hover:bg-[#1A2333] transition-colors" data-testid={`scenario-row-${s.key}`}>
                <td className="px-4 py-3 text-slate-100 whitespace-nowrap">{s.label}</td>
                <td className="px-4 py-3 font-mono text-slate-300 whitespace-nowrap">{fmt(s.baseline.demand_kw, 0)} → <span className="text-cyan-300">{fmt(s.simulated.demand_kw, 0)}</span> kW</td>
                <td className="px-4 py-3 font-mono text-slate-300 whitespace-nowrap">{fmt(s.baseline.energy_kwh, 0)} → <span className="text-cyan-300">{fmt(s.simulated.energy_kwh, 0)}</span> kWh</td>
                <td className="px-4 py-3 font-mono text-slate-300 whitespace-nowrap">{inr(s.baseline.cost_inr)} → <span className="text-cyan-300">{inr(s.simulated.cost_inr)}</span></td>
                <td className={`px-4 py-3 font-mono whitespace-nowrap ${s.comparison.cost_difference_inr > 0 ? "text-orange-300" : "text-emerald-300"}`} data-testid={`scenario-cost-diff-${s.key}`}>
                  {s.comparison.cost_difference_inr > 0 ? "+" : ""}{inr(s.comparison.cost_difference_inr)} ({signed(s.comparison.demand_change_pct, 1, "%")} kW)
                </td>
                <td className="px-4 py-3 whitespace-nowrap"><span className="font-mono text-slate-300 mr-2">{fmt(s.simulated.utilization_pct, 1)}%</span><SevBadge sev={s.simulated.severity} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="grid lg:grid-cols-3 gap-4">
        <div className="panel p-4 lg:col-span-2 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart}>
              <XAxis dataKey="name" stroke="#475569" fontSize={10} interval={0} />
              <YAxis stroke="#475569" fontSize={10} width={48} />
              <Tooltip contentStyle={{ background: "#121824", border: "1px solid #334155", fontSize: 12 }} formatter={(v) => `${fmt(v, 1)} kW`} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="before" name="Before (kW)" fill="#475569" radius={[3, 3, 0, 0]} />
              <Bar dataKey="after" name="After (kW)" fill="#00F0FF" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="panel p-4 text-xs text-slate-400 space-y-2" data-testid="scenario-notes">
          <p className="text-slate-300">{data.note}</p>
          <p>High outdoor temperature scenario: +3% demand per °C above 35 °C (scenario assumption, editable in the What-If simulator).</p>
          <p>Energy optimisation scenario assumes 20% lower unit rating and 2 fewer operating hours.</p>
        </div>
      </div>
    </div>
  );
};
