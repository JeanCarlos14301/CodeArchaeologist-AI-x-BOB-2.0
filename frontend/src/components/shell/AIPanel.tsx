import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { lineRange } from "../../lib/format";
import { useWorkspace } from "../../lib/workspace";
import type { AskContext } from "../../types";
import { AskAnswerView, AskComposer } from "../domain/AskBob";
import { IconButton } from "../ui/Button";
import { Eyebrow } from "../ui/Layout";

const KIND_LABEL: Record<AskContext["kind"], string> = {
  project: "Proyecto",
  finding: "Hallazgo",
  file: "Archivo",
  function: "Función",
  module: "Módulo",
};

function suggestions(context: AskContext): string[] {
  const label = context.label ?? "esto";
  switch (context.kind) {
    case "finding":
      return [
        `¿Por qué ${context.finding_id} es un riesgo y qué evidencia lo respalda?`,
        `¿Qué podría romperse si corrijo ${context.finding_id}?`,
        "¿Qué pruebas debería ejecutar después de ese cambio?",
      ];
    case "file":
      return [`¿Qué hace ${label} y quién depende de él?`, `¿Qué riesgos hay en ${label}?`];
    case "function":
    case "module":
      return [`¿Quién depende de ${label}?`, `¿Qué impacto tendría modificar ${label}?`];
    default:
      return ["¿Qué debería migrar primero y por qué?", "Explica la arquitectura de este sistema.", "¿Qué pruebas faltan para migrar con seguridad?"];
  }
}

export function AIPanel({ onClose }: { onClose: () => void }) {
  const { aiContext, askHistory, route, flow, bob, seedComposer } = useWorkspace();
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    end.current?.scrollIntoView({ block: "end" });
  }, [askHistory]);

  const disabledReason = !route.jobId
    ? "Abre un análisis para preguntar sobre su código."
    : flow?.status !== "done"
      ? "Disponible cuando el análisis termine."
      : bob && !(bob.installed && bob.api_key_configured)
        ? "Bob no está disponible en el servidor."
        : null;

  return (
    <aside aria-label="Asistente IBM Bob" className="flex h-full flex-col bg-surface">
      <header className="flex h-12 shrink-0 items-center gap-2 border-b border-line px-4">
        <span aria-hidden className="h-2 w-2 rounded-pill bg-fg-2" />
        <h2 className="font-display text-body text-fg">Bob</h2>
        <span className="text-caption text-subtle">· contexto del workspace</span>
        <IconButton label="Cerrar panel de Bob" className="ml-auto" onClick={onClose}>
          <X size={16} aria-hidden />
        </IconButton>
      </header>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-4">
        <section aria-label="Contexto actual" className="rounded-inner border border-line px-3 py-2.5">
          <Eyebrow>Contexto · {KIND_LABEL[aiContext.kind]}</Eyebrow>
          <p className="mt-1 text-body text-pretty text-fg">{aiContext.label ?? (route.jobId ? "Este repositorio" : "Ningún proyecto abierto")}</p>
          {aiContext.path && (
            <p className="mt-0.5 truncate font-mono text-caption text-subtle">
              {aiContext.path}{aiContext.line_start ? `:${lineRange(aiContext.line_start, aiContext.line_end ?? aiContext.line_start)}` : ""}
            </p>
          )}
          <p className="mt-2 text-caption text-subtle">Bob lee el código de este análisis en modo solo lectura y cita archivo y líneas; cada cita se comprueba.</p>
        </section>

        {!disabledReason && (
          <section aria-label="Preguntas sugeridas">
            <Eyebrow>Preguntar sobre esto</Eyebrow>
            <ul className="mt-2 space-y-1">
              {suggestions(aiContext).map((text) => (
                <li key={text}>
                  <button type="button" onClick={() => seedComposer(text)} className="w-full rounded-inner px-2.5 py-1.5 text-left text-caption text-fg-2 transition-[background-color,color] duration-150 hover:bg-raised hover:text-fg">
                    {text}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {askHistory.length > 0 && (
          <section aria-label="Conversación" className="space-y-5">
            {askHistory.map((entry) => (
              <article key={entry.id} className="space-y-2 border-t border-line pt-4">
                <p className="text-micro tracking-eyebrow text-subtle uppercase">
                  Pregunta · {KIND_LABEL[entry.context.kind]}{entry.context.finding_id ? ` ${entry.context.finding_id}` : ""}
                </p>
                <p className="text-body text-fg">{entry.question}</p>
                <AskAnswerView entry={entry} />
              </article>
            ))}
            <div ref={end} />
          </section>
        )}
      </div>

      <div className="shrink-0 border-t border-line p-3">
        <AskComposer context={aiContext} disabledReason={disabledReason} />
      </div>
    </aside>
  );
}
