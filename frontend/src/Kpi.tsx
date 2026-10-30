import type { ReactNode } from "react";

export type Tone = "neutral" | "danger" | "warn" | "good";

const TONE = {
  neutral: { value: "text-slate-100", dot: "bg-slate-500", badge: "border-slate-700 bg-slate-800/70 text-slate-300" },
  danger: { value: "text-red-400", dot: "bg-red-500", badge: "border-red-800 bg-red-950/70 text-red-300" },
  warn: { value: "text-amber-400", dot: "bg-amber-500", badge: "border-amber-800 bg-amber-950/60 text-amber-300" },
  good: { value: "text-emerald-400", dot: "bg-emerald-500", badge: "border-emerald-800 bg-emerald-950/60 text-emerald-300" },
} as const;

/** Compact status pill: crisp border, dark tinted fill, small accent dot. No glow. */
export function StatusBadge({
  tone = "neutral",
  pulse = false,
  className = "",
  children,
}: {
  tone?: Tone;
  pulse?: boolean;
  className?: string;
  children: ReactNode;
}) {
  const t = TONE[tone];
  return (
    <span
      className={`inline-flex items-center gap-2 whitespace-nowrap rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${t.badge} ${className}`}
    >
      <span className={`size-1.5 rounded-full ${t.dot} ${pulse ? "animate-pulse" : ""}`} aria-hidden="true" />
      {children}
    </span>
  );
}

/** Stat tile. `value` can be text or a node (e.g. a StatusBadge); `hint` is the small line beneath. */
export function KpiCard({
  label,
  value,
  tone = "neutral",
  hint,
}: {
  label: string;
  value: ReactNode;
  tone?: Tone;
  hint?: ReactNode;
}) {
  const t = TONE[tone];
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-center gap-2">
        <span className={`size-1.5 rounded-full ${t.dot}`} aria-hidden="true" />
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</span>
      </div>
      <div className="flex min-h-10 items-center">
        {typeof value === "string" || typeof value === "number" ? (
          <span className={`text-3xl font-semibold leading-none tabular-nums ${t.value}`}>{value}</span>
        ) : (
          value
        )}
      </div>
      {hint && <p className="text-xs leading-snug text-slate-500">{hint}</p>}
    </div>
  );
}
