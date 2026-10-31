import { ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from "recharts";
import { fmt } from "./format";

const RANGES = [24, 72, 168];

const tick = (ts, hours) => {
  const d = new Date(ts);
  return hours > 24 ? `${d.getDate()}/${d.getMonth() + 1} ${d.getHours()}h` : `${String(d.getHours()).padStart(2, "0")}:00`;
};

export const HistoryChart = ({ series, hours, onHours }) => (
  <div className="panel p-4" data-testid="history-chart">
    <div className="flex items-center justify-between mb-3">
      <span className="font-mono text-[11px] uppercase tracking-widest text-slate-400">Demand vs expected baseline vs capacity</span>
      <div className="flex gap-1">
        {RANGES.map((h) => (
          <button
            key={h}
            type="button"
            data-testid={`history-range-${h}`}
            onClick={() => onHours(h)}
            className={`font-mono text-[10px] px-2 py-1 rounded border transition-colors ${hours === h ? "border-cyan-500/50 text-cyan-300 bg-cyan-500/10" : "border-slate-700 text-slate-500 hover:text-slate-200"}`}
          >
            {h === 168 ? "7D" : `${h}H`}
          </button>
        ))}
      </div>
    </div>
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={series} margin={{ left: 0, right: 8, top: 4 }}>
          <defs>
            <linearGradient id="dem" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00F0FF" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#00F0FF" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#1e293b" vertical={false} />
          <XAxis dataKey="timestamp" tickFormatter={(t) => tick(t, hours)} stroke="#475569" fontSize={10} minTickGap={24} />
          <YAxis stroke="#475569" fontSize={10} tickFormatter={(v) => fmt(v)} width={48} />
          <Tooltip
            contentStyle={{ background: "#121824", border: "1px solid #334155", fontSize: 12 }}
            labelFormatter={(t) => new Date(t).toLocaleString("en-IN")}
            formatter={(v, n) => [`${fmt(v, 1)} kW`, n]}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Area type="monotone" dataKey="demand_kw" name="Demand" stroke="#00F0FF" fill="url(#dem)" strokeWidth={2} />
          <Line type="monotone" dataKey="baseline_kw" name="Expected baseline" stroke="#94A3B8" strokeDasharray="4 4" dot={false} />
          <Line type="stepAfter" dataKey="capacity_kw" name="Capacity" stroke="#EF4444" dot={false} strokeWidth={1} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  </div>
);
