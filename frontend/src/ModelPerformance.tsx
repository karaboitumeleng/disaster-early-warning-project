import { useEffect, useState, ReactNode } from "react";

// --- TYPES ---

export type SatelliteFeedMetrics = {
  provider: string;
  uplink_latency_mins: number;
  coverage_pct: number;
  cloud_mask_accuracy: number;
  status: "optimal" | "degraded" | "offline";
};

export type SensorNetworkMetrics = {
  active_stations: number;
  total_stations: number;
  packet_loss_pct: number;
  gauge_uptime_pct: number;
  calibration_drift_pct: number;
};

export type ExtendedModelMetrics = {
  available: boolean;
  note?: string;
  active_model_version?: string;
  dataset_version?: string;
  smart_target?: number;
  smart_target_met?: boolean;

  // Predictive Quality Metrics
  forecast_accuracy?: number;
  alert_precision?: number;
  recall?: number;
  f1_score?: number;
  false_alarm_rate?: number;
  anomaly_score?: number;
  rmse?: number;

  // Latency & System Performance
  latency_p50_ms?: number;
  latency_p95_ms?: number;
  latency_p99_ms?: number;
  throughput_rps?: number;
  model_drift_index?: number;

  // Telemetry Sources
  satellite_feeds?: SatelliteFeedMetrics[];
  sensor_network?: SensorNetworkMetrics;

  [key: string]: unknown;
};

// --- MOCK DATA ---

const SAMPLE_METRICS: ExtendedModelMetrics = {
  available: true,
  note: "Sample telemetry data shown because no API token was provided.",
  active_model_version: "sample-v1.4.2",
  dataset_version: "SA-hydro-2024Q3",
  smart_target: 0.8,
  smart_target_met: true,

  forecast_accuracy: 92.4,
  alert_precision: 88.1,
  recall: 86.7,
  f1_score: 87.4,
  false_alarm_rate: 11.3,
  anomaly_score: 0.71,
  rmse: 0.042,

  latency_p50_ms: 14.2,
  latency_p95_ms: 38.6,
  latency_p99_ms: 82.1,
  throughput_rps: 420,
  model_drift_index: 0.031,

  satellite_feeds: [
    {
      provider: "Meteosat-11 (SEVIRI)",
      uplink_latency_mins: 12,
      coverage_pct: 99.4,
      cloud_mask_accuracy: 94.2,
      status: "optimal",
    },
    {
      provider: "Sentinel-3 (OLCI / SLSTR)",
      uplink_latency_mins: 42,
      coverage_pct: 96.1,
      cloud_mask_accuracy: 91.8,
      status: "optimal",
    },
    {
      provider: "Landsat-9 (Thermal/SWIR)",
      uplink_latency_mins: 105,
      coverage_pct: 88.5,
      cloud_mask_accuracy: 89.0,
      status: "degraded",
    },
  ],

  sensor_network: {
    active_stations: 412,
    total_stations: 425,
    packet_loss_pct: 0.82,
    gauge_uptime_pct: 98.9,
    calibration_drift_pct: 1.15,
  },
};

// --- API FETCH FUNCTION ---

async function getModelMetrics(token: string): Promise<ExtendedModelMetrics> {
  const response = await fetch("/api/model-metrics", {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Model metrics request failed (${response.status})`);
  }

  return (await response.json()) as ExtendedModelMetrics;
}

// --- MAIN COMPONENT ---

export default function ModelPerformance({ token = "" }: { token?: string }) {
  const [metrics, setMetrics] = useState<ExtendedModelMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (!token) {
      setMetrics(SAMPLE_METRICS);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    getModelMetrics(token)
      .then((data) => {
        const responseData = (data as any)?.data ?? data;

        if (responseData) {
          setMetrics({
            ...responseData,
            available: responseData.available ?? true,
          } as ExtendedModelMetrics);
        } else {
          setMetrics(SAMPLE_METRICS);
        }
      })
      .catch((e: Error) => {
        setError(e.message || "Failed to fetch model telemetry.");
        setMetrics(SAMPLE_METRICS);
      })
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-8 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm animate-pulse text-xs text-slate-400 flex items-center justify-center gap-3">
        <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
        <span>Loading live system telemetry & observation feeds...</span>
      </div>
    );
  }

  return (
    <div className="model-perf max-w-6xl mx-auto space-y-6 text-slate-100 font-sans p-2 sm:p-4">
      {/* Warning Banner */}
      {error && (
        <div
          role="alert"
          className="px-4 py-3 bg-rose-950/40 border border-rose-800/60 text-rose-300 rounded-xl text-xs flex items-center justify-between gap-3 shadow-lg"
        >
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
            <span>
              <strong>API Fetch Warning:</strong> {error} (Displaying sample telemetry fallback)
            </span>
          </div>
        </div>
      )}

      {/* Inactive or Missing Model Banner */}
      {(!metrics || !metrics.available) && (
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-white">Model Status</h3>
            <span className="px-3 py-1 text-xs rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-medium">
              ◐ No Trained Model Active
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-2">{metrics?.note}</p>
          <div className="mt-4 pt-4 border-t border-slate-800/80 text-xs text-slate-400">
            Currently serving fallback predictions from:{" "}
            <strong className="text-slate-200 font-mono">
              {metrics?.active_model_version ?? "N/A"}
            </strong>
          </div>
        </Card>
      )}

      {/* Main Dashboard Grid */}
      {metrics && metrics.available && (
        <>
          {/* Header Overview Card */}
          <Card className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-3">
                  <h2 className="text-xl font-bold tracking-tight text-white">
                    Model & Telemetry Dashboard
                  </h2>
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Live Engine
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Active Model:{" "}
                  <span className="text-blue-400 font-mono font-semibold">
                    {metrics.active_model_version}
                  </span>{" "}
                  · Dataset:{" "}
                  <span className="text-slate-300 font-mono">
                    {metrics.dataset_version}
                  </span>
                </p>
              </div>

              {/* SMART Target Indicator */}
              <div className="flex items-center gap-4 bg-slate-950/60 px-4 py-2.5 rounded-xl border border-slate-800">
                <div className="text-right">
                  <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider block">
                    SMART Target (≥
                    {((metrics.smart_target ?? 0.8) * 100).toFixed(0)}%)
                  </span>
                  <span
                    className={`text-xs font-bold tracking-wide ${
                      metrics.smart_target_met
                        ? "text-emerald-400"
                        : "text-rose-400"
                    }`}
                  >
                    {metrics.smart_target_met ? "✓ TARGET MET" : "✕ TARGET UNMET"}
                  </span>
                </div>
              </div>
            </div>
          </Card>

          {/* Section 1: Predictive Quality */}
          <Section label="Model Accuracy & Predictive Quality">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <MetricStat
                label="Forecast Accuracy"
                value={`${metrics.forecast_accuracy}%`}
                progress={metrics.forecast_accuracy}
              />
              <MetricStat
                label="Alert Precision"
                value={`${metrics.alert_precision}%`}
                progress={metrics.alert_precision}
              />
              <MetricStat
                label="Recall Rate"
                value={`${metrics.recall}%`}
                progress={metrics.recall}
              />
              <MetricStat label="F1 Score" value={`${metrics.f1_score}%`} />
              <MetricStat
                label="False Alarm Rate"
                value={`${metrics.false_alarm_rate}%`}
                status={
                  (metrics.false_alarm_rate ?? 0) < 15 ? "good" : "warning"
                }
              />
              <MetricStat label="RMSE" value={`${metrics.rmse}`} />
            </div>
          </Section>

          {/* Section 2: Inference & System Latency */}
          <Section label="Inference Performance & Pipeline Metrics">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              <MetricStat
                label="p50 Latency"
                value={`${metrics.latency_p50_ms} ms`}
                subtext="Median inference time"
              />
              <MetricStat
                label="p95 Latency"
                value={`${metrics.latency_p95_ms} ms`}
                subtext="95th percentile limit"
              />
              <MetricStat
                label="p99 Latency"
                value={`${metrics.latency_p99_ms} ms`}
                subtext="Tail latency bound"
              />
              <MetricStat
                label="Throughput"
                value={`${metrics.throughput_rps} rps`}
                subtext="Active pipeline load"
              />
              <MetricStat
                label="Drift Index"
                value={`${metrics.model_drift_index}`}
                subtext={
                  (metrics.model_drift_index ?? 0) < 0.05
                    ? "Normal distribution"
                    : "Drift warning"
                }
                status={
                  (metrics.model_drift_index ?? 0) < 0.05 ? "good" : "warning"
                }
              />
            </div>
          </Section>

          {/* Section 3: Sensor Telemetry & Observation Feeds */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Satellite Feeds */}
            <Card className="lg:col-span-2 p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-base">🛰️</span>
                  <h3 className="text-sm font-bold text-white tracking-wide">
                    Satellite Earth Observation Feeds
                  </h3>
                </div>
                <span className="text-[11px] text-slate-400">
                  Uplink & Spatial Coverage
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider border-b border-slate-800/80">
                      <th className="pb-2.5 font-semibold">Instrument / Provider</th>
                      <th className="pb-2.5 font-semibold">Uplink Sync</th>
                      <th className="pb-2.5 font-semibold">Coverage</th>
                      <th className="pb-2.5 font-semibold">Cloud Mask Acc.</th>
                      <th className="pb-2.5 font-semibold text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {metrics.satellite_feeds?.map((feed, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/20 transition-colors">
                        <td className="py-3 font-medium text-slate-200">
                          {feed.provider}
                        </td>
                        <td className="py-3 font-mono text-slate-300">
                          {feed.uplink_latency_mins} min ago
                        </td>
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            <span className="font-mono">{feed.coverage_pct}%</span>
                            <ProgressBar percentage={feed.coverage_pct} />
                          </div>
                        </td>
                        <td className="py-3 font-mono text-slate-300">
                          {feed.cloud_mask_accuracy}%
                        </td>
                        <td className="py-3 text-right">
                          <StatusBadge status={feed.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            {/* In-Situ Ground Gauge Network */}
            <Card className="p-5 flex flex-col justify-between space-y-4">
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-base">🌊</span>
                    <h3 className="text-sm font-bold text-white tracking-wide">
                      Ground Gauge Telemetry
                    </h3>
                  </div>
                </div>

                {metrics.sensor_network && (
                  <div className="space-y-3.5 text-xs">
                    {/* Station Ratio with visual progress bar */}
                    <div>
                      <div className="flex justify-between items-center mb-1 text-slate-400">
                        <span>Active Sensor Stations</span>
                        <span className="font-bold text-white font-mono">
                          {metrics.sensor_network.active_stations} /{" "}
                          {metrics.sensor_network.total_stations}
                        </span>
                      </div>
                      <ProgressBar
                        percentage={
                          (metrics.sensor_network.active_stations /
                            metrics.sensor_network.total_stations) *
                          100
                        }
                      />
                    </div>

                    <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                      <span className="text-slate-400">Gauge Network Uptime</span>
                      <span className="font-bold text-emerald-400 font-mono">
                        {metrics.sensor_network.gauge_uptime_pct}%
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                      <span className="text-slate-400">IoT Packet Loss</span>
                      <span className="font-bold text-slate-200 font-mono">
                        {metrics.sensor_network.packet_loss_pct}%
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-1.5">
                      <span className="text-slate-400">Calibration Drift</span>
                      <span className="font-bold text-amber-400 font-mono">
                        ±{metrics.sensor_network.calibration_drift_pct}%
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800 text-[11px] text-slate-400 flex items-start gap-2">
                <span className="text-blue-400">ℹ</span>
                <span>
                  Telemetry continuously synced across LoRaWAN & Satellite IoT uplinks.
                </span>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

// --- SUB-COMPONENTS ---

function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`bg-slate-900/90 border border-slate-800 rounded-2xl shadow-sm backdrop-blur-sm ${className}`}
    >
      {children}
    </div>
  );
}

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 px-1">
        {label}
      </h3>
      {children}
    </div>
  );
}

function MetricStat({
  label,
  value,
  subtext,
  progress,
  status = "neutral",
}: {
  label: string;
  value: string;
  subtext?: string;
  progress?: number;
  status?: "neutral" | "good" | "warning";
}) {
  const statusColors = {
    neutral: "text-white",
    good: "text-emerald-400",
    warning: "text-amber-400",
  };

  return (
    <Card className="p-3.5 flex flex-col justify-between space-y-2 hover:border-slate-700/80 transition-colors">
      <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider truncate">
        {label}
      </span>
      <div>
        <div className={`text-lg font-extrabold tracking-tight font-mono ${statusColors[status]}`}>
          {value}
        </div>
        {subtext && (
          <span className="text-[10px] text-slate-400 block mt-0.5 leading-tight">
            {subtext}
          </span>
        )}
      </div>
      {typeof progress === "number" && (
        <ProgressBar percentage={progress} className="mt-1" />
      )}
    </Card>
  );
}

function ProgressBar({
  percentage,
  className = "",
}: {
  percentage: number;
  className?: string;
}) {
  return (
    <div className={`w-full bg-slate-950 h-1.5 rounded-full overflow-hidden border border-slate-800/60 ${className}`}>
      <div
        className="bg-blue-500 h-full rounded-full transition-all duration-500"
        style={{ width: `${Math.min(100, Math.max(0, percentage))}%` }}
      />
    </div>
  );
}

function StatusBadge({ status }: { status: "optimal" | "degraded" | "offline" }) {
  const styles = {
    optimal: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    degraded: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    offline: "bg-rose-500/10 text-rose-400 border-rose-500/20",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-[10px] font-semibold rounded-full border capitalize ${styles[status]}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          status === "optimal"
            ? "bg-emerald-400 animate-pulse"
            : status === "degraded"
            ? "bg-amber-400"
            : "bg-rose-400"
        }`}
      />
      {status}
    </span>
  );
}