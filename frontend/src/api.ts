const BASE: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type Alert = {
  id: number;
  region_id: string;
  severity: "watch" | "warning" | "critical";
  disaster_type: string;
  risk_score: number;
  confidence: number;
  degraded: boolean;
  novel: boolean;
  model_version: string;
  explanation: { feature: string; contribution: number }[];
  status: "open" | "acknowledged" | "resolved";
  handled_by: string | null;
  latency_ms: number;
  created_at: string;
};

async function call<T>(path: string, token: string | null, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) throw new Error(res.status === 401 ? "Invalid credentials or session expired" : `Request failed (${res.status})`);
  return res.json() as Promise<T>;
}

export const login = (username: string, password: string) =>
  call<{ access_token: string; role: string }>("/auth/login", null, {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

export const listAlerts = (token: string) => call<Alert[]>("/alerts", token);

export const setStatus = (token: string, id: number, action: "ack" | "resolve") =>
  call<Alert>(`/alerts/${id}/${action}`, token, { method: "POST" });

export function openAlertSocket(token: string, onAlert: (a: Alert) => void, onClose: () => void): WebSocket {
  const ws = new WebSocket(BASE.replace(/^http/, "ws") + "/ws/alerts");
  ws.onopen = () => ws.send(JSON.stringify({ token }));
  ws.onmessage = (e) => onAlert(JSON.parse(e.data) as Alert);
  ws.onclose = onClose;
  return ws;
}

export type Region = {
  id: string;
  name: string;
  province: string;
   geojson: { type: "Polygon"; coordinates: number[][][] };
  centroid_lat: number;
  centroid_lon: number;
  risk_score: number;
  band: "low" | "elevated" | "high";
  degraded: boolean;
  novel: boolean;
  last_updated: string | null;
};

export const listRegions = (token: string) => call<Region[]>("/regions", token);

export type Reading = {
  observed_at: string;
  rainfall_mm_24h: number | null;
  river_level_m: number | null;
  soil_moisture: number | null;
  temperature_c: number | null;
  humidity_pct: number | null;
};

export type ModelMetrics = {
  available: boolean;
  dataset_version: string | null;
  smart_target: number | null;
  smart_target_met: boolean | null;
  models: Record<string, {
    accuracy: number; precision: number; recall: number; f1: number; roc_auc: number;
    confusion_matrix: number[][];
  }> | null;
  real_data_only: {
    accuracy: number; precision: number; recall: number; f1: number; roc_auc: number;
    confusion_matrix: number[][];
  } | null;
  novelty_detector: { threshold: number; qualitative_check_passed: boolean } | null;
  note: string | null;
  active_model_version: string;
};

export const listReadings = (token: string, regionId: string) =>
  call<Reading[]>(`/regions/${regionId}/readings`, token);

export const getModelMetrics = (token: string) => call<ModelMetrics>("/models/metrics", token);

export const getHealth = (token: string) => call<Record<string, unknown>>("/health", token);