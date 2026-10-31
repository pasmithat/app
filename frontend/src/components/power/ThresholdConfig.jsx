import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Input } from "../ui/input";
import { api, errMsg } from "@/lib/api";

const FIELDS = [
  { k: "moderate_pct", label: "Moderate from (%)" },
  { k: "high_pct", label: "High from (%)" },
  { k: "exceeded_pct", label: "Exceeded above (%)" },
  { k: "tariff_inr_per_kwh", label: "Tariff (₹/kWh)" },
];

export const ThresholdConfig = ({ settings, onSaved }) => {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (settings) {
      setForm({ moderate_pct: settings.moderate_pct, high_pct: settings.high_pct, exceeded_pct: settings.exceeded_pct, tariff_inr_per_kwh: settings.tariff_inr_per_kwh });
    }
  }, [settings]);

  const save = async (body) => {
    setSaving(true);
    try {
      await api.put("/thresholds", body);
      toast.success("Thresholds saved");
      onSaved();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSaving(false);
    }
  };

  if (!form) return null;
  return (
    <div className="panel p-4 space-y-3" data-testid="threshold-config">
      <div className="font-mono text-[11px] uppercase tracking-widest text-slate-400">Alert thresholds</div>
      <p className="text-xs text-slate-500">Utilisation = Current demand ÷ Available capacity × 100</p>
      {FIELDS.map((f) => (
        <label key={f.k} className="flex items-center justify-between gap-3 text-sm text-slate-300">
          {f.label}
          <Input
            type="number"
            step="0.5"
            data-testid={`threshold-${f.k}`}
            value={form[f.k]}
            onChange={(e) => setForm({ ...form, [f.k]: e.target.value })}
            className="w-24 font-mono bg-[#0B0F17]"
          />
        </label>
      ))}
      <div className="flex gap-2 pt-1">
        <button
          type="button"
          disabled={saving}
          data-testid="threshold-save-button"
          onClick={() => save(Object.fromEntries(Object.entries(form).map(([k, v]) => [k, Number(v)])))}
          className="flex-1 font-mono text-xs uppercase tracking-wider py-2 rounded bg-cyan-400 text-[#0B0F17] font-bold hover:bg-cyan-300 transition-colors disabled:opacity-50"
        >
          Save
        </button>
        <button
          type="button"
          disabled={saving}
          data-testid="threshold-defaults-button"
          onClick={() => save(settings.defaults || { moderate_pct: 70, high_pct: 85, exceeded_pct: 100, tariff_inr_per_kwh: 8 })}
          className="font-mono text-xs uppercase tracking-wider px-3 py-2 rounded border border-slate-700 text-slate-400 hover:text-slate-100 transition-colors"
        >
          Defaults
        </button>
      </div>
      <p className="text-[11px] text-slate-500">Default tariff ₹8/kWh is an editable demo assumption, not an official rate.</p>
    </div>
  );
};
