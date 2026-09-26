import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError, jobsApi } from "../api";
import { NeuralGraph, type Layers } from "../components/NeuralGraph";
import { Timeline } from "../components/Timeline";
import { Button, Card, EmptyState, ErrorState, Loading, PageHeader, SeverityBadge } from "../components/ui";
import type { FlowJob, GraphData, Severity } from "../types";

const POLL_MS = 2000;
const REPLAY_MS = 1400;
const TOTAL_STAGES = 11;

/** Etapa a partir de la cual el pipeline deja cada capa (worker.py: 3 valida, 5 radio, 8 corte). */
const LAYER_FROM = { findings: 3, blast: 5, migration: 8 } as const;

const toSeverity = (value: string): Severity => value.toLowerCase() as Severity;

interface Props {
  flow: FlowJob | null;
  onGoHome: () => void;
  onOpenFinding: (id: string) => void;
}

export function NeuralView({ flow, onGoHome, onOpenFinding }: Props) {
  const jobId = flow?.id ?? null;
  const engineOk = flow?.engine === "jobs";
  const running = flow?.status === "queued" || flow?.status === "running";

  const [graph, setGraph] = useState<GraphData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waiting, setWaiting] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [focusFinding, setFocusFinding] = useState<string | null>(null);
  const [viewStage, setViewStage] = useState<number | null>(null);
  const [replaying, setReplaying] = useState(false);
  const [tick, setTick] = useState(0);
  const replayTimer = useRef<number | undefined>(undefined);

  // Carga el grafo real; mientras el job corre se refresca para ver aparecer nodos y marcas.
  useEffect(() => {
    if (!jobId || !engineOk) return;
    let cancelled = false;
    let timer: number | undefined;
    const load = () => {
      jobsApi
        .graph(jobId)
        .then((data) => {
          if (cancelled) return;
          setGraph(data);
          setError(null);
          setWaiting(false);
          if (running || !data.has_result) timer = window.setTimeout(load, POLL_MS);
        })
        .catch((err: Error) => {
          if (cancelled) return;
          if (err instanceof ApiError && err.status === 404 && running) {
            setWaiting(true);
            timer = window.setTimeout(load, POLL_MS);
          } else setError(err.message);
        });
    };
    setGraph(null);
    setSelected(null);
    setFocusFinding(null);
    load();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [jobId, engineOk, running, tick]);

  useEffect(() => () => window.clearInterval(replayTimer.current), []);
  useEffect(() => {
    setViewStage(null);
    setReplaying(false);
    window.clearInterval(replayTimer.current);
  }, [jobId]);

  const stage = viewStage ?? flow?.current_stage ?? 0;
  const layers: Layers = {
    structure: stage >= 1,
    findings: stage >= LAYER_FROM.findings,
    blast: stage >= LAYER_FROM.blast,
    migration: stage >= LAYER_FROM.migration,
  };

  const startReplay = () => {
    window.clearInterval(replayTimer.current);
    setReplaying(true);
    setFocusFinding(null);
    let next = 1;
    setViewStage(next);
    replayTimer.current = window.setInterval(() => {
      next += 1;
      if (next > TOTAL_STAGES) {
        window.clearInterval(replayTimer.current);
        setReplaying(false);
        setViewStage(null);
      } else setViewStage(next);
    }, REPLAY_MS);
  };

  const findingList = useMemo(() => {
    if (!graph) return [];
    const seen = new Map<string, { id: string; title: string; severity: string; status: string; nodes: Set<string> }>();
    for (const mark of graph.findings) {
      const item = seen.get(mark.finding_id) ?? { id: mark.finding_id, title: mark.title, severity: mark.severity, status: mark.status, nodes: new Set<string>() };
      if (mark.node) item.nodes.add(mark.node);
      seen.set(mark.finding_id, item);
    }
    return [...seen.values()];
  }, [graph]);

  const node = graph?.nodes.find((item) => item.id === selected) ?? null;
  const nodeInfo = useMemo(() => {
    if (!graph || !node) return null;
    const name = (id: string) => graph.nodes.find((n) => n.id === id);
    return {
      callers: graph.edges.filter((e) => e.target === node.id).map((e) => name(e.source)).filter((n) => !!n),
      callees: graph.edges.filter((e) => e.source === node.id).map((e) => name(e.target)).filter((n) => !!n),
      marks: graph.findings.filter((m) => m.node === node.id),
      blast: graph.blast_radius.filter((b) => b.origin_nodes.includes(node.id) || b.impacted_nodes.includes(node.id)),
      migrated: graph.migration_cut?.legacy_node === node.id,
      modern: graph.migration_cut?.modern_nodes.includes(node.id) ?? false,
    };
  }, [graph, node]);

  if (!flow || !engineOk) {
    return (
      <>
        <PageHeader title="Mapa neuronal" />
        <EmptyState icon="✦" title={flow ? "Este análisis no tiene grafo" : "Aún no hay un análisis"} action={<Button onClick={onGoHome}>Ir a Inicio</Button>}>
          {flow
            ? "El mapa se construye con el motor /api/jobs, que analiza el código real del repositorio. Este análisis se ejecutó sin ese motor."
            : "Lanza un análisis para ver qué funciones toca cada etapa del pipeline."}
        </EmptyState>
      </>
    );
  }

  const selectFinding = (id: string) => {
    const next = focusFinding === id ? null : id;
    setFocusFinding(next);
    if (next) {
      const first = findingList.find((f) => f.id === next)?.nodes.values().next().value ?? null;
      setSelected(first);
      if (stage < LAYER_FROM.findings) setViewStage(LAYER_FROM.findings);
    }
  };

  return (
    <>
      <PageHeader
        title="Mapa neuronal del código"
        subtitle="Cada nodo es una función real del repositorio y cada arista una llamada. Las capas se encienden con la etapa del pipeline que las produce."
        right={
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={startReplay} disabled={replaying || !graph}>
              {replaying ? "Reproduciendo…" : "▶ Repetir etapas"}
            </Button>
            {viewStage !== null && !replaying && <Button variant="ghost" onClick={() => setViewStage(null)}>Volver al estado actual</Button>}
          </div>
        }
      />

      {error && <div className="mb-4"><ErrorState message={error} onRetry={() => setTick((v) => v + 1)} /></div>}

      <div className="grid gap-5 xl:grid-cols-[300px_minmax(0,1fr)]">
        <Card className="p-4 xl:max-h-[calc(100vh-7rem)] xl:overflow-auto">
          <h2 className="mb-3 text-sm font-semibold">Etapas del pipeline</h2>
          <Timeline job={flow} selectedStage={viewStage ?? undefined} onSelectStage={(n) => { window.clearInterval(replayTimer.current); setReplaying(false); setViewStage(n); }} />
        </Card>

        <div className="min-w-0 space-y-4">
          {waiting && !graph && <Loading label="Esperando a que el pipeline prepare el repositorio…" />}
          {!waiting && !graph && !error && <Loading label="Construyendo el grafo…" />}
          {graph && graph.nodes.length === 0 && <EmptyState title="No se encontraron funciones Python">El repositorio analizado no tiene funciones que graficar.</EmptyState>}
          {graph && graph.nodes.length > 0 && (
            <>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted" aria-label="Leyenda">
                <span><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-accent" />Función legada</span>
                <span><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-ok" />Función moderna</span>
                <span><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full border-2 border-[var(--sev-high)]" />Hallazgo (color = severidad)</span>
                <span><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-bad/50" />Origen del impacto</span>
                <span><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-warn/50" />Afectada por radio de explosión</span>
                <span><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full border border-dashed border-ok" />Ruta migrada</span>
                <span className="ml-auto font-mono">{graph.nodes.length} funciones · {graph.edges.length} llamadas · vista: etapa {stage || "—"}/{TOTAL_STAGES}</span>
              </div>

              <NeuralGraph graph={graph} layers={layers} selectedId={selected} focusFindingId={focusFinding} onSelect={setSelected} />

              {!layers.findings && graph.has_result && <p className="text-xs text-muted">Los hallazgos se validan en la etapa 3; avanza la vista para verlos sobre el grafo.</p>}
              {!graph.has_result && <p className="text-xs text-muted">El expediente aún no está listo: se muestra solo la estructura. Las marcas aparecen cuando el pipeline las guarda.</p>}

              <div className="grid gap-4 lg:grid-cols-2">
                <Card className="p-4">
                  <h2 className="mb-3 text-sm font-semibold">Dónde toca cada hallazgo</h2>
                  {findingList.length === 0 ? (
                    <p className="text-sm text-muted">Sin hallazgos todavía.</p>
                  ) : (
                    <ul className="space-y-1">
                      {findingList.map((finding) => (
                        <li key={finding.id}>
                          <button type="button" onClick={() => selectFinding(finding.id)} aria-pressed={focusFinding === finding.id} className={`flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm transition hover:bg-surface-2 ${focusFinding === finding.id ? "bg-accent/10" : ""}`}>
                            <SeverityBadge severity={toSeverity(finding.severity)} />
                            <span className="font-mono text-xs text-muted">{finding.id}</span>
                            <span className="min-w-0 flex-1 truncate">{finding.title}</span>
                            {finding.status === "rejected" && <span className="text-[11px] text-bad">rechazado</span>}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>

                <Card className="p-4">
                  <h2 className="mb-3 text-sm font-semibold">{node ? "Función seleccionada" : "Detalle"}</h2>
                  {!node || !nodeInfo ? (
                    <p className="text-sm text-muted">Pulsa un nodo o un hallazgo para ver qué llama, qué lo llama y qué etapa lo toca.</p>
                  ) : (
                    <div className="space-y-3 text-sm">
                      <div>
                        <p className="font-mono font-semibold">{node.qualname}</p>
                        <p className="font-mono text-xs text-muted">{node.file}:{node.line_start}–{node.line_end}</p>
                        {node.route && <p className="mt-1 text-xs"><span className="rounded bg-accent/10 px-1.5 py-0.5 font-mono text-accent">{node.route.methods.join(",")} {node.route.rule}</span></p>}
                      </div>
                      {nodeInfo.migrated && <p className="rounded-lg bg-ok/10 px-3 py-2 text-xs text-ok">Ruta migrada en el corte Strangler ({graph.migration_cut?.endpoint}); +{graph.migration_cut?.diff_added} / −{graph.migration_cut?.diff_removed} líneas en el parche.</p>}
                      {nodeInfo.modern && <p className="rounded-lg bg-ok/10 px-3 py-2 text-xs text-ok">Código moderno generado en la etapa 8.</p>}
                      {nodeInfo.marks.length > 0 && (
                        <ul className="space-y-1">
                          {nodeInfo.marks.map((mark) => (
                            <li key={`${mark.finding_id}-${mark.line_start}`}>
                              <button type="button" onClick={() => onOpenFinding(mark.finding_id)} className="flex w-full items-center gap-2 text-left text-xs hover:text-accent">
                                <SeverityBadge severity={toSeverity(mark.severity)} />
                                <span className="min-w-0 flex-1 truncate">{mark.finding_id} · {mark.path}:{mark.line_start}–{mark.line_end}</span>
                                <span aria-hidden>→</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                      {nodeInfo.blast.length > 0 && <p className="text-xs text-muted">Radio de explosión: {nodeInfo.blast.map((b) => `${b.finding_id} (${b.score})`).join(", ")}</p>}
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div>
                          <p className="mb-1 text-muted">Lo llaman ({nodeInfo.callers.length})</p>
                          {nodeInfo.callers.map((n) => n && <button key={n.id} type="button" onClick={() => setSelected(n.id)} className="block font-mono hover:text-accent">{n.name}</button>)}
                        </div>
                        <div>
                          <p className="mb-1 text-muted">Llama a ({nodeInfo.callees.length})</p>
                          {nodeInfo.callees.map((n) => n && <button key={n.id} type="button" onClick={() => setSelected(n.id)} className="block font-mono hover:text-accent">{n.name}</button>)}
                        </div>
                      </div>
                    </div>
                  )}
                </Card>
              </div>

              {graph.blast_radius.some((b) => b.unresolved_symbols.length > 0) && layers.blast && (
                <p className="text-xs text-muted">
                  Nota: {graph.blast_radius.reduce((total, b) => total + b.unresolved_symbols.length, 0)} símbolos del radio de explosión reportados por el pipeline no corresponden a funciones existentes en el repositorio y no se dibujan.
                </p>
              )}
              <p className="text-xs text-muted">{graph.notes}</p>
            </>
          )}
        </div>
      </div>
    </>
  );
}
