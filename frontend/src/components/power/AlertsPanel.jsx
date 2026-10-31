import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { SevBadge } from "./Badges";
import { fmt } from "./format";

const RULE_LABEL = {
  after_hours: "AC outside operating hours",
  unoccupied_high: "High use in unoccupied building",
  unexpected_increase: "Unexpected demand increase",
  continuous_operation: "Continuous AC operation",
  unusual_daily_pattern: "Unusual daily energy pattern",
};

const AlertCard = ({ a, onSelect, children }) => (
  <button
    type="button"
    data-testid={`alert-${a.id}`}
    onClick={() => onSelect(a)}
    className="panel w-full text-left p-4 hover:bg-[#1A2333] transition-colors"
  >
    <div className="flex flex-wrap items-center gap-2 mb-2">
      <SevBadge sev={a.severity} />
      <span className="font-medium text-slate-100">{a.building_name}</span>
      <span className="font-mono text-[10px] text-slate-500">{a.zone_name}</span>
    </div>
    {children}
    <p className="text-sm text-slate-300 mt-2"><span className="font-mono text-[10px] uppercase text-slate-500 mr-2">Reason</span>{a.reason}</p>
    <p className="text-sm text-cyan-200/90 mt-1"><span className="font-mono text-[10px] uppercase text-slate-500 mr-2">Action</span>{a.recommended_action}</p>
  </button>
);

const Empty = ({ text, testId }) => (
  <div className="panel p-6 text-center text-sm text-slate-500" data-testid={testId}>{text}</div>
);

export const AlertsPanel = ({ alerts, onSelect }) => (
  <Tabs defaultValue="overload" className="w-full">
    <TabsList className="bg-[#121824] border border-slate-800">
      <TabsTrigger value="overload" data-testid="alerts-tab-overload">Overload ({alerts?.overload.length ?? 0})</TabsTrigger>
      <TabsTrigger value="abnormal" data-testid="alerts-tab-abnormal">Abnormal use ({alerts?.abnormal.length ?? 0})</TabsTrigger>
    </TabsList>
    <TabsContent value="overload" className="space-y-2 mt-3" data-testid="overload-alerts-panel">
      <p className="text-xs text-amber-300/80 font-mono">{alerts?.note}</p>
      {alerts?.overload.length === 0 && <Empty text="All buildings in scope are below the moderate threshold." testId="overload-empty" />}
      {alerts?.overload.map((a) => (
        <AlertCard key={a.id} a={a} onSelect={onSelect}>
          <div className="grid grid-cols-3 gap-2 font-mono text-xs">
            <div><div className="text-slate-500 text-[10px]">DEMAND</div><span className="text-slate-100">{fmt(a.current_demand_kw, 1)} kW</span></div>
            <div><div className="text-slate-500 text-[10px]">CAPACITY</div><span className="text-slate-100">{fmt(a.available_capacity_kw, 0)} kW</span></div>
            <div><div className="text-slate-500 text-[10px]">UTILISATION</div><span className="text-slate-100">{fmt(a.utilization_pct, 1)}%</span></div>
          </div>
        </AlertCard>
      ))}
    </TabsContent>
    <TabsContent value="abnormal" className="space-y-2 mt-3" data-testid="abnormal-alerts-panel">
      <p className="text-xs text-slate-500 font-mono">Rule-based detection (not machine learning). Compares current vs same-hour history, schedule and occupancy.</p>
      {alerts?.abnormal.length === 0 && <Empty text="No abnormal consumption patterns in scope." testId="abnormal-empty" />}
      {alerts?.abnormal.map((a) => (
        <AlertCard key={a.id} a={a} onSelect={onSelect}>
          <span className="font-mono text-[11px] text-orange-300">{RULE_LABEL[a.rule]}</span>
          {a.evidence?.occupancy_note && <div className="font-mono text-[10px] text-slate-500">{a.evidence.occupancy_note}</div>}
        </AlertCard>
      ))}
    </TabsContent>
  </Tabs>
);
