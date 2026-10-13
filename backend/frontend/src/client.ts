const BASE: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type Level = "critical" | "warning" | "watch" | "low" | "unknown";

export type RegionRisk = {
  id: string;
  name: string;
  province: string;
  lat: number;
  lon: number;
  risk: number | null;
  level: Level;
  confidence: number | null;
  degraded: boolean;
  novel: boolean;
  updated_at: string | null;
};

export type Point = {
  t: string;
  rainfall: number | null;
  river_level: number | null;
  risk: number;
  novel: boolean;
};

export type Feed = {
  name: string;
  label: string;
  note: string;
  state: "up" | "down";
  breaker: string;
  simulated: boolean;
};

async function req<T>(path: string, token: string, method: "GET" | "POST"): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method, headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(res.status === 401 ? "Session expired" : `Request failed (${res.status})`);
  return (await res.json()) as T;
}

export const getJSON = <T>(path: string, token: string) => req<T>(path, token, "GET");
export const postJSON = <T>(path: string, token: string) => req<T>(path, token, "POST");
