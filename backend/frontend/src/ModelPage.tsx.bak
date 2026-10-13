import { useCallback, useEffect, useState } from "react";
import { Feed, getJSON, postJSON } from "./client";

type M = {
  threshold: number; accuracy: number; balanced_accuracy: number; precision: number;
  recall: number; f1: number; roc_auc: number; confusion_matrix: number[][];
};
type Doc = { data_kind: string; primary: string; models: Record<string, M> };
type Resp = {
  available: boolean;
  metrics: Doc | null;
  latency: { count: number; mean_ms: number | null; p95_ms: number | null; max_ms: number | null };
  active_model: string;
};

const p = (v: number) => `${(v * 100).toFixed(1)}%`;

export default function ModelPage({ token, role }: { token: string; role: string }) {
  const [resp, setResp] = useState<Resp | null>(null);
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    getJSON<Resp>("/model/metrics", token).then(setResp).catch((e: Error) => setErr(e.message));
    getJSON<Feed[]>("/feeds", token).then(setFeeds).catch((e: Error) => setErr(e.message));
  }, [token]);
  useEffect(load, [load]);

  const toggle = async (f: Feed) => {
    try {
      await postJSON(`/feeds/${f.name}/${f.state === "up" ? "down" : "up"}`, token);
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const doc = resp?.metrics;
  const primary = doc ? doc.models[doc.primary] : null;

  return (
    <section>
      <h2>Model performance and data feeds</h2>
      {err && <p role="alert" className="error">{err}</p>}
      {!resp && <div className="skeleton" aria-busy="true" />}
      {resp && (
        <>
          <p>Active predictor in the alert path: <strong>{resp.active_model}</strong></p>
          <div className="card">
            <h3>Alert latency (measured, server side)</h3>
            {resp.latency.count === 0 ? (
              <p className="muted">No alerts recorded yet.</p>
            ) : (
              <p>
                n={resp.latency.count} - mean {resp.latency.mean_ms} ms - p95 {resp.latency.p95_ms} ms - max{" "}
                {resp.latency.max_ms} ms (target: under 60000 ms)
              </p>
            )}
          </div>
          <div className="card">
            <h3>Model evaluation</h3>
            {!doc && <p className="muted">No metrics yet. Run: python scripts/train_all.py</p>}
            {doc && (
              <>
                {doc.data_kind !== "real" && (
                  <p className="badge" role="note">
                    {"\u26A0"} Metrics computed on {doc.data_kind.toUpperCase()} data. They validate the pipeline, not the
                    accuracy objective.
                  </p>
                )}
                <div className="scroll">
                  <table>
                    <thead>
                      <tr><th>Model</th><th>Accuracy</th><th>Balanced acc.</th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th></tr>
                    </thead>
                    <tbody>
                      {Object.entries(doc.models).map(([name, m]) => (
                        <tr key={name}>
                          <td>{name}{name === doc.primary ? " (primary)" : ""}</td>
                          <td>{p(m.accuracy)}</td><td>{p(m.balanced_accuracy)}</td><td>{p(m.precision)}</td>
                          <td>{p(m.recall)}</td><td>{p(m.f1)}</td><td>{m.roc_auc.toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {primary && (
                  <div className="matrix" role="table" aria-label="Confusion matrix, primary model">
                    <div /><div className="muted">Pred: no flood</div><div className="muted">Pred: flood</div>
                    <div className="muted">Actual: no flood</div><div>TN {primary.confusion_matrix[0][0]}</div><div>FP {primary.confusion_matrix[0][1]}</div>
                    <div className="muted">Actual: flood</div><div>FN {primary.confusion_matrix[1][0]}</div><div>TP {primary.confusion_matrix[1][1]}</div>
                  </div>
                )}
              </>
            )}
          </div>
          <div className="card">
            <h3>Data-source health</h3>
            <ul className="feeds">
              {feeds.map((f) => (
                <li key={f.name}>
                  <span className={f.state === "up" ? "pill ok" : "pill down"}>
                    {f.state === "up" ? "\u25CF UP" : "\u25CB DOWN"}
                  </span>{" "}
                  <strong>{f.label}</strong> <span className="muted">breaker: {f.breaker}{f.simulated ? " - simulated outage" : ""}</span>
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
