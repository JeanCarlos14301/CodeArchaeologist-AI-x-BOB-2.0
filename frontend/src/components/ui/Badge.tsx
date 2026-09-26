import type { ReactNode } from "react";
import { SEVERITY } from "../../lib/severity";
import type { ExecutionMode, Severity } from "../../types";

export function Chip({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex h-5.5 items-center gap-1.5 rounded-pill border border-line px-2.5 text-caption text-fg-2 ${className}`}>
      {children}
    </span>
  );
}

/** Severidad = glifo + etiqueta + color (nunca solo color). */
export function SeverityBadge({ severity, compact = false }: { severity: Severity; compact?: boolean }) {
  const info = SEVERITY[severity];
  return (
    <span className={`inline-flex items-center gap-1.5 text-micro font-semibold tracking-eyebrow uppercase ${info.text}`}>
      <span aria-hidden className="text-caption leading-none">{info.glyph}</span>
      {compact ? <span className="sr-only">{info.label}</span> : info.label}
    </span>
  );
}

const MODE: Record<ExecutionMode, { label: string; hint: string; tone: string }> = {
  live: { label: "LIVE", hint: "Bob analizó este repositorio en vivo", tone: "text-verified border-verified/40" },
  imported: { label: "IMPORTADO", hint: "Respuesta real de Bob grabada y reutilizada", tone: "text-fg-2 border-line-strong" },
  example: { label: "EJEMPLO", hint: "Datos de ejemplo: no provienen de un análisis real", tone: "text-warning border-warning/40" },
};

export function ModeBadge({ mode }: { mode: ExecutionMode }) {
  const info = MODE[mode];
  return (
    <span title={info.hint} className={`inline-flex h-5 items-center gap-1.5 rounded-pill border px-2 font-mono text-micro font-medium tracking-wide ${info.tone}`}>
      <span aria-hidden className="h-1.5 w-1.5 rounded-pill bg-current" />
      {info.label}
      <span className="sr-only">: {info.hint}</span>
    </span>
  );
}

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="inline-flex h-4.5 min-w-4.5 items-center justify-center rounded-tick border border-line-strong px-1 font-mono text-micro text-subtle">
      {children}
    </kbd>
  );
}

type Tone = "ok" | "bad" | "warn" | "idle" | "busy";
const DOT: Record<Tone, string> = {
  ok: "bg-verified",
  bad: "bg-danger",
  warn: "bg-warning",
  idle: "bg-subtle",
  busy: "bg-activity animate-pulse",
};

export function StatusDot({ tone, label }: { tone: Tone; label?: string }) {
  return (
    <span className="inline-flex min-w-0 items-center gap-1.5">
      <span aria-hidden className={`h-1.5 w-1.5 shrink-0 rounded-pill ${DOT[tone]}`} />
      {label && <span className="truncate" title={label}>{label}</span>}
    </span>
  );
}
