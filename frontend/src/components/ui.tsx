import type { ReactNode } from "react";
import type { ExecutionMode, Severity } from "../types";

export const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

export const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Crítico",
  high: "Alto",
  medium: "Medio",
  low: "Bajo",
  info: "Info",
};

const SEVERITY_BADGE: Record<Severity, string> = {
  critical: "bg-[color-mix(in_srgb,var(--sev-critical)_16%,transparent)] text-[var(--sev-critical)] ring-[var(--sev-critical)]/30",
  high: "bg-[color-mix(in_srgb,var(--sev-high)_16%,transparent)] text-[var(--sev-high)] ring-[var(--sev-high)]/30",
  medium: "bg-[color-mix(in_srgb,var(--sev-medium)_16%,transparent)] text-[var(--sev-medium)] ring-[var(--sev-medium)]/30",
  low: "bg-[color-mix(in_srgb,var(--sev-low)_16%,transparent)] text-[var(--sev-low)] ring-[var(--sev-low)]/30",
  info: "bg-[color-mix(in_srgb,var(--sev-low)_10%,transparent)] text-muted ring-line",
};

export const SEVERITY_BAR: Record<Severity, string> = {
  critical: "bg-[var(--sev-critical)]",
  high: "bg-[var(--sev-high)]",
  medium: "bg-[var(--sev-medium)]",
  low: "bg-[var(--sev-low)]",
  info: "bg-muted/50",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset ${SEVERITY_BADGE[severity]}`}>
      {SEVERITY_LABEL[severity]}
    </span>
  );
}

const MODE_INFO: Record<ExecutionMode, { label: string; hint: string; tone: string }> = {
  live: { label: "LIVE", hint: "Bob analizó el repositorio en vivo", tone: "text-ok ring-ok/40 bg-ok/10" },
  imported: { label: "IMPORTADO", hint: "Respuesta real de Bob reutilizada", tone: "text-accent ring-accent/40 bg-accent/10" },
  example: { label: "EJEMPLO", hint: "Datos de ejemplo, no provienen de un análisis real", tone: "text-warn ring-warn/40 bg-warn/10" },
};

export function ModeBadge({ mode }: { mode: ExecutionMode }) {
  const info = MODE_INFO[mode];
  return (
    <span title={info.hint} className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 font-mono text-[11px] font-semibold ring-1 ring-inset ${info.tone}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {info.label}
    </span>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-xl border border-line bg-surface ${className}`}>{children}</section>;
}

export function PageHeader({ title, subtitle, right }: { title: string; subtitle?: string; right?: ReactNode }) {
  return (
    <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-muted">{subtitle}</p>}
      </div>
      {right}
    </header>
  );
}

export function EmptyState({ icon = "◌", title, children, action }: { icon?: string; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed border-line px-6 py-14 text-center">
      <span className="mb-3 text-3xl text-muted" aria-hidden>{icon}</span>
      <h2 className="text-base font-semibold">{title}</h2>
      {children && <p className="mt-1 max-w-md text-sm text-muted">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-bad/40 bg-bad/10 px-4 py-3 text-sm text-bad">
      <span>{message}</span>
      {onRetry && (
        <button type="button" onClick={onRetry} className="rounded-md border border-bad/40 px-2.5 py-1 text-xs font-medium hover:bg-bad/10">
          Reintentar
        </button>
      )}
    </div>
  );
}

export function Loading({ label = "Cargando…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-10 text-sm text-muted">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-line border-t-accent" aria-hidden />
      {label}
    </div>
  );
}

export function Button({
  children, onClick, type = "button", variant = "primary", disabled, className = "",
}: {
  children: ReactNode; onClick?: () => void; type?: "button" | "submit"; variant?: "primary" | "ghost"; disabled?: boolean; className?: string;
}) {
  const base = "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50";
  const tone = variant === "primary" ? "bg-accent text-accent-fg hover:brightness-110" : "border border-line bg-surface-2 hover:border-accent/50";
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={`${base} ${tone} ${className}`}>
      {children}
    </button>
  );
}
