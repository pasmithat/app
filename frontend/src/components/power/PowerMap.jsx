import { MapContainer, TileLayer, CircleMarker, Circle, Tooltip } from "react-leaflet";
import { SEV, fmt } from "./format";

const Legend = ({ hidden }) => (
  <div className="absolute bottom-3 left-3 z-[500] bg-[#121824] border border-slate-700 rounded p-2.5 font-mono text-[10px] space-y-1" data-testid="map-legend">
    {Object.entries(SEV).map(([k, v]) => (
      <div key={k} className="flex items-center gap-2 text-slate-300">
        <span className="h-2.5 w-2.5 rounded-full" style={{ background: v.color }} /> {v.label}
      </div>
    ))}
    <div className="text-slate-500 pt-1 border-t border-slate-800">Ring = zone AC demand</div>
    {hidden > 0 && <div className="text-amber-300" data-testid="map-hidden-count">{hidden} building(s) hidden: no coordinates</div>}
  </div>
);

export const PowerMap = ({ buildings, zones, zone, buildingId, onBuilding, onZone }) => {
  const located = buildings.filter((b) => b.latitude !== null && b.longitude !== null);
  const maxDemand = Math.max(1, ...zones.map((z) => z.current_demand_kw || 0));
  return (
    <div className="relative h-[420px] lg:h-full min-h-[420px] rounded overflow-hidden border border-slate-800" data-testid="chennai-leaflet-map">
      <MapContainer center={[13.0, 80.2]} zoom={11} scrollWheelZoom={false} className="h-full w-full">
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
          className="dark-tiles"
        />
        {zones.map((z) => (
          <Circle
            key={z.zone_name}
            center={[z.latitude, z.longitude]}
            radius={600 + 1800 * ((z.current_demand_kw || 0) / maxDemand)}
            pathOptions={{
              color: zone === z.zone_name ? "#00F0FF" : SEV[z.severity].color,
              weight: zone === z.zone_name ? 2 : 1,
              fillOpacity: 0.06,
              dashArray: "4 4",
            }}
            eventHandlers={{ click: () => onZone(z.zone_name) }}
          >
            <Tooltip>
              <div className="font-mono text-xs">
                <b>{z.zone_name}</b><br />AC demand {fmt(z.current_demand_kw, 1)} kW<br />
                Utilisation {fmt(z.capacity_utilization_pct, 1)}%
              </div>
            </Tooltip>
          </Circle>
        ))}
        {located.map((b) => {
          const sel = b.building_id === buildingId;
          const warn = b.severity === "high" || b.severity === "exceeded";
          return (
            <CircleMarker
              key={b.building_id}
              center={[b.latitude, b.longitude]}
              radius={sel ? 11 : warn ? 9 : 6}
              pathOptions={{ color: sel ? "#00F0FF" : warn ? "#fff" : SEV[b.severity].color, weight: sel || warn ? 2 : 1, fillColor: SEV[b.severity].color, fillOpacity: 0.9 }}
              eventHandlers={{ click: () => onBuilding(b) }}
            >
              <Tooltip direction="top">
                <div className="font-mono text-xs">
                  <b>{b.building_name}</b><br />{fmt(b.current_demand_kw, 1)} kW / {fmt(b.available_capacity_kw, 0)} kW<br />
                  {fmt(b.utilization_pct, 1)}% · {SEV[b.severity].label}{warn ? " · overload warning" : ""}
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
      <Legend hidden={buildings.length - located.length} />
      <div className="sr-only" data-testid="map-marker-count">{located.length}</div>
    </div>
  );
};
