import { useMemo } from "react";
import { GRAPH_H, GRAPH_W, layoutGraph } from "../lib/layout";
import type { GraphData } from "../types";

export interface Layers {
  structure: boolean;
  findings: boolean;
  blast: boolean;
}

const SEV_VAR: Record<string, string> = {
  CRITICAL: "var(--sev-critical)",
  critical: "var(--sev-critical)",
  HIGH: "var(--sev-high)",
  high: "var(--sev-high)",
  MEDIUM: "var(--sev-medium)",
  medium: "var(--sev-medium)",
  LOW: "var(--sev-low)",
  low: "var(--sev-low)",
  INFO: "var(--muted)",
  info: "var(--muted)",
};
const SEV_RANK = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];

interface Props {
  graph: GraphData;
  layers: Layers;
  selectedId: string | null;
  focusFindingId: string | null;
  onSelect: (id: string | null) => void;
}

/**
 * Grafo de funciones estilo "red neuronal". Cada nodo es una función real del repo; cada arista, una
 * llamada real. Las capas (hallazgos, radio de explosión, migración) se encienden según la etapa.
 */
export function NeuralGraph({ graph, layers, selectedId, focusFindingId, onSelect }: Props) {
  const positions = useMemo(() => layoutGraph(graph), [graph.nodes.length, graph.edges.length, graph.nodes[0]?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const derived = useMemo(() => {
    const worst = new Map<string, string>();
    for (const mark of graph.findings) {
      if (!mark.node || mark.status === "rejected") continue;
      const current = worst.get(mark.node);
      if (!current || SEV_RANK.indexOf(mark.severity.toUpperCase()) < SEV_RANK.indexOf(current)) worst.set(mark.node, mark.severity.toUpperCase());
    }
    const origin = new Set<string>();
    const impacted = new Set<string>();
    for (const blast of graph.blast_radius) {
      if (focusFindingId && blast.finding_id !== focusFindingId) continue;
      blast.origin_nodes.forEach((id) => origin.add(id));
      blast.impacted_nodes.forEach((id) => impacted.add(id));
    }
    const focusNodes = new Set<string>();
    if (focusFindingId) graph.findings.filter((m) => m.finding_id === focusFindingId && m.node).forEach((m) => focusNodes.add(m.node!));
    return { worst, origin, impacted, focusNodes };
  }, [graph, focusFindingId]);

  const visible = () => layers.structure;
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));

  const files = useMemo(() => {
    const groups = new Map<string, { x: number; y: number; n: number }>();
    for (const node of graph.nodes) {
      const p = positions[node.id];
      if (!p) continue;
      const g = groups.get(node.file) ?? { x: 0, y: 0, n: 0 };
      groups.set(node.file, { x: g.x + p.x, y: g.y + p.y, n: g.n + 1 });
    }
    return [...groups.entries()].map(([file, g]) => ({ file, x: g.x / g.n, y: g.y / g.n }));
  }, [graph.nodes, positions]);

  const activeSet = new Set<string>();
  if (selectedId) {
    activeSet.add(selectedId);
    graph.edges.forEach((e) => {
      if (e.source === selectedId) activeSet.add(e.target);
      if (e.target === selectedId) activeSet.add(e.source);
    });
  }

  return (
    <svg viewBox={`0 0 ${GRAPH_W} ${GRAPH_H}`} role="img" aria-label="Grafo de llamadas entre funciones del repositorio" className="h-auto w-full rounded-xl border border-line bg-code" onClick={() => onSelect(null)}>
      <defs>
        <filter id="glow" x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur stdDeviation="4" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <radialGradient id="bg" cx="50%" cy="50%" r="70%">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.07" />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
        </radialGradient>
        <style>{`
          @keyframes ca-flow { to { stroke-dashoffset: -24; } }
          @keyframes ca-pulse { 0%,100% { opacity: .35; transform: scale(1); } 50% { opacity: 1; transform: scale(1.35); } }
          .ca-flow { stroke-dasharray: 4 8; animation: ca-flow 1s linear infinite; }
          .ca-pulse { transform-box: fill-box; transform-origin: center; animation: ca-pulse 1.6s ease-in-out infinite; }
          @media (prefers-reduced-motion: reduce) { .ca-flow, .ca-pulse { animation: none; } }
        `}</style>
      </defs>
      <rect width={GRAPH_W} height={GRAPH_H} fill="url(#bg)" />

      {layers.structure &&
        files.map((f) => (
          <text key={f.file} x={f.x} y={f.y - 46} textAnchor="middle" className="fill-muted" fontSize="11" fontFamily="var(--font-mono)" opacity="0.55">
            {f.file}
          </text>
        ))}

      {/* aristas: llamadas reales */}
      {graph.edges.map((edge) => {
        const a = positions[edge.source];
        const b = positions[edge.target];
        const na = nodeById.get(edge.source);
        const nb = nodeById.get(edge.target);
        if (!a || !b || !na || !nb || !visible()) return null;
        const active = selectedId !== null && (edge.source === selectedId || edge.target === selectedId);
        const inBlast = layers.blast && derived.impacted.has(edge.source) && (derived.impacted.has(edge.target) || derived.origin.has(edge.target));
        const mx = (a.x + b.x) / 2 + (b.y - a.y) * 0.12;
        const my = (a.y + b.y) / 2 - (b.x - a.x) * 0.12;
        return (
          <path
            key={`${edge.source}>${edge.target}`}
            d={`M${a.x},${a.y} Q${mx},${my} ${b.x},${b.y}`}
            fill="none"
            stroke={inBlast ? "var(--warn)" : active ? "var(--accent)" : "var(--muted)"}
            strokeOpacity={active || inBlast ? 0.95 : selectedId ? 0.1 : 0.28}
            strokeWidth={active || inBlast ? 1.8 : 1}
            className={active || inBlast ? "ca-flow" : undefined}
          />
        );
      })}

      {/* nodos */}
      {graph.nodes.map((node) => {
        const p = positions[node.id];
        if (!p || !visible()) return null;
        const span = node.line_end - node.line_start + 1;
        const r = Math.max(6, Math.min(15, 5 + Math.sqrt(span) * 1.1));
        const worst = layers.findings ? derived.worst.get(node.id) : undefined;
        const isOrigin = layers.blast && derived.origin.has(node.id);
        const isImpacted = layers.blast && derived.impacted.has(node.id);
        const dim = selectedId !== null && !activeSet.has(node.id);
        const fill = "var(--accent)";
        const showLabel = !dim && (node.id === selectedId || activeSet.has(node.id) || !!node.route || !!worst || isOrigin || derived.focusNodes.has(node.id));
        return (
          <g key={node.id} opacity={dim ? 0.22 : 1} className="cursor-pointer transition-opacity" onClick={(event) => { event.stopPropagation(); onSelect(node.id === selectedId ? null : node.id); }}>
            <title>{`${node.file}:${node.line_start}-${node.line_end} · ${node.qualname}`}</title>
            {(isImpacted || isOrigin) && <circle cx={p.x} cy={p.y} r={r + 9} fill={isOrigin ? "var(--bad)" : "var(--warn)"} opacity="0.22" className="ca-pulse" />}
            {worst && <circle cx={p.x} cy={p.y} r={r + 5} fill="none" stroke={SEV_VAR[worst]} strokeWidth="2" className="ca-pulse" />}
            <circle cx={p.x} cy={p.y} r={r} fill={fill} fillOpacity={node.route ? 0.95 : 0.7} stroke={node.id === selectedId ? "var(--fg)" : fill} strokeWidth={node.id === selectedId ? 2.5 : 1} filter="url(#glow)" />
            {node.route && <circle cx={p.x} cy={p.y} r={2.4} fill="var(--accent-fg)" />}
            {showLabel && (
              <text x={p.x} y={p.y + r + 13} textAnchor="middle" fontSize="10.5" fontFamily="var(--font-mono)" className="fill-fg" paintOrder="stroke" stroke="var(--code-bg)" strokeWidth="3">
                {node.name}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
