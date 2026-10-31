import { Link } from "react-router-dom";
import { ArrowRight, Puzzle } from "lucide-react";

export default function StagePlaceholder({ stage }) {
  return (
    <div className="max-w-3xl mx-auto px-6 py-24" data-testid="stage-placeholder">
      <Puzzle className="h-10 w-10 text-slate-500 mb-6" />
      <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight mb-4">{stage}</h1>
      <p className="text-slate-400 leading-relaxed mb-8">
        This stage belongs to the existing UrbanShield AI application. Its code was not present in this workspace,
        so only the Power Monitoring module is implemented here. Once the existing module is merged, this route
        will show it in place of this notice.
      </p>
      <Link
        to="/power"
        data-testid="go-to-power-link"
        className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-wider px-4 py-2 rounded border border-cyan-500/40 text-cyan-300 hover:bg-cyan-500/10 transition-colors"
      >
        Open AC Power Monitoring <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
