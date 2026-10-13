import { useEffect, useState } from "react";
import {
  Bar, Brush, CartesianGrid, ComposedChart, Legend, Line, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Point, RegionRisk, getJSON } from "./client";

export default function Analytics({ token }: { token: string }) {
  const [regions, setRegions] = useState<RegionRisk[]>([]);
  const [rid, setRid] = useState("KZN-ETHEKWINI");
  const [pts, setPts] = useState<Point[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    getJSON<RegionRisk[]>("/regions/risk", token).then(setRegions).catch((e: Error) => setErr(e.message));
  }, [token]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    getJSON<Point[]>(`/regions/${encodeURIComponent(rid)}/timeseries?limit=200`, token)
      .then((p) => alive && (setPts(p), setErr("")))
      .catch((e: Error) => alive && setErr(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [rid, token]);

  const data = pts.map((p) => ({
    label: new Date(p.t).toLocaleString([], { day: "2-digit", month: "short", hour: "2-digit" }),
    rainfall: p.rainfall,
    river: p.river_level,
    risk: Math.round(p.risk * 100),
    novel: p.novel,
  }));
  const latest = data.length ? data[data.length - 1] : null;

  return (
    <section>
      <div className="row">
        <h2>Time-series analytics</h2>
        <label className="inline">
          Region
          <select value={rid} onChange={(e) => setRid(e.target.value)}>
            {(regions.length ? regions.map((r) => r.id) : [rid]).map((id) => (
              <option key={id} value={id}>{regions.find((r) => r.id === id)?.name ?? id}</option>
            ))}
          </select>
        </label>
      </div>
      {err && <p role="alert" className="error">{err}</p>}
      {loading && <div className="skeleton" aria-busy="true" />}
      {!loading && data.length === 0 && (
        <p className="muted">No readings for this region yet. Run scripts/seed_demo.py or ingest data.</p>
      )}
      {data.length > 0 && (
        <div className="card chart">
          <p className="muted">
            Bars: 24h rainfall (mm). Solid line: river level (m). Dashed line: predicted risk (%). Red dots: unrecognised
            pattern. Drag the strip below the chart to zoom.
          </p>
          <ResponsiveContainer width="100%" height={380}>
            <ComposedChart data={data}>
              <CartesianGrid stroke="rgba(255,255,255,.1)" />
              <XAxis dataKey="label" stroke="#9fb0c7" minTickGap={30} />
              <YAxis yAxisId="left" stroke="#9fb0c7" />
              <YAxis yAxisId="risk" orientation="right" domain={[0, 100]} stroke="#9fb0c7" />
              <Tooltip contentStyle={{ background: "#0f1a30", border: "1px solid rgba(255,255,255,.2)" }} />
              <Legend />
              <Bar yAxisId="left" dataKey="rainfall" name="Rainfall mm" fill="#4da3ff" />
              <Line yAxisId="left" type="monotone" dataKey="river" name="River level m" stroke="#2ecc9a" dot={false} />
              <Line yAxisId="risk" type="monotone" dataKey="risk" name="Risk %" stroke="#ffb020" strokeDasharray="6 3" dot={false} />
              {data.filter((d) => d.novel).map((d) => (
                <ReferenceDot key={d.label} x={d.label} y={d.risk} yAxisId="risk" r={6} fill="#ff4d5e" stroke="#fff" />
              ))}
              <Brush dataKey="label" height={24} stroke="#4da3ff" />
            </ComposedChart>
          </ResponsiveContainer>
          {latest && <p>Latest predicted risk: {latest.risk}%</p>}
        </div>
      )}
    </section>
  );
}
