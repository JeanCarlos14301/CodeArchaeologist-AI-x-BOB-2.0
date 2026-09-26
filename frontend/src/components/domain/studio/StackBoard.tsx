import { Eyebrow } from "../../ui/Layout";
import { cleanVersion } from "../../../lib/format";
import { TechIcon } from "./TechIcon";
import type { DetectedTech, StackReport } from "../../../types";

const KINDS: { kind: string; label: string }[] = [
  { kind: "language", label: "Lenguajes" },
  { kind: "backend", label: "Backend" },
  { kind: "frontend", label: "Frontend" },
  { kind: "database", label: "Datos" },
  { kind: "orm", label: "Acceso a datos" },
  { kind: "infra", label: "Infraestructura" },
  { kind: "testing", label: "Pruebas" },
  { kind: "build", label: "Construcción" },
];

const ARCHITECTURE: Record<StackReport["architecture"]["kind"], { label: string; note: string }> = {
  monolith: { label: "Monolito", note: "Una sola aplicación desplegable." },
  "multi-app": { label: "Varias aplicaciones", note: "Backend y frontend como aplicaciones separadas." },
  microservices: { label: "Microservicios", note: "Varios servicios con código propio." },
  unknown: { label: "Sin determinar", note: "No se encontró un framework de aplicación." },
};

function evidenceTitle(tech: DetectedTech): string {
  const lines = tech.evidence.filter((item) => item.path).map((item) => (item.line ? `${item.path}:${item.line}` : item.path));
  return lines.length ? `Detectado en ${lines.join(", ")}` : "Detectado por extensión de archivo";
}

/** Lo que el proyecto usa hoy, medido sobre el código: cada tecnología con su evidencia en el tooltip. */
export function StackBoard({ stack }: { stack: StackReport }) {
  const architecture = ARCHITECTURE[stack.architecture.kind];
  const languageShare = new Map(stack.languages.map((language) => [language.id, language.share]));
  const multiService = stack.services.length > 1;

  return (
    <div>
      <div className="grid gap-x-10 gap-y-3 @3xl:grid-cols-[minmax(0,15rem)_minmax(0,1fr)]">
        <div>
          <Eyebrow>Arquitectura detectada</Eyebrow>
          <p className="mt-1 font-display text-title text-fg">{architecture.label}</p>
          <p className="text-caption text-subtle">{architecture.note}</p>
        </div>
        <ul className="space-y-1 text-caption text-muted">
          {stack.architecture.basis.map((line) => (
            <li key={line} className="grid grid-cols-[1rem_1fr]"><span aria-hidden className="text-subtle">·</span><span>{line}</span></li>
          ))}
          <li className="grid grid-cols-[1rem_1fr] text-subtle"><span aria-hidden>·</span><span className="font-mono">{stack.totals.files} archivos · {stack.totals.lines} líneas de código · {stack.totals.technologies} tecnologías</span></li>
        </ul>
      </div>

      <div className="mt-5 border-b border-line-subtle">
        {KINDS.map(({ kind, label }) => {
          const items = stack.technologies.filter((tech) => tech.kind === kind);
          if (!items.length) return null;
          return (
            <div key={kind} className="grid gap-x-6 gap-y-2 border-t border-line-subtle py-3 @2xl:grid-cols-[8.5rem_minmax(0,1fr)]">
              <Eyebrow className="pt-1.5">{label}</Eyebrow>
              <ul className="flex flex-wrap gap-2">
                {items.map((tech) => (
                  <li key={`${tech.id}-${tech.service}`} title={evidenceTitle(tech)} className="inline-flex h-8 items-center gap-2 rounded-pill border border-line pr-3 pl-2.5 text-caption text-fg">
                    <TechIcon slug={tech.icon} name={tech.name} size={16} />
                    <span>{tech.name}</span>
                    {kind === "language" && languageShare.has(tech.id) && <span className="font-mono text-subtle tabular-nums">{Math.round((languageShare.get(tech.id) ?? 0) * 100)}%</span>}
                    {tech.version && <span className="font-mono text-subtle">{cleanVersion(tech.version)}</span>}
                    {multiService && tech.service && tech.service !== "." && <span className="font-mono text-subtle">· {tech.service}</span>}
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
