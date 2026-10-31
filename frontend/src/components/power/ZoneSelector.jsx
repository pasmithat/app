import { X } from "lucide-react";
import { ZONES, slug } from "./format";

export const ZoneSelector = ({ zone, buildingName, onZone, onClear }) => (
  <div className="flex flex-col gap-3" data-testid="zone-selector-container">
    <div className="flex flex-wrap gap-1.5">
      <button
        type="button"
        data-testid="zone-pill-all"
        onClick={() => onZone(null)}
        className={`font-mono text-[11px] uppercase tracking-wider px-3 py-1.5 rounded-full border transition-colors ${
          !zone ? "bg-cyan-400 text-[#0B0F17] border-cyan-400" : "border-slate-700 text-slate-400 hover:border-cyan-500/50 hover:text-slate-100"
        }`}
      >
        All Chennai zones (10)
      </button>
      {ZONES.map((z) => (
        <button
          key={z}
          type="button"
          data-testid={`zone-pill-${slug(z)}`}
          onClick={() => onZone(z)}
          className={`font-mono text-[11px] uppercase tracking-wider px-3 py-1.5 rounded-full border transition-colors ${
            zone === z ? "bg-cyan-400 text-[#0B0F17] border-cyan-400" : "border-slate-700 text-slate-400 hover:border-cyan-500/50 hover:text-slate-100"
          }`}
        >
          {z}
        </button>
      ))}
    </div>
    <div className="flex items-center gap-2 font-mono text-xs text-slate-400" data-testid="current-scope">
      <span className="text-slate-600">SCOPE</span>
      <span>Chennai</span>
      {zone && <span>› {zone}</span>}
      {buildingName && <span className="text-cyan-300">› {buildingName}</span>}
      {(zone || buildingName) && (
        <button type="button" onClick={onClear} data-testid="clear-scope-button" className="ml-2 inline-flex items-center gap-1 text-slate-500 hover:text-red-300">
          <X className="h-3 w-3" /> clear
        </button>
      )}
    </div>
  </div>
);
