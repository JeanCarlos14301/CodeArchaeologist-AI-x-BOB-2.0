interface Props {
  path?: string;
  lines: { number: number; text: string }[];
  highlight?: [number, number];
  caption?: string;
  maxHeight?: string;
}

/** Bloque de código con numeración y rango resaltado. */
export function CodeBlock({ path, lines, highlight, caption, maxHeight = "55vh" }: Props) {
  return (
    <div className="overflow-hidden rounded-lg border border-line bg-code">
      {(path || caption) && (
        <div className="flex items-center justify-between gap-2 border-b border-line bg-surface-2 px-3 py-1.5 font-mono text-xs text-muted">
          <span className="truncate text-fg">{path}</span>
          {caption && <span className="shrink-0">{caption}</span>}
        </div>
      )}
      <div className="overflow-auto py-2 font-mono text-[12.5px] leading-6" style={{ maxHeight }}>
        {lines.map((line) => {
          const hit = highlight && line.number >= highlight[0] && line.number <= highlight[1];
          return (
            <div key={line.number} className={`flex px-3 ${hit ? "border-l-2 border-warn bg-[var(--code-hl)]" : "border-l-2 border-transparent"}`}>
              <span className="mr-4 w-8 shrink-0 select-none text-right text-muted/70">{line.number}</span>
              <code className="whitespace-pre">{line.text || " "}</code>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function toLines(code: string, start = 1): { number: number; text: string }[] {
  return code.split("\n").map((text, index) => ({ number: start + index, text }));
}
