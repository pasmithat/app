import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";
import { SEV, fmt } from "./format";

export const ZoneDemandChart = ({ zones, zone, onZone }) => (
  <div className="panel p-4 h-full flex flex-col" data-testid="zone-demand-chart">
    <span className="font-mono text-[11px] uppercase tracking-widest text-slate-400 mb-3">AC demand by zone (kW)</span>
    <div className="flex-1 min-h-[340px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={zones} layout="vertical" margin={{ left: 8, right: 12 }}>
          <XAxis type="number" stroke="#475569" fontSize={10} />
          <YAxis type="category" dataKey="zone_name" stroke="#94A3B8" fontSize={10} width={96} />
          <Tooltip
            cursor={{ fill: "rgba(0,240,255,0.05)" }}
            contentStyle={{ background: "#121824", border: "1px solid #334155", fontSize: 12 }}
            formatter={(v, n, p) => [`${fmt(v, 1)} kW · ${fmt(p.payload.capacity_utilization_pct, 1)}%`, "Demand"]}
          />
          <Bar dataKey="current_demand_kw" radius={[0, 3, 3, 0]} onClick={(d) => onZone(d.zone_name)} className="cursor-pointer">
            {zones.map((z) => (
              <Cell key={z.zone_name} fill={zone === z.zone_name ? "#00F0FF" : SEV[z.severity].color} fillOpacity={zone && zone !== z.zone_name ? 0.35 : 0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  </div>
);
