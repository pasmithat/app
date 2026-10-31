import { useCallback, useEffect, useRef, useState } from "react";
import { RotateCcw, AlertOctagon, ShieldCheck } from "lucide-react";
import { Slider } from "../ui/slider";
import { Switch } from "../ui/switch";
import { Input } from "../ui/input";
import { api, errMsg } from "@/lib/api";
import { SevBadge } from "./Badges";
import { fmt, inr, signed } from "./format";

const FIELDS = [
  { k: "outdoor_temp_c", label: "Outdoor temperature", unit: "°C", min: () => 20, max: () => 50, step: 0.5 },
  { k: "ac_units", label: "Operating AC units", unit: "units", min: () => 0, max: (b) => Math.max(10, Math.ceil(b * 2)), step: 1 },
  { k: "ac_power_rating_kw", label: "AC power rating", unit: "kW", min: () => 0.5, max: () => 10, step: 0.05 },
  { k: "operating_hours", label: "Operating hours / day", unit: "h", min: () => 0, max: () => 24, step: 0.5 },
  { k: "occupied_buildings", label: "Occupied buildings", unit: "", min: () => 0, max: (b, n) => n, step: 1 },
  { k: "tariff_inr_per_kwh", label: "Electricity tariff", unit: "₹/kWh", min: () => 0, max: () => 20, step: 0.25 },
  { k: "available_capacity_kw", label: "Available capacity", unit: "kW", min: () => 1, max: (b) => Math.ceil(b * 2), step: 1 },
];

const Row = ({ label, base, sim, render, testId }) => (
  <div className="grid grid-cols-3 gap-2 py-2 border-b border-slate-800/70 text-sm" data-testid={testId}>
    <span className="text-slate-400">{label}</span>
    <span className="font-mono text-slate-300 text-right" data-testid={`${testId}-baseline`}>{render(base)}</span>
    <span className="font-mono text-cyan-300 text-right" data-testid={`${testId}-simulated`}>{render(sim)}</span>
  </div>
);

const FieldControl = ({ f, value, base, buildings, onChange }) => {
  const max = f.max(base, buildings);
  const changed = value !== base;
  return (
    <div data-testid={`sim-field-${f.k}`}>
      <div className="flex items-center justify-between mb-2">
        <span className={`text-sm ${changed ? "text-cyan-300" : "text-slate-300"}`}>{f.label}</span>
        <div className="flex items-center gap-1">
          <Input
            type="number"
            data-testid={`sim-input-${f.k}`}
            value={value}
            step={f.step}
            onChange={(e) => onChange(f.k, e.target.value === "" ? "" : Number(e.target.value))}
            className="h-7 w-24 text-right font-mono text-xs bg-[#0B0F17]"
          />
          <span className="font-mono text-[10px] text-slate-500 w-10">{f.unit}</span>
        </div>
      </div>
      <Slider
        data-testid={`sim-slider-${f.k}`}
        min={f.min(base)}
        max={Math.max(max, Number(value) || 0)}
        step={f.step}
        value={[Number(value) || 0]}
        onValueChange={([v]) => onChange(f.k, v)}
      />
      <div className="font-mono text-[10px] text-slate-600 mt-1">baseline {fmt(base, f.step < 1 ? 2 : 0)}</div>
    </div>
  );
};

export const WhatIfSimulator = ({ scope, buildingsCount }) => {
  const [base, setBase] = useState(null);
  const [values, setValues] = useState(null);
  const [temp, setTemp] = useState({ enabled: false, demand_change_pct_per_c: 3 });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const timer = useRef(null);

  const run = useCallback(async (overrides, t) => {
    try {
      const { data } = await api.post("/simulate", { ...scope, overrides, temperature_assumption: t });
      setResult(data);
      setError(null);
      return data;
    } catch (e) {
      setError(errMsg(e));
      return null;
    }
  }, [scope]);

  useEffect(() => {
    const t0 = { enabled: false, demand_change_pct_per_c: 3 };
    setTemp(t0);
    run({}, t0).then((d) => {
      if (d) {
        setBase(d.baseline.inputs);
        setValues(d.baseline.inputs);
      }
    });
  }, [run]);

  const schedule = (vals, t) => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const ov = Object.fromEntries(Object.entries(vals).filter(([k, v]) => v !== base[k] && v !== ""));
      run(ov, t);
    }, 250);
  };

  const change = (k, v) => {
    const next = { ...values, [k]: v };
    setValues(next);
    schedule(next, temp);
  };

  const changeTemp = (t) => {
    setTemp(t);
    schedule(values, t);
  };

  const reset = () => {
    clearTimeout(timer.current);
    const t0 = { enabled: false, demand_change_pct_per_c: 3 };
    setValues(base);
    setTemp(t0);
    run({}, t0);
  };

  if (!values) return <div className="panel p-6 text-slate-500 text-sm">{error || "Loading baseline…"}</div>;
  const b = result?.baseline;
  const s = result?.simulated;
  const c = result?.comparison;
  return (
    <div className="grid lg:grid-cols-5 gap-4" data-testid="what-if-power-simulator">
      <div className="panel p-5 lg:col-span-2 space-y-5">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] uppercase tracking-widest text-slate-400">Inputs</span>
          <button
            type="button"
            onClick={reset}
            data-testid="reset-baseline-button"
            className="inline-flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-cyan-500/40 font-mono text-xs font-bold px-4 py-2 rounded uppercase tracking-wider transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Reset to baseline
          </button>
        </div>
        {FIELDS.map((f) => (
          <FieldControl key={f.k} f={f} value={values[f.k]} base={base[f.k]} buildings={buildingsCount} onChange={change} />
        ))}
        <div className="border-t border-slate-800 pt-4">
          <label className="flex items-center justify-between text-sm text-slate-300">
            Apply temperature scenario assumption
            <Switch data-testid="temp-assumption-switch" checked={temp.enabled} onCheckedChange={(v) => changeTemp({ ...temp, enabled: v })} />
          </label>
          {temp.enabled && (
            <label className="flex items-center justify-between text-xs text-slate-400 mt-3">
              Demand change per °C above {base.outdoor_temp_c} °C (%)
              <Input
                type="number"
                step="0.5"
                data-testid="temp-assumption-pct"
                value={temp.demand_change_pct_per_c}
                onChange={(e) => changeTemp({ ...temp, demand_change_pct_per_c: Number(e.target.value) })}
                className="h-7 w-20 font-mono text-xs bg-[#0B0F17]"
              />
            </label>
          )}
          <p className="text-[11px] text-slate-500 mt-2">Off by default: outdoor temperature does not change demand unless you enable this documented assumption.</p>
        </div>
      </div>

      <div className="lg:col-span-3 space-y-4">
        {error && <div className="panel p-3 border-red-500/40 text-sm text-red-300" data-testid="sim-error">{error}</div>}
        {result?.overload_warning && (
          <div className="panel p-4 border-red-500/50 bg-red-500/10 flex gap-3" data-testid="sim-overload-warning">
            <AlertOctagon className="h-5 w-5 text-red-400 shrink-0" />
            <p className="text-sm text-red-200">{result.warnings[0]}</p>
          </div>
        )}
        {!result?.overload_warning && result?.warnings?.length > 0 && (
          <div className="panel p-3 border-orange-500/40 text-sm text-orange-200" data-testid="sim-warning">{result.warnings[0]}</div>
        )}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            ["Demand change", signed(c?.demand_change_pct, 1, "%"), "sim-demand-change-pct"],
            ["Δ Demand", signed(c?.demand_change_kw, 1, " kW"), "sim-demand-change-kw"],
            ["Δ Energy", signed(c?.energy_change_kwh, 0, " kWh"), "sim-energy-change"],
            ["Cost difference", c ? `${c.cost_difference_inr > 0 ? "+" : ""}${inr(c.cost_difference_inr)}` : "—", "sim-cost-difference"],
          ].map(([l, v, id]) => (
            <div key={id} className="panel p-3">
              <div className="font-mono text-[10px] uppercase tracking-widest text-slate-500">{l}</div>
              <div className="font-mono text-xl text-cyan-300 mt-1" data-testid={id}>{v}</div>
            </div>
          ))}
        </div>
        <div className="panel p-4">
          <div className="grid grid-cols-3 gap-2 font-mono text-[10px] uppercase tracking-widest text-slate-500 pb-2">
            <span>Metric</span><span className="text-right">Baseline</span><span className="text-right">Simulated</span>
          </div>
          <Row label="Electricity demand" base={b?.demand_kw} sim={s?.demand_kw} render={(v) => `${fmt(v, 1)} kW`} testId="sim-row-demand" />
          <Row label="Energy consumption" base={b?.energy_kwh} sim={s?.energy_kwh} render={(v) => `${fmt(v, 0)} kWh`} testId="sim-row-energy" />
          <Row label="Estimated cost" base={b?.cost_inr} sim={s?.cost_inr} render={inr} testId="sim-row-cost" />
          <Row label="Capacity utilisation" base={b?.utilization_pct} sim={s?.utilization_pct} render={(v) => `${fmt(v, 1)}%`} testId="sim-row-util" />
          <div className="grid grid-cols-3 gap-2 pt-2 text-sm">
            <span className="text-slate-400">Severity</span>
            <span className="text-right">{b && <SevBadge sev={b.severity} testId="sim-baseline-sev" />}</span>
            <span className="text-right">{s && <SevBadge sev={s.severity} testId="sim-simulated-sev" />}</span>
          </div>
        </div>
        <div className="panel p-4 text-xs text-slate-400 space-y-1" data-testid="sim-assumptions">
          {result?.assumptions.map((a) => <p key={a}>· {a}</p>)}
          {result && (
            <p className={`flex items-center gap-1.5 pt-2 font-mono ${result.baseline_unchanged ? "text-emerald-400" : "text-red-400"}`} data-testid="baseline-integrity">
              <ShieldCheck className="h-3.5 w-3.5" />
              {result.baseline_unchanged ? "Baseline data unchanged" : "Baseline data changed!"} · {result.baseline_fingerprint_after.slice(0, 12)}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
