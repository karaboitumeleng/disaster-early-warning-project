import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Reading, Region, listReadings } from "./api";

// Sample fallback regions if none are passed
const SAMPLE_REGIONS = [
  { id: "za-gp", name: "Gauteng Region" },
  { id: "za-wc", name: "Western Cape" },
  { id: "za-kzn", name: "KwaZulu-Natal" },
] as Region[];

// Sample fallback readings for immediate preview
const SAMPLE_READINGS: Reading[] = Array.from({ length: 12 }, (_, i) => {
  const time = new Date(Date.now() - (11 - i) * 2 * 3600 * 1000);
  return {
    id: `sample-${i}`,
    observed_at: time.toISOString(),
    rainfall_mm_24h: Number((Math.sin(i / 2) * 12 + 15).toFixed(1)),
    river_level_m: Number((Math.cos(i / 3) * 0.8 + 2.4).toFixed(2)),
    soil_moisture: Number((Math.sin(i / 2 + 1) * 10 + 42).toFixed(1)),
    temperature_c: Number((Math.cos(i / 3 + 1) * 4 + 21).toFixed(1)),
    humidity_pct: Number((Math.sin(i / 2 + 2) * 8 + 68).toFixed(1)),
  };
});

export default function TimeSeries({
  token = "",
  regions = SAMPLE_REGIONS,
}: {
  token?: string;
  regions?: Region[];
}) {
  const [regionId, setRegionId] = useState(regions[0]?.id ?? SAMPLE_REGIONS[0].id);
  const [readings, setReadings] = useState<Reading[]>(SAMPLE_READINGS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!regionId || !token) return;
    setLoading(true);
    setError("");
    listReadings(token, regionId)
      .then((data) => {
        if (data && data.length > 0) {
          setReadings(data);
        } else {
          setReadings(SAMPLE_READINGS);
        }
      })
      .catch((e: Error) => {
        setError(e.message);
        setReadings(SAMPLE_READINGS); // Fallback to sample data on error
      })
      .finally(() => setLoading(false));
  }, [token, regionId]);

  // Calculated KPI summary metrics
  const kpis = useMemo(() => {
    if (readings.length === 0) {
      return { totalRainfall: 0, peakRiver: 0, avgRiver: 0, count: 0 };
    }
    const totalRainfall = readings.reduce((acc, r) => acc + (r.rainfall_mm_24h || 0), 0);
    const peakRiver = Math.max(...readings.map((r) => r.river_level_m || 0));
    const avgRiver = readings.reduce((acc, r) => acc + (r.river_level_m || 0), 0) / readings.length;

    return {
      totalRainfall: totalRainfall.toFixed(1),
      peakRiver: peakRiver.toFixed(2),
      avgRiver: avgRiver.toFixed(2),
      count: readings.length,
    };
  }, [readings]);

  // Formatted chart data
  const data = useMemo(
    () =>
      readings.map((r) => ({
        time: new Date(r.observed_at).toLocaleString(undefined, {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        }),
        Rainfall: r.rainfall_mm_24h,
        "River level": r.river_level_m,
      })),
    [readings]
  );

  return (
    <div className="card chart-card bg-slate-900 text-slate-100 p-5 rounded-xl border border-slate-800 shadow-lg space-y-4">
      {/* Header & Region Selector */}
      <div className="chart-header flex justify-between items-center pb-2 border-b border-slate-800">
        <div>
          <h3 className="text-lg font-bold text-white">Time-Series Analytics</h3>
          <p className="text-xs text-slate-400">Regional rainfall & hydrologic trends</p>
        </div>
        <select
          value={regionId}
          onChange={(e) => setRegionId(e.target.value)}
          aria-label="Select region"
          className="bg-slate-800 text-slate-200 border border-slate-700 rounded px-3 py-1.5 text-xs font-medium focus:outline-none focus:border-blue-500"
        >
          {regions.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </div>

      {/* Compact KPI Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-slate-800/80 border border-slate-700/70 p-3 rounded-lg">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wide block">
            Total Precip
          </span>
          <span className="text-lg font-extrabold text-blue-400 mt-0.5 block">
            {kpis.totalRainfall} <span className="text-xs text-slate-400 font-normal">mm</span>
          </span>
        </div>

        <div className="bg-slate-800/80 border border-slate-700/70 p-3 rounded-lg">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wide block">
            Peak River Level
          </span>
          <span className="text-lg font-extrabold text-rose-400 mt-0.5 block">
            {kpis.peakRiver} <span className="text-xs text-slate-400 font-normal">m</span>
          </span>
        </div>

        <div className="bg-slate-800/80 border border-slate-700/70 p-3 rounded-lg">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wide block">
            Avg River Level
          </span>
          <span className="text-lg font-extrabold text-amber-400 mt-0.5 block">
            {kpis.avgRiver} <span className="text-xs text-slate-400 font-normal">m</span>
          </span>
        </div>

        <div className="bg-slate-800/80 border border-slate-700/70 p-3 rounded-lg">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wide block">
            Total Telemetry
          </span>
          <span className="text-lg font-extrabold text-emerald-400 mt-0.5 block">
            {kpis.count} <span className="text-xs text-slate-400 font-normal">points</span>
          </span>
        </div>
      </div>

      {/* Error & Loading Indicators */}
      {error && <p role="alert" className="error text-red-400 text-xs">{error}</p>}
      {loading && (
        <div
          className="skeleton h-[320px] w-full bg-slate-800/50 animate-pulse rounded-lg flex items-center justify-center text-slate-500 text-xs"
          aria-busy="true"
        >
          Loading telemetry data...
        </div>
      )}

      {/* Chart Visualization */}
      {!loading && data.length === 0 && (
        <p className="muted text-slate-500 text-center py-10 text-sm">
          No readings available for this region.
        </p>
      )}

      {!loading && data.length > 0 && (
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.08)" />
            <XAxis dataKey="time" tick={{ fill: "#8fa2c2", fontSize: 11 }} minTickGap={30} />
            <YAxis
              yAxisId="left"
              tick={{ fill: "#8fa2c2", fontSize: 11 }}
              label={{ value: "mm", angle: -90, position: "insideLeft", fill: "#8fa2c2", fontSize: 11 }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fill: "#8fa2c2", fontSize: 11 }}
              label={{ value: "m", angle: 90, position: "insideRight", fill: "#8fa2c2", fontSize: 11 }}
            />
            <Tooltip
              contentStyle={{
                background: "#0d1526",
                border: "1px solid rgba(255,255,255,.12)",
                borderRadius: 8,
                color: "#fff",
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ color: "#8fa2c2", fontSize: 12 }} />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="Rainfall"
              stroke="#4da3ff"
              dot={false}
              strokeWidth={2}
              connectNulls
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="River level"
              stroke="#ff4d5e"
              dot={false}
              strokeWidth={2}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}