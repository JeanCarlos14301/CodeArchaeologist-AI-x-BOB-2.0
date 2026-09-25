import { useEffect, useId, useState } from "react";

/** Renderiza Mermaid cargándolo bajo demanda (el paquete es pesado). Se re-renderiza al cambiar de tema. */
export function Mermaid({ chart, theme }: { chart: string; theme: "dark" | "light" }) {
  const id = useId().replace(/:/g, "");
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setSvg(null);
    setError(null);
    import("mermaid")
      .then(async ({ default: mermaid }) => {
        mermaid.initialize({ startOnLoad: false, theme: theme === "dark" ? "dark" : "neutral", securityLevel: "strict", flowchart: { htmlLabels: false } });
        const out = await mermaid.render(`m-${id}-${theme}`, chart);
        if (!cancelled) setSvg(out.svg);
      })
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [chart, theme, id]);

  if (error) return <pre className="overflow-auto rounded-lg bg-code p-3 text-xs text-bad">No se pudo dibujar el diagrama: {error}</pre>;
  if (!svg) return <p role="status" className="py-10 text-center text-sm text-muted">Dibujando diagrama…</p>;
  return <div className="mermaid-host overflow-auto" dangerouslySetInnerHTML={{ __html: svg }} />;
}
