import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { Level, RegionRisk, getJSON } from "./client";

const LEVEL: Record<Level, { icon: string; color: string; label: string }> = {
  critical: { icon: "\u26D4", color: "#ff4d5e", label: "Critical" },
  warning: { icon: "\u26A0", color: "#ffb020", label: "Warning" },
  watch: { icon: "\u25C9", color: "#4da3ff", label: "Watch" },
  low: { icon: "\u2713", color: "#2ecc9a", label: "Low" },
  unknown: { icon: "?", color: "#9fb0c7", label: "No data" },
};

const pct = (v: number | null) => (v === null ? "-" : `${Math.round(v * 100)}%`);

export default function RiskMap({ token }: { token: string }) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const layer = useRef<L.LayerGroup | null>(null);
  const base = useRef<L.TileLayer | null>(null);
  const fitted = useRef(false);
  const [regions, setRegions] = useState<RegionRisk[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [basemap, setBasemap] = useState(false);

  useEffect(() => {
    if (!el.current || map.current) return;
    const m = L.map(el.current).setView([-28.0, 30.5], 6);
    layer.current = L.layerGroup().addTo(m);
    map.current = m;
    return () => {
      m.remove();
      map.current = null;
      fitted.current = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    const load = () =>
      getJSON<RegionRisk[]>("/regions/risk", token)
        .then((r) => alive && (setRegions(r), setErr("")))
        .catch((e: Error) => alive && setErr(e.message))
        .finally(() => alive && setLoading(false));
    load();
    const t = window.setInterval(load, 15000);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, [token]);

  useEffect(() => {
    const m = map.current;
    const g = layer.current;
    if (!m || !g) return;
    g.clearLayers();
    regions.forEach((r) => {
      const lv = LEVEL[r.level];
      const div = document.createElement("div");
      div.className = `marker ${r.level}`;
      div.style.borderColor = lv.color;
      div.textContent = `${lv.icon} ${pct(r.risk)}`;
      const icon = L.divIcon({ html: div, className: "", iconSize: [78, 28] });
      L.marker([r.lat, r.lon], { icon, title: `${r.name}: ${lv.label}`, keyboard: true })
        .on("click", () => setSelectedId(r.id))
        .addTo(g);
    });
    if (regions.length && !fitted.current) {
      m.fitBounds(L.latLngBounds(regions.map((r): L.LatLngTuple => [r.lat, r.lon])).pad(0.3));
      fitted.current = true;
    }
  }, [regions]);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    if (basemap && !base.current) {
      base.current = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "\u00A9 OpenStreetMap contributors",
      }).addTo(m);
    } else if (!basemap && base.current) {
      base.current.remove();
      base.current = null;
    }
  }, [basemap]);

  const selected = regions.find((r) => r.id === selectedId) ?? null;
  const sorted = [...regions].sort((a, b) => (b.risk ?? -1) - (a.risk ?? -1));

  return (
    <section className="mapgrid">
      <div>
        <div className="row">
          <h2>Risk map</h2>
          <label className="inline">
            <input type="checkbox" checked={basemap} onChange={(e) => setBasemap(e.target.checked)} />
            Basemap (needs internet)
          </label>
        </div>
        {err && <p role="alert" className="error">{err}</p>}
        {loading && <div className="skeleton" aria-busy="true" />}
        <div ref={el} className="map" aria-label="Map of district flood risk" />
        <p className="muted">
          Markers sit at approximate district seats. Level is shown by icon and label as well as colour.
        </p>
      </div>
      <aside className="card">
        <h3>Regions by risk</h3>
        {regions.length === 0 && !loading && (
          <p className="muted">No regions yet. Run scripts/seed_demo.py or ingest a reading.</p>
        )}
        <ul className="regionlist">
          {sorted.map((r) => (
            <li key={r.id}>
              <button className="secondary" onClick={() => setSelectedId(r.id)}>
                {LEVEL[r.level].icon} {r.name} - {pct(r.risk)}
              </button>
            </li>
          ))}
        </ul>
        {selected && (
          <div className="drawer">
            <h3>{selected.name}</h3>
            <p>{selected.province}</p>
            <p>
              {LEVEL[selected.level].icon} {LEVEL[selected.level].label} - risk {pct(selected.risk)} - confidence{" "}
              {pct(selected.confidence)}
            </p>
            {selected.degraded && <p className="badge">{"\u25D0"} Reduced confidence: satellite feed unavailable</p>}
            {selected.novel && <p className="badge">Unrecognised pattern (possible novel event)</p>}
            <p className="muted">
              Updated {selected.updated_at ? new Date(selected.updated_at).toLocaleString() : "never"}
            </p>
          </div>
        )}
      </aside>
    </section>
  );
}
