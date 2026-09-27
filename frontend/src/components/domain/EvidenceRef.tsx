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
 * Verifiable `file:line` reference (DESIGN.md §4). ✓ = the Python validator confirmed that the
 * file, the lines and the snippet exist; ✗ = they do not match; no mark = not checked.
 */
export function EvidenceRef({ path, lineStart, lineEnd, verified, reason, active = false, onOpen }: Props) {
  const mark = verified === null ? null : verified ? "✓" : "✗";
  const tone = verified === null ? "text-fg-2" : verified ? "text-verified" : "text-danger";
  const status = verified === null ? "no comprobada" : verified ? "verificada" : "no verificada";
  const content = (
    <>
      {mark && <span aria-hidden className={tone}>{mark}</span>}
      <span className="min-w-0 truncate text-fg" title={path}>{path}</span>
      <span className="text-subtle">:{lineRange(lineStart, lineEnd)}</span>
      <span className="sr-only">, evidence {status}{reason ? `: ${reason}` : ""}</span>
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
