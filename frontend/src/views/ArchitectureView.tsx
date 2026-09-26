import { useEffect, useMemo, useState } from "react";
import { FileCode2, MessageSquareText } from "lucide-react";
import { CallGraph, type Layers } from "../components/domain/CallGraph";
import { ModuleMap } from "../components/domain/ModuleMap";
import { SeverityBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataList, Eyebrow, ScreenHeader, Section, Segmented } from "../components/ui/Layout";
import { EmptyState, ErrorState, Loading } from "../components/ui/States";
import { toSeverity } from "../lib/severity";
import { useResource, useWorkspace } from "../lib/workspace";
import type { ArchitectureData, Dossier, GraphData } from "../types";
import { JobGate } from "./JobGate";

type Tab = "modules" | "functions";

export function ArchitectureView() {
  return <JobGate>{(dossier) => <Architecture dossier={dossier} />}</JobGate>;
}

function Architecture({ dossier }: { dossier: Dossier }) {
  const { route } = useWorkspace();
  const architecture = useResource("architecture");
  const graph = useResource("graph");
  const [tab, setTab] = useState<Tab>(route.node || route.finding ? "functions" : "modules");
  // Un enlace a una función o al impacto de un hallazgo abre directamente el grafo de funciones.
  useEffect(() => {
    if (route.node || route.finding) setTab("functions");
  }, [route.node, route.finding]);

  const failed = architecture.error ?? graph.error;
  if (failed) return <div className="p-6"><ErrorState title="No se pudo medir la arquitectura." message={failed} onRetry={() => { architecture.retry(); graph.retry(); }} /></div>;
  if (!architecture.data || !graph.data) return <div className="p-6"><Loading label="Midiendo módulos, llamadas y rutas…" /></div>;
  const arch = architecture.data;

  return (
    <div className="px-6 py-6 @3xl:px-10">
      <ScreenHeader
        eyebrow="Arquitectura · ¿Cómo funciona este sistema?"
        title={`${arch.modules.length} módulos · ${arch.totals.functions} funciones · ${arch.totals.calls} llamadas`}
        description="Medido con análisis estático (AST, SQL, complejidad ciclomática) sobre el código del análisis. Nada se estima."
        actions={
          <Segmented<Tab> label="Vista de arquitectura" value={tab} onChange={setTab} options={[
            { value: "modules", label: "Módulos" },
            { value: "functions", label: "Funciones" },
          ]} />
        }
      />
      <div className="py-6">
        {tab === "modules" ? <ModulesPanel arch={arch} dossier={dossier} /> : <FunctionsPanel graph={graph.data} />}
      </div>
      <EntryPoints arch={arch} />
    </div>
  );
}

function ModulesPanel({ arch, dossier }: { arch: ArchitectureData; dossier: Dossier }) {
  const { route, go, seedComposer } = useWorkspace();
  const selected = route.file && arch.modules.some((m) => m.file === route.file) ? route.file : null;
  const module = arch.modules.find((m) => m.file === selected) ?? null;
  const incoming = arch.dependencies.filter((d) => d.target === selected);
  const outgoing = arch.dependencies.filter((d) => d.source === selected);
  const findings = dossier.findings.filter((f) => f.evidence.some((e) => e.path === selected));
  const inCycle = arch.circular_dependencies.some((cycle) => selected && cycle.includes(selected));

  return (
    <div className="grid gap-5 @4xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="min-w-0 space-y-3">
        <Legend />
        <ModuleMap data={arch} selected={selected} onSelect={(file) => go("architecture", { file: file ?? undefined })} />
      </div>
      <aside aria-label="Inspector de módulo" className="@4xl:border-l @4xl:border-line @4xl:pl-5">
        {!module ? (
          <p className="text-body text-muted">Selecciona un módulo para ver quién lo llama, a quién llama y qué hallazgos contiene. Los módulos de la izquierda son puntos de entrada; las flechas son llamadas medidas.</p>
        ) : (
          <div className="space-y-4">
            <div>
              <Eyebrow>Módulo</Eyebrow>
              <p className="mt-1 font-mono text-body text-fg">{module.file}</p>
              {inCycle && <p className="mt-1 text-caption text-danger">▲ Participa en una dependencia circular</p>}
            </div>
            <DataList rows={[
              { label: "Funciones", value: module.functions },
              { label: "Lo llaman", value: incoming.length ? incoming.map((d) => `${d.source} (${d.calls})`).join(", ") : "nadie" },
              { label: "Llama a", value: outgoing.length ? outgoing.map((d) => `${d.target} (${d.calls})`).join(", ") : "nadie" },
              { label: "Hallazgos", value: findings.length },
            ]} />
            {findings.length > 0 && (
              <ul className="space-y-1">
                {findings.map((f) => (
                  <li key={f.id}>
                    <button type="button" onClick={() => go("risks", { finding: f.id })} className="flex w-full items-baseline gap-2 rounded-inner px-2 py-1.5 text-left hover:bg-raised">
                      <SeverityBadge severity={f.severity} compact />
                      <span className="text-caption text-fg-2">{f.title}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-col gap-2 border-t border-line pt-4">
              <Button size="sm" icon={<MessageSquareText size={14} aria-hidden />} onClick={() => seedComposer(`¿Qué impacto tendría modificar ${module.file} y quién depende de él?`)}>Preguntar a Bob por el impacto</Button>
              <Button size="sm" variant="ghost" icon={<FileCode2 size={14} aria-hidden />} onClick={() => go("repository", { file: module.file })}>Abrir {module.file}</Button>
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}

function FunctionsPanel({ graph }: { graph: GraphData }) {
  const { route, go, seedComposer } = useWorkspace();
  const [layers, setLayers] = useState<Layers>({ findings: true, impact: true });
  const node = graph.nodes.find((n) => n.id === route.node) ?? null;
  const focusFinding = route.finding;

  const info = useMemo(() => {
    if (!node) return null;
    const byId = (id: string) => graph.nodes.find((n) => n.id === id);
    return {
      callers: graph.edges.filter((e) => e.target === node.id).map((e) => byId(e.source)).filter((n) => !!n),
      callees: graph.edges.filter((e) => e.source === node.id).map((e) => byId(e.target)).filter((n) => !!n),
      marks: graph.findings.filter((m) => m.node === node.id && m.status !== "rejected"),
    };
  }, [graph, node]);

  if (graph.nodes.length === 0) return <EmptyState title="No se encontraron funciones Python">El repositorio no tiene funciones que graficar.</EmptyState>;

  const toggle = (key: keyof Layers) => setLayers((current) => ({ ...current, [key]: !current[key] }));
  const findingIds = [...new Set(graph.findings.filter((m) => m.status !== "rejected").map((m) => m.finding_id))];

  return (
    <div className="grid gap-5 @4xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="min-w-0 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          {(["findings", "impact"] as const).map((key) => (
            <button key={key} type="button" role="switch" aria-checked={layers[key]} onClick={() => toggle(key)}
              className={`inline-flex h-7 items-center gap-2 rounded-pill border px-3 text-caption transition-[border-color,color] duration-150 ${layers[key] ? "border-line-strong text-fg" : "border-line text-subtle"}`}>
              <span aria-hidden className={`h-2 w-2 rounded-pill ${layers[key] ? (key === "findings" ? "bg-risk-high" : "bg-warning") : "bg-disabled"}`} />
              {key === "findings" ? "Capa de hallazgos" : "Capa de impacto"}
            </button>
          ))}
          <label className="sr-only" htmlFor="focus-finding">Enfocar impacto de un hallazgo</label>
          <select id="focus-finding" value={focusFinding ?? ""} onChange={(event) => go("architecture", { finding: event.target.value || undefined, node: route.node ?? undefined })}
            className="h-7 rounded-pill border border-line bg-control px-3 text-caption text-fg-2 focus:border-focus focus:outline-none">
            <option value="">Impacto de todos los hallazgos</option>
            {findingIds.map((id) => <option key={id} value={id}>Impacto de {id}</option>)}
          </select>
          <span className="ml-auto font-mono text-caption text-subtle">{graph.nodes.length} funciones · {graph.edges.length} llamadas</span>
        </div>
        <div className="overflow-hidden rounded-panel border border-line bg-surface">
          <CallGraph graph={graph} layers={layers} selectedId={node?.id ?? null} focusFindingId={focusFinding}
            onSelect={(id) => go("architecture", { node: id ?? undefined, finding: focusFinding ?? undefined })} />
        </div>
        <p className="text-caption text-subtle">
          <span className="mr-3"><span aria-hidden className="mr-1 inline-block h-2 w-2 rounded-pill bg-fg align-middle" />Punto de entrada HTTP</span>
          <span className="mr-3"><span aria-hidden className="mr-1 inline-block h-2 w-2 rounded-pill border border-fg-2 align-middle" />Función</span>
          <span className="mr-3"><span aria-hidden className="mr-1 inline-block h-2 w-2 rounded-pill bg-danger/60 align-middle" />Origen del hallazgo</span>
          <span><span aria-hidden className="mr-1 inline-block h-2 w-2 rounded-pill bg-warning/60 align-middle" />La llama (impacto)</span>
          {" · "}{graph.notes}
        </p>
      </div>
      <aside aria-label="Inspector de función" className="@4xl:border-l @4xl:border-line @4xl:pl-5">
        {!node || !info ? (
          <p className="text-body text-muted">Selecciona una función para ver quién la llama, a quién llama y qué hallazgos la tocan. Usa Tab para recorrer el grafo con el teclado.</p>
        ) : (
          <div className="space-y-4">
            <div>
              <Eyebrow>Función</Eyebrow>
              <p className="mt-1 font-mono text-body break-all text-fg">{node.qualname}</p>
              <p className="font-mono text-caption text-subtle">{node.file}:{node.line_start}–{node.line_end}</p>
              {node.route && <p className="mt-1 font-mono text-caption text-fg-2">{node.route.methods.join(",")} {node.route.rule}</p>}
            </div>
            {info.marks.length > 0 && (
              <ul className="space-y-1">
                {info.marks.map((mark) => (
                  <li key={`${mark.finding_id}-${mark.line_start}`}>
                    <button type="button" onClick={() => go("risks", { finding: mark.finding_id })} className="flex w-full items-baseline gap-2 rounded-inner px-2 py-1.5 text-left hover:bg-raised">
                      <SeverityBadge severity={toSeverity(mark.severity)} compact />
                      <span className="text-caption text-fg-2">{mark.finding_id} · {mark.title}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <NodeList title={`La llaman · ${info.callers.length}`} nodes={info.callers} onSelect={(id) => go("architecture", { node: id })} />
            <NodeList title={`Llama a · ${info.callees.length}`} nodes={info.callees} onSelect={(id) => go("architecture", { node: id })} />
            <div className="flex flex-col gap-2 border-t border-line pt-4">
              <Button size="sm" icon={<MessageSquareText size={14} aria-hidden />} onClick={() => seedComposer(`¿Qué podría romperse si modifico ${node.qualname} (${node.file})?`)}>Preguntar a Bob qué rompería</Button>
              <Button size="sm" variant="ghost" icon={<FileCode2 size={14} aria-hidden />} onClick={() => go("repository", { file: node.file, line: node.line_start })}>Ver código</Button>
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}

function NodeList({ title, nodes, onSelect }: { title: string; nodes: ({ id: string; name: string; file: string } | undefined)[]; onSelect: (id: string) => void }) {
  return (
    <div>
      <Eyebrow>{title}</Eyebrow>
      {nodes.length === 0 ? <p className="mt-1 text-caption text-subtle">Ninguna</p> : (
        <ul className="mt-1">
          {nodes.map((n) => n && (
            <li key={n.id}>
              <button type="button" onClick={() => onSelect(n.id)} className="w-full truncate rounded-inner px-2 py-1 text-left font-mono text-caption text-fg-2 hover:bg-raised hover:text-fg">
                {n.name} <span className="text-subtle">· {n.file}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Legend() {
  return (
    <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-subtle">
      <span>Barra izquierda = peor severidad del módulo</span>
      <span>Número sobre la flecha = llamadas medidas</span>
      <span className="text-danger">- - - dependencia circular</span>
    </p>
  );
}

function EntryPoints({ arch }: { arch: ArchitectureData }) {
  const { go } = useWorkspace();
  return (
    <div className="grid gap-x-12 @4xl:grid-cols-2">
      <Section eyebrow="Puntos de entrada" title={`Rutas HTTP · ${arch.routes.length}`}>
        {arch.routes.length === 0 ? <p className="text-body text-muted">No se detectaron rutas HTTP.</p> : (
          <table className="w-full text-left">
            <thead><tr className="border-b border-line text-micro tracking-eyebrow text-subtle uppercase"><th className="py-2 font-medium">Método · ruta</th><th className="py-2 text-right font-medium">Definida en</th></tr></thead>
            <tbody className="divide-y divide-line-subtle">
              {arch.routes.map((r) => (
                <tr key={`${r.file}:${r.line_start}:${r.rule}`}>
                  <td className="py-2 font-mono text-caption"><span className="text-subtle">{r.methods.join(",")}</span> <span className="text-fg">{r.rule}</span></td>
                  <td className="py-2 text-right">
                    <button type="button" onClick={() => go("repository", { file: r.file, line: r.line_start })} className="font-mono text-caption text-fg-2 hover:text-fg">{r.file}:{r.line_start}</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
      <Section eyebrow="Puntos calientes" title="Funciones más complejas">
        {arch.complex_functions.length === 0 ? <p className="text-body text-muted">No se pudo medir la complejidad.</p> : (
          <table className="w-full text-left">
            <thead><tr className="border-b border-line text-micro tracking-eyebrow text-subtle uppercase"><th className="py-2 font-medium">Función</th><th className="py-2 text-right font-medium">Complejidad</th><th className="py-2 text-right font-medium">Líneas</th></tr></thead>
            <tbody className="divide-y divide-line-subtle">
              {arch.complex_functions.map((fn) => (
                <tr key={`${fn.file}:${fn.line_start}`}>
                  <td className="py-2">
                    <button type="button" onClick={() => go("repository", { file: fn.file, line: fn.line_start })} className="text-left font-mono text-caption text-fg hover:text-fg-2">{fn.name}</button>
                    <span className="block font-mono text-micro text-subtle">{fn.file}:{fn.line_start}</span>
                  </td>
                  <td className="py-2 text-right font-mono text-caption tabular-nums">
                    <span className={fn.complexity > 20 ? "text-risk-high" : "text-fg"}>{fn.complexity}</span> <span className="text-subtle">({fn.rank})</span>
                  </td>
                  <td className="py-2 text-right font-mono text-caption text-fg-2 tabular-nums">{fn.lines}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
    </div>
  );
}
