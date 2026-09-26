import { useEffect, useRef, type ReactNode } from "react";
import { SEVERITY } from "../../lib/severity";
import type { Severity } from "../../types";

export interface CodeMark {
  start: number;
  end: number;
  severity?: Severity;
  label?: string;
}

interface Props {
  path: string;
  lines: { number: number; text: string }[];
  marks?: CodeMark[];
  focusLine?: number | null;
  caption?: ReactNode;
  actions?: ReactNode;
  maxHeight?: string;
  onMarkClick?: (mark: CodeMark) => void;
}

/** Superficie de código: el código es el contenido principal (PRODUCT.md §23). */
export function CodeViewer({ path, lines, marks = [], focusLine = null, caption, actions, maxHeight = "70vh", onMarkClick }: Props) {
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!focusLine || !scroller.current) return;
    const row = scroller.current.querySelector<HTMLElement>(`[data-line="${focusLine}"]`);
    if (row) scroller.current.scrollTop = Math.max(0, row.offsetTop - scroller.current.clientHeight / 3);
  }, [focusLine, lines]);

  const markAt = (line: number) => marks.find((mark) => line >= mark.start && line <= mark.end);

  return (
    <figure className="overflow-hidden rounded-inner border border-line bg-code">
      <figcaption className="flex min-h-9 items-center justify-between gap-3 border-b border-line px-3">
        <span className="min-w-0 truncate font-mono text-caption text-fg">{path}</span>
        <span className="flex shrink-0 items-center gap-2 text-caption text-subtle">
          {caption}
          {actions}
        </span>
      </figcaption>
      <div ref={scroller} className="overflow-auto py-2" style={{ maxHeight }}>
        <pre className="min-w-max font-mono text-code">
          {lines.map((line) => {
            const mark = markAt(line.number);
            const isStart = mark?.start === line.number;
            const tone = mark?.severity ? SEVERITY[mark.severity] : null;
            return (
              <div
                key={line.number}
                data-line={line.number}
                className={`grid grid-cols-[1.25rem_3rem_1fr] pr-4 ${mark ? "bg-code-hl" : ""} ${line.number === focusLine ? "shadow-inset-accent" : ""}`}
              >
                <span className="flex items-center justify-center">
                  {isStart && tone ? (
                    <button
                      type="button"
                      onClick={() => mark && onMarkClick?.(mark)}
                      title={mark?.label}
                      aria-label={mark?.label ?? "Hallazgo"}
                      className={`text-caption leading-none ${tone.text}`}
                    >
                      {tone.glyph}
                    </button>
                  ) : mark ? (
                    <span aria-hidden className={`h-full w-px ${tone?.bg ?? "bg-warning"}`} />
                  ) : null}
                </span>
                <span className="pr-3 text-right text-subtle select-none">{line.number}</span>
                <code className="whitespace-pre text-fg-2">{line.text || " "}</code>
              </div>
            );
          })}
        </pre>
      </div>
    </figure>
  );
}

export function toLines(code: string, start = 1): { number: number; text: string }[] {
  return code.split("\n").map((text, index) => ({ number: start + index, text }));
}
