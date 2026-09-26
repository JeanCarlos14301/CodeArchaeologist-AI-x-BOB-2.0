import { lineRange } from "../../lib/format";

interface Props {
  path: string;
  lineStart: number;
  lineEnd: number;
  verified: boolean | null;
  reason?: string;
  active?: boolean;
  onOpen?: () => void;
}

/**
 * Referencia `archivo:línea` verificable (DESIGN.md §4). ✓ = el validador en Python confirmó que el
 * archivo, las líneas y el fragmento existen; ✗ = no coinciden; sin marca = no se comprobó.
 */
export function EvidenceRef({ path, lineStart, lineEnd, verified, reason, active = false, onOpen }: Props) {
  const mark = verified === null ? null : verified ? "✓" : "✗";
  const tone = verified === null ? "text-fg-2" : verified ? "text-verified" : "text-danger";
  const status = verified === null ? "no comprobada" : verified ? "verificada" : "no verificada";
  const content = (
    <>
      {mark && <span aria-hidden className={tone}>{mark}</span>}
      <span className="truncate text-fg">{path}</span>
      <span className="text-subtle">:{lineRange(lineStart, lineEnd)}</span>
      <span className="sr-only">, evidencia {status}{reason ? `: ${reason}` : ""}</span>
    </>
  );
  const base = "inline-flex max-w-full items-center gap-1.5 rounded-pill border px-2.5 py-0.5 font-mono text-caption";
  if (!onOpen) return <span className={`${base} border-line`}>{content}</span>;
  return (
    <button
      type="button"
      onClick={onOpen}
      title={reason}
      aria-pressed={active}
      className={`${base} transition-[border-color,background-color] duration-150 ease-out ${active ? "border-accent-hover bg-raised" : "border-line hover:border-line-strong hover:bg-raised"}`}
    >
      {content}
    </button>
  );
}
