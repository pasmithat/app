import { Link, useLocation } from "react-router-dom";
import { ShieldHalf, ChevronRight } from "lucide-react";

const STEPS = [
  { to: "/heat-monitoring", label: "Heat Monitoring", id: "heat-monitoring" },
  { to: "/heat-risk", label: "Heat Risk", id: "heat-risk" },
  { to: "/power", label: "AC Power Monitoring", id: "power" },
  { to: "/power#overload", label: "Overload Detection", id: "overload" },
  { to: "/power#whatif", label: "What-If Simulation", id: "whatif" },
  { to: "/power#recommendations", label: "Recommendations", id: "recommendations" },
  { to: "/emergency", label: "Emergency Priority", id: "emergency" },
];

const isActive = (step, loc) => {
  const [path, hash] = step.to.split("#");
  if (path !== loc.pathname) return false;
  return hash ? loc.hash === `#${hash}` : !loc.hash || path !== "/power";
};

export const Shell = ({ children }) => {
  const loc = useLocation();
  return (
    <div className="min-h-screen grid-bg">
      <header className="sticky top-0 z-[1000] bg-[#0B0F17]/90 backdrop-blur-md border-b border-slate-800/80">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-3 flex flex-col lg:flex-row lg:items-center gap-3">
          <Link to="/power" data-testid="brand-link" className="flex items-center gap-2 shrink-0">
            <ShieldHalf className="h-6 w-6 text-cyan-400" />
            <span className="font-display font-extrabold text-lg tracking-tight">UrbanShield<span className="text-cyan-400"> AI</span></span>
            <span className="font-mono text-[10px] text-slate-500 border border-slate-700 rounded px-1.5 py-0.5">CHENNAI</span>
          </Link>
          <nav className="flex items-center gap-1 overflow-x-auto pb-1 lg:pb-0 lg:ml-6" data-testid="pipeline-nav">
            {STEPS.map((s, i) => {
              const active = isActive(s, loc);
              return (
                <div key={s.id} className="flex items-center shrink-0">
                  <Link
                    to={s.to}
                    onClick={() => { if (!s.to.includes("#")) window.scrollTo({ top: 0, behavior: "smooth" }); }}
                    data-testid={`pipeline-step-${s.id}`}
                    className={`font-mono text-[11px] uppercase tracking-wider px-2.5 py-1.5 rounded transition-colors ${
                      active ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40" : "text-slate-400 hover:text-slate-100 border border-transparent"
                    }`}
                  >
                    <span className="text-slate-600 mr-1">{String(i + 1).padStart(2, "0")}</span>
                    {s.label}
                  </Link>
                  {i < STEPS.length - 1 && <ChevronRight className="h-3 w-3 text-slate-700 mx-0.5" />}
                </div>
              );
            })}
          </nav>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
};
