import { useCallback, useEffect, useState } from "react";
import { Alert, listAlerts, login, openAlertSocket, setStatus } from "./api";
import { Feed, getJSON } from "./client";
import Analytics from "./Analytics";
import ModelPage from "./ModelPage";
import RiskMap from "./RiskMap";

const SEV = {
  critical: { icon: "\u26D4", label: "CRITICAL" },
  warning: { icon: "\u26A0", label: "WARNING" },
  watch: { icon: "\u25C9", label: "WATCH" },
} as const;

type Tab = "map" | "alerts" | "analytics" | "model";
const TABS: [Tab, string][] = [
  ["map", "Risk map"],
  ["alerts", "Alerts"],
  ["analytics", "Analytics"],
  ["model", "Model & feeds"],
];

function Login({ onLogin }: { onLogin: (t: string, role: string) => void }) {
  const [u, setU] = useState("analyst");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const r = await login(u, p);
      onLogin(r.access_token, r.role);
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="center">
      <form className="card login" onSubmit={submit}>
        <h1>SA Early Warning</h1>
        <p className="muted">National Disaster Management Centre</p>
        <label>Username<input value={u} onChange={(e) => setU(e.target.value)} autoComplete="username" /></label>
        <label>Password<input type="password" value={p} onChange={(e) => setP(e.target.value)} autoComplete="current-password" /></label>
        {err && <p role="alert" className="error">{err}</p>}
        <button disabled={busy || !p}>{busy ? "Signing in..." : "Sign in"}</button>
      </form>
    </main>
  );
}

function AlertCard({ a, canAct, onAct }: { a: Alert; canAct: boolean; onAct: (id: number, act: "ack" | "resolve") => void }) {
  const sev = SEV[a.severity];
  return (
    <article className={`card alert ${a.severity} ${a.status}`}>
      <header>
        <span className="sev">{sev.icon} {sev.label}</span>
        <span className="muted">{new Date(a.created_at).toLocaleString()}</span>
      </header>
      <h3>{a.region_id} - {a.novel ? "Unrecognised pattern (possible novel event)" : a.disaster_type}</h3>
      <p>Risk {(a.risk_score * 100).toFixed(0)}% - Confidence {(a.confidence * 100).toFixed(0)}% - Status: {a.status}</p>
      {a.degraded && <p className="badge">{"\u25D0"} Reduced confidence: satellite feed unavailable</p>}
      <details>
        <summary>Why this alert?</summary>
        <ul>{a.explanation.map((x) => <li key={x.feature}>{x.feature}: {x.contribution >= 0 ? "+" : ""}{x.contribution}</li>)}</ul>
        <p className="muted">Model {a.model_version} - pipeline latency {a.latency_ms} ms</p>
      </details>
      {canAct && a.status !== "resolved" && (
        <div className="actions">
          {a.status === "open" && <button onClick={() => onAct(a.id, "ack")}>Acknowledge</button>}
          <button className="secondary" onClick={() => onAct(a.id, "resolve")}>Resolve</button>
        </div>
      )}
    </article>
  );
}

export default function App() {
  // Token lives in memory only (not localStorage) to limit XSS exposure; a refresh signs out.
  const [session, setSession] = useState<{ token: string; role: string } | null>(null);
  const [tab, setTab] = useState<Tab>("map");
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [live, setLive] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const upsert = useCallback((a: Alert) => {
    setAlerts((prev) => [a, ...prev.filter((x) => x.id !== a.id)].sort((x, y) => y.id - x.id));
  }, []);

  useEffect(() => {
    if (!session) return;
    let closed = false;
    let ws: WebSocket | null = null;
    let timer: number | undefined;
    setLoading(true);
    listAlerts(session.token)
      .then(setAlerts)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
    const connect = () => {
      ws = openAlertSocket(session.token, upsert, () => {
        setLive(false);
        if (!closed) timer = window.setTimeout(connect, 3000);
      });
      ws.onopen = () => {
        setLive(true);
        ws?.send(JSON.stringify({ token: session.token }));
      };
    };
    connect();
    return () => {
      closed = true;
      window.clearTimeout(timer);
      ws?.close();
    };
  }, [session, upsert]);

  useEffect(() => {
    if (!session) return;
    let alive = true;
    const load = () =>
      getJSON<Feed[]>("/feeds", session.token).then((f) => alive && setFeeds(f)).catch(() => undefined);
    load();
    const t = window.setInterval(load, 10000);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, [session]);

  if (!session) return <Login onLogin={(token, role) => setSession({ token, role })} />;

  const canAct = session.role !== "viewer";
  const openCritical = alerts.filter((a) => a.severity === "critical" && a.status === "open");
  const satDown = feeds.some((f) => f.name === "satellite" && f.state === "down");
  const act = async (id: number, action: "ack" | "resolve") => {
    try {
      upsert(await setStatus(session.token, id, action));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="shell">
      <header className="topbar">
        <strong>SA Early Warning</strong>
        <span className={live ? "pill ok" : "pill down"}>{live ? "\u25CF Live" : "\u25CB Reconnecting..."}</span>
        <span className="muted">Role: {session.role}</span>
        <button className="secondary" onClick={() => setSession(null)}>Sign out</button>
      </header>
      <nav className="tabs" aria-label="Sections">
        {TABS.map(([id, label]) => (
          <button key={id} className={tab === id ? "tab active" : "tab"} aria-current={tab === id} onClick={() => setTab(id)}>
            {label}{id === "alerts" && openCritical.length > 0 ? ` (${openCritical.length})` : ""}
          </button>
        ))}
      </nav>
      {openCritical.length > 0 && (
        <div className="banner" role="alert">{"\u26D4"} {openCritical.length} critical alert(s) require action</div>
      )}
      {satDown && (
        <div className="banner warn" role="status">
          {"\u25D0"} Reduced-confidence mode: satellite feed is down, predictions use ground data only.
        </div>
      )}
      {error && <p role="alert" className="error">{error}</p>}
      {tab === "map" && <RiskMap token={session.token} />}
      {tab === "analytics" && <Analytics token={session.token} />}
      {tab === "model" && <ModelPage token={session.token} role={session.role} />}
      {tab === "alerts" && (
        <main className="feed">
          <h2>Live alerts</h2>
          {loading && <div className="skeleton" aria-busy="true" />}
          {!loading && alerts.length === 0 && (
            <p className="muted">No alerts. New sensor readings that exceed the risk threshold will appear here instantly.</p>
          )}
          {alerts.map((a) => <AlertCard key={a.id} a={a} canAct={canAct} onAct={act} />)}
        </main>
      )}
    </div>
  );
}
