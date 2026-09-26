import { Activity, ArrowRightLeft, Boxes, FileDown, FolderTree, History, LayoutDashboard, Network, ShieldAlert, type LucideIcon } from "lucide-react";
import type { Section } from "../../lib/router";
import { useWorkspace } from "../../lib/workspace";

export const NAV: { id: Section; label: string; question: string; icon: LucideIcon }[] = [
  { id: "overview", label: "Resumen", question: "¿Qué tipo de sistema es?", icon: LayoutDashboard },
  { id: "session", label: "Sesión de Bob", question: "¿Cómo lo analizó IBM Bob?", icon: Activity },
  { id: "architecture", label: "Arquitectura", question: "¿Cómo funciona?", icon: Network },
  { id: "repository", label: "Repositorio", question: "¿Qué contiene?", icon: FolderTree },
  { id: "dependencies", label: "Dependencias", question: "¿De qué depende?", icon: Boxes },
  { id: "risks", label: "Riesgos", question: "¿Qué podría romperse?", icon: ShieldAlert },
  { id: "modernization", label: "Modernización", question: "¿Cómo migrar con seguridad?", icon: ArrowRightLeft },
  { id: "reports", label: "Reportes", question: "Entregables del análisis", icon: FileDown },
];

export function NavRail({ onNavigate }: { onNavigate?: () => void }) {
  const { route, navigate, dossier, flow } = useWorkspace();
  const blocking = dossier ? dossier.findings.filter((f) => f.severity === "critical" || f.severity === "high").length : 0;
  const hasJob = !!route.jobId;

  const itemClass = (active: boolean) =>
    `relative flex h-9 w-full items-center gap-2.5 rounded-inner px-3 text-body transition-[color,background-color] duration-150 ease-out ${active ? "bg-raised text-fg" : "text-muted hover:bg-raised hover:text-fg"}`;

  return (
    <nav aria-label="Workspace" className="flex h-full flex-col gap-1 p-3">
      <button type="button" onClick={() => { navigate({ jobId: null }); onNavigate?.(); }} aria-current={!hasJob ? "page" : undefined} className={itemClass(!hasJob)}>
        {!hasJob && <span aria-hidden className="absolute inset-y-2 left-0 w-0.5 rounded-pill bg-accent-hover" />}
        <History size={16} aria-hidden className="shrink-0" />
        Proyectos
      </button>

      <div className="mt-4 mb-1 px-3 text-micro tracking-eyebrow text-subtle uppercase">
        {hasJob ? (flow?.label ?? "Proyecto") : "Workspace"}
      </div>
      <ul className="space-y-0.5">
        {NAV.map((item) => {
          const active = hasJob && route.section === item.id;
          const Icon = item.icon;
          return (
            <li key={item.id}>
              <button
                type="button"
                disabled={!hasJob}
                title={hasJob ? item.question : "Abre o inicia un análisis para explorarlo"}
                aria-current={active ? "page" : undefined}
                onClick={() => { navigate({ jobId: route.jobId, section: item.id }); onNavigate?.(); }}
                className={`${itemClass(active)} disabled:cursor-not-allowed disabled:opacity-35`}
              >
                {active && <span aria-hidden className="absolute inset-y-2 left-0 w-0.5 rounded-pill bg-accent-hover" />}
                <Icon size={16} aria-hidden className="shrink-0" />
                <span className="truncate">{item.label}</span>
                {item.id === "risks" && blocking > 0 && (
                  <span className="ml-auto font-mono text-caption text-risk-high tabular-nums" title={`${blocking} críticos o altos`}>
                    {blocking}<span className="sr-only"> hallazgos críticos o altos</span>
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
