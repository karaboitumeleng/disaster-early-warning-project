import { useCallback, useEffect, useState } from "react";
import { Feed, getJSON, postJSON } from "./client";

type M = {
  threshold: number;
  accuracy: number;
  balanced_accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  confusion_matrix: number[][];
};

type Doc = { data_kind: string; primary: string; models: Record<string, M> };

export type ComputingMetrics = {
  inference_latency_ms?: {
    p50?: number;
    p95?: number;
    p99?: number;
  };
  throughput_rps?: number;
  gpu_utilization_pct?: number;
  cpu_utilization_pct?: number;
  vram_used_mb?: number;
  vram_total_mb?: number;
  ram_used_mb?: number;
  model_parameters_m?: number;
  flops_giga?: number;
  batch_size?: number;
  hardware_accelerator?: string;
};

type Resp = {
  available: boolean;
  metrics: Doc | null;
  latency: {
    count: number;
    mean_ms: number | null;
    p95_ms: number | null;
    max_ms: number | null;
  };
  active_model: string;
  computing?: ComputingMetrics | null;
};

const p = (v: number) => `${(v * 100).toFixed(1)}%`;

function MeterBar({
  label,
  value,
  max = 100,
  unit = "%",
}: {
  label: string;
  value: number;
  max?: number;
  unit?: string;
}) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div style={{ margin: "0.5rem 0" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "0.8rem",
          marginBottom: "0.2rem",
        }}
      >
        <span>{label}</span>
        <strong>
          {value}
          {unit}
        </strong>
      </div>
      <div
        style={{
          height: "6px",
          backgroundColor: "#334155",
          borderRadius: "3px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${percentage}%`,
            backgroundColor: percentage > 85 ? "#f43f5e" : "#3b82f6",
            transition: "width 0.3s ease",
          }}
        />
      </div>
    </div>
  );
}

export default function ModelPage({
  token,
  role,
}: {
  token: string;
  role: string;
}) {
  const [resp, setResp] = useState<Resp | null>(null);
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    getJSON<Resp>("/model/metrics", token)
      .then(setResp)
      .catch((e: Error) => setErr(e.message));
    getJSON<Feed[]>("/feeds", token)
      .then(setFeeds)
      .catch((e: Error) => setErr(e.message));
  }, [token]);

  useEffect(load, [load]);

  const toggle = async (f: Feed) => {
    try {
      await postJSON(
        `/feeds/${f.name}/${f.state === "up" ? "down" : "up"}`,
        token
      );
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const doc = resp?.metrics;
  const primary = doc ? doc.models[doc.primary] : null;
  const comp = resp?.computing;

  return (
    <section>
      <h2>Model performance and data feeds</h2>
      {err && (
        <p role="alert" className="error">
          {err}
        </p>
      )}
      {!resp && <div className="skeleton" aria-busy="true" />}
      {resp && (
        <>
          <p>
            Active predictor in the alert path:{" "}
            <strong>{resp.active_model}</strong>
          </p>

          {/* System & Computing Performance Card */}
          {comp && (
            <div className="card">
              <h3>System & Computing Performance</h3>
              <p className="muted" style={{ marginBottom: "1rem" }}>
                Accelerator:{" "}
                <strong>
                  {comp.hardware_accelerator ?? "CPU Execution"}
                </strong>{" "}
                {comp.batch_size && `| Batch Size: ${comp.batch_size}`}
              </p>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                  gap: "0.75rem",
                  marginBottom: "1rem",
                }}
              >
                <div
                  style={{
                    padding: "0.5rem",
                    background: "rgba(255,255,255,0.03)",
                    borderRadius: "4px",
                  }}
                >
                  <span className="muted" style={{ fontSize: "0.75rem" }}>
                    Inference p50
                  </span>
                  <div style={{ fontWeight: "bold", fontSize: "1.1rem" }}>
                    {comp.inference_latency_ms?.p50 ?? "N/A"} ms
                  </div>
                  {comp.inference_latency_ms?.p95 && (
                    <span className="muted" style={{ fontSize: "0.7rem" }}>
                      p95: {comp.inference_latency_ms.p95}ms
                    </span>
                  )}
                </div>

                <div
                  style={{
                    padding: "0.5rem",
                    background: "rgba(255,255,255,0.03)",
                    borderRadius: "4px",
                  }}
                >
                  <span className="muted" style={{ fontSize: "0.75rem" }}>
                    Throughput
                  </span>
                  <div style={{ fontWeight: "bold", fontSize: "1.1rem" }}>
                    {comp.throughput_rps ?? "N/A"} req/s
                  </div>
                </div>

                <div
                  style={{
                    padding: "0.5rem",
                    background: "rgba(255,255,255,0.03)",
                    borderRadius: "4px",
                  }}
                >
                  <span className="muted" style={{ fontSize: "0.75rem" }}>
                    Model Size
                  </span>
                  <div style={{ fontWeight: "bold", fontSize: "1.1rem" }}>
                    {comp.model_parameters_m
                      ? `${comp.model_parameters_m}M params`
                      : "N/A"}
                  </div>
                </div>

                <div
                  style={{
                    padding: "0.5rem",
                    background: "rgba(255,255,255,0.03)",
                    borderRadius: "4px",
                  }}
                >
                  <span className="muted" style={{ fontSize: "0.75rem" }}>
                    Compute Overhead
                  </span>
                  <div style={{ fontWeight: "bold", fontSize: "1.1rem" }}>
                    {comp.flops_giga ? `${comp.flops_giga} GFLOPs` : "N/A"}
                  </div>
                </div>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                  gap: "1rem",
                }}
              >
                {comp.gpu_utilization_pct !== undefined && (
                  <MeterBar
                    label="GPU Utilization"
                    value={comp.gpu_utilization_pct}
                  />
                )}
                {comp.cpu_utilization_pct !== undefined && (
                  <MeterBar
                    label="CPU Utilization"
                    value={comp.cpu_utilization_pct}
                  />
                )}
                {comp.vram_used_mb !== undefined && comp.vram_total_mb && (
                  <MeterBar
                    label={`VRAM Usage (${comp.vram_used_mb}MB / ${comp.vram_total_mb}MB)`}
                    value={comp.vram_used_mb}
                    max={comp.vram_total_mb}
                    unit="MB"
                  />
                )}
              </div>
            </div>
          )}

          {/* Server-Side Alert Latency */}
          <div className="card">
            <h3>Alert latency (measured, server side)</h3>
            {resp.latency.count === 0 ? (
              <p className="muted">No alerts recorded yet.</p>
            ) : (
              <p>
                n={resp.latency.count} - mean {resp.latency.mean_ms} ms - p95{" "}
                {resp.latency.p95_ms} ms - max {resp.latency.max_ms} ms (target:
                under 60000 ms)
              </p>
            )}
          </div>

          {/* Model Evaluation Card */}
          <div className="card">
            <h3>Model evaluation</h3>
            {!doc && (
              <p className="muted">
                No metrics yet. Run: python scripts/train_all.py
              </p>
            )}
            {doc && (
              <>
                {doc.data_kind !== "real" && (
                  <p className="badge" role="note">
                    {"\u26A0"} Metrics computed on {doc.data_kind.toUpperCase()}{" "}
                    data. They validate the pipeline, not the accuracy
                    objective.
                  </p>
                )}
                <div className="scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Model</th>
                        <th>Accuracy</th>
                        <th>Balanced acc.</th>
                        <th>Precision</th>
                        <th>Recall</th>
                        <th>F1</th>
                        <th>ROC-AUC</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(doc.models).map(([name, m]) => (
                        <tr key={name}>
                          <td>
                            {name}
                            {name === doc.primary ? " (primary)" : ""}
                          </td>
                          <td>{p(m.accuracy)}</td>
                          <td>{p(m.balanced_accuracy)}</td>
                          <td>{p(m.precision)}</td>
                          <td>{p(m.recall)}</td>
                          <td>{p(m.f1)}</td>
                          <td>{m.roc_auc.toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {primary && (
                  <div
                    className="matrix"
                    role="table"
                    aria-label="Confusion matrix, primary model"
                  >
                    <div />
                    <div className="muted">Pred: no flood</div>
                    <div className="muted">Pred: flood</div>
                    <div className="muted">Actual: no flood</div>
                    <div>TN {primary.confusion_matrix[0][0]}</div>
                    <div>FP {primary.confusion_matrix[0][1]}</div>
                    <div className="muted">Actual: flood</div>
                    <div>FN {primary.confusion_matrix[1][0]}</div>
                    <div>TP {primary.confusion_matrix[1][1]}</div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Data-Source Health Card */}
          <div className="card">
            <h3>Data-source health</h3>
            <ul className="feeds">
              {feeds.map((f) => (
                <li key={f.name}>
                  <span
                    className={f.state === "up" ? "pill ok" : "pill down"}
                  >
                    {f.state === "up" ? "\u25CF UP" : "\u25CB DOWN"}
                  </span>{" "}
                  <strong>{f.label}</strong>{" "}
                  <span className="muted">
                    breaker: {f.breaker}
                    {f.simulated ? " - simulated outage" : ""}
                  </span>
                  <div className="muted">{f.note}</div>
                  {role === "admin" && (
                    <button className="secondary" onClick={() => toggle(f)}>
                      {f.state === "up" ? "Simulate outage" : "Restore"}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </section>
  );
}