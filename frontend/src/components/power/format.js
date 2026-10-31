export const fmt = (n, d = 0) =>
  n === null || n === undefined || Number.isNaN(Number(n))
    ? "—"
    : Number(n).toLocaleString("en-IN", { maximumFractionDigits: d, minimumFractionDigits: d });

export const inr = (n) => (n === null || n === undefined ? "—" : `₹${fmt(n, 0)}`);

export const signed = (n, d = 0, suffix = "") =>
  n === null || n === undefined ? "—" : `${n > 0 ? "+" : ""}${fmt(n, d)}${suffix}`;

export const SEV = {
  normal: { label: "Normal", color: "#34C759", cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
  moderate: { label: "Moderate", color: "#EAB308", cls: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30" },
  high: { label: "High", color: "#F97316", cls: "bg-orange-500/15 text-orange-400 border-orange-500/30" },
  exceeded: { label: "Exceeded", color: "#EF4444", cls: "bg-red-500/15 text-red-400 border-red-500/40" },
};

export const ZONES = [
  "T. Nagar", "Anna Nagar", "Velachery", "Guindy", "Adyar",
  "Tambaram", "Perungudi", "Sholinganallur", "Ambattur", "Porur",
];

export const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-");
