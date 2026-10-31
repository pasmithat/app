export const SimBadge = ({ source = "SIMULATED", testId = "simulated-data-badge" }) => {
  const sensor = source === "IOT_SENSOR";
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center gap-2 font-mono text-[10px] font-bold tracking-widest uppercase px-2.5 py-1 rounded-full border ${
        sensor ? "bg-cyan-500/15 border-cyan-500/40 text-cyan-300" : "bg-amber-500/15 border-amber-500/40 text-amber-300"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full animate-pulse ${sensor ? "bg-cyan-300" : "bg-amber-300"}`} />
      {sensor ? "IoT sensor reading" : "Simulated demo data"}
    </span>
  );
};

export const SevBadge = ({ sev, testId }) => {
  const map = {
    normal: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    moderate: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
    high: "bg-orange-500/15 text-orange-400 border-orange-500/30",
    exceeded: "bg-red-500/15 text-red-400 border-red-500/40",
  };
  return (
    <span data-testid={testId} className={`inline-block font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border ${map[sev] || map.normal}`}>
      {sev}
    </span>
  );
};

export const SectionHead = ({ id, kicker, title, children }) => (
  <div id={id} className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-5 scroll-mt-28">
    <div>
      <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-cyan-400/80 mb-1">{kicker}</div>
      <h2 className="text-base md:text-lg font-bold tracking-tight text-slate-100">{title}</h2>
    </div>
    {children}
  </div>
);
