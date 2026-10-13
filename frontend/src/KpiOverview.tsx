import { useEffect, useState } from "react";
import { Feed, RegionRisk, getJSON } from "./client";
import { Alert, listAlerts } from "./api";

type ModelResp = {
  available: boolean;
  metrics: { models: Record<string, { accuracy: number; f1: number; roc_auc: number }>; primary: string; data_kind: string } | null;
  latency: { count: number; mean_ms: number | null; p95_ms: number | null };
  active_model: string;
};

function Tile({
  label, value, sub, accent, big,
}: { label: string; value: string; sub?: string; accent: "ok" | "warn" | "crit" | "info"; big?: boolean }) {
  return (
    <div className={`kpi-tile kpi-${accent}`}>
      <div className="kpi-glow" />
      <span className="kpi-label">{label}</span>
      <span className={big ? "kpi-value kpi-value-lg" : "kpi-value"}>{value}</span>
      {sub && <span className="kpi-sub">{sub}</span>}
    </div>
  );
}

export default function KpiOverview({ token }: { token: string }) {
  const [regions, setRegions] = useState<RegionRisk[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [model, setModel] = useState<ModelResp | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    const load = () => {
      Promise.all([
        getJSON<RegionRisk[]>("/regions/risk", token),
        listAlerts(token),
        getJSON<Feed[]>("/feeds", token),
        getJSON<ModelResp>("/model/metrics", token),
      ])
        .then(([r, a, f, m]) => alive && (setRegions(r), setAlerts(a), setFeeds(f), setModel(m), setErr("")))
        .catch((e: Error) => alive && setErr(e.message));
    };
    load();
    const t = window.setInterval(load, 12000);
    return () => { alive = false; window.clearInterval(t); };
  }, [token]);

  const openAlerts = alerts.filter((a) => a.status === "open");
  const critical = openAlerts.filter((a) => a.severity === "critical").length;
  const highestRisk = regions.reduce<RegionRisk | null>(
    (best, r) => (r.risk !== null && (best === null || (best.risk ?? 0) < r.risk) ? r : best), null
  );
  const feedsUp = feeds.filter((f) => f.state === "up").length;
  const degradedRegions = regions.filter((r) => r.degraded).length;
  const primary = model?.metrics ? model.metrics.models[model.metrics.primary] : null;
  const latencyOk = model && model.latency.p95_ms !== null ? model.latency.p95_ms < 60000 : null;

  return (
    <section className="kpi-overview">
      <div className="row">
        <h2>Command centre overview</h2>
        <span className="muted">Auto-refreshes every 12s</span>
      </div>
      {err && <p role="alert" className="error">{err}</p>}
      <div className="kpi-grid">
        <Tile
          label="Open alerts" big
          value={String(openAlerts.length)}
          sub={critical > 0 ? `${critical} critical - needs action` : "none critical"}
          accent={critical > 0 ? "crit" : openAlerts.length > 0 ? "warn" : "ok"}
        />
        <Tile
          label="Highest regional risk" big
          value={highestRisk?.risk != null ? `${Math.round(highestRisk.risk * 100)}%` : "-"}
          sub={highestRisk ? highestRisk.name : "no data yet"}
          accent={highestRisk?.level === "critical" ? "crit" : highestRisk?.level === "warning" ? "warn" : "ok"}
        />
        <Tile
          label="Data feeds up"
          value={feeds.length ? `${feedsUp}/${feeds.length}` : "-"}
          sub={degradedRegions > 0 ? `${degradedRegions} region(s) in reduced confidence` : "all nominal"}
          accent={feedsUp === feeds.length && feeds.length > 0 ? "ok" : "warn"}
        />
        <Tile
          label="Active model"
          value={model?.active_model ?? "-"}
          sub={model?.metrics ? `${model.metrics.data_kind} data` : "no evaluation on file"}
          accent="info"
        />
        <Tile
          label="Model accuracy"
          value={primary ? `${(primary.accuracy * 100).toFixed(1)}%` : "-"}
          sub={primary ? `F1 ${primary.f1.toFixed(2)} - AUC ${primary.roc_auc.toFixed(2)}` : "run scripts/train_all.py"}
          accent={primary && primary.accuracy >= 0.8 ? "ok" : "warn"}
        />
        <Tile
          label="Alert latency p95"
          value={model && model.latency.p95_ms !== null ? `${Math.round(model.latency.p95_ms)} ms` : "-"}
          sub={latencyOk === null ? "no alerts recorded yet" : latencyOk ? "within 60s target" : "over 60s target"}
          accent={latencyOk === false ? "crit" : "ok"}
        />
      </div>
      <p className="muted kpi-footnote">
        Figures reflect this instance's live data and any evaluation on file in models/metrics.json.
        Accuracy and latency only satisfy the project's targets once measured on real data - see docs/PERFORMANCE.md.
      </p>
    </section>
  );
}
