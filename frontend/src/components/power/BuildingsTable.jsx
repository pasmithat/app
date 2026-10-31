import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { SevBadge, SimBadge } from "./Badges";
import { fmt } from "./format";

const COLS = ["Building", "Zone", "AC units", "Rating (kW)", "Status", "Demand (kW)", "Daily energy (kWh)", "Capacity (kW)", "Utilisation", "Source"];

export const BuildingsTable = ({ buildings, buildingId, onSelect }) => (
  <div className="panel overflow-hidden" data-testid="buildings-data-table">
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="border-slate-800 hover:bg-transparent">
            {COLS.map((c) => (
              <TableHead key={c} className="font-mono text-[10px] uppercase tracking-wider text-slate-500 whitespace-nowrap">{c}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {buildings.map((b) => (
            <TableRow
              key={b.building_id}
              data-testid={`building-row-${b.building_id}`}
              onClick={() => onSelect(b)}
              className={`cursor-pointer border-slate-800/70 transition-colors ${b.building_id === buildingId ? "bg-cyan-500/10" : "hover:bg-[#1A2333]"}`}
            >
              <TableCell className="font-medium text-slate-100 whitespace-nowrap">
                {b.building_name}
                <div className="font-mono text-[10px] text-slate-500">{b.building_id}{b.latitude === null ? " · no coordinates" : ""}</div>
              </TableCell>
              <TableCell className="text-slate-300 whitespace-nowrap">{b.zone_name}</TableCell>
              <TableCell className="font-mono text-slate-300">{b.ac_units_operating}/{b.ac_units}</TableCell>
              <TableCell className="font-mono text-slate-300">{fmt(b.ac_power_rating_kw, 2)}</TableCell>
              <TableCell>
                <span className={`font-mono text-[11px] ${b.operating_status === "Operating" ? "text-cyan-300" : "text-slate-500"}`}>{b.operating_status}</span>
                <div className="font-mono text-[10px] text-slate-500">{b.occupancy_status}</div>
              </TableCell>
              <TableCell className="font-mono text-slate-100" data-testid={`building-demand-${b.building_id}`}>{fmt(b.current_demand_kw, 1)}</TableCell>
              <TableCell className="font-mono text-slate-300">{fmt(b.daily_energy_kwh, 0)}</TableCell>
              <TableCell className="font-mono text-slate-300">{fmt(b.available_capacity_kw, 0)}</TableCell>
              <TableCell className="whitespace-nowrap">
                <span className="font-mono text-slate-100 mr-2" data-testid={`building-util-${b.building_id}`}>{fmt(b.utilization_pct, 1)}%</span>
                <SevBadge sev={b.severity} testId={`building-sev-${b.building_id}`} />
              </TableCell>
              <TableCell><SimBadge source={b.data_source} testId={`building-source-${b.building_id}`} /></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  </div>
);
