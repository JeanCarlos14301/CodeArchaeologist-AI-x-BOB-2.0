import { useMemo, type KeyboardEvent } from "react";
import { GRAPH_H, GRAPH_W, layoutCallGraph } from "../../lib/graphLayout";
import { SEVERITY_ORDER, SEVERITY_VAR, toSeverity } from "../../lib/severity";
import type { GraphData, Severity } from "../../types";

export interface Layers {
  findings: boolean;
  impact: boolean;
}

interface Props {
  graph: GraphData;
  layers: Layers;
  selectedId: string | null;
  focusFindingId: string | null;
  onSelect: (id: string | null) => void;
}

/**
 * Grafo de llamadas real: nodo = función (AST), arista = llamada. Capas opcionales: hallazgos
 * (anillo con el color de la peor severidad) e impacto (origen en rojo, llamadores en amarillo).
 */
export function CallGraph({ graph, layers, selectedId, focusFindingId, onSelect }: Props) {
  const positions = useMemo(() => layoutCallGraph(graph), [graph]);

  const derived = useMemo(() => {
    const worst = new Map<string, Severity>();
    for (const mark of graph.findings) {
      if (!mark.node || mark.status === "rejected") continue;
      const severity = toSeverity(mark.severity);
      const current = worst.get(mark.node);
      if (!current || SEVERITY_ORDER.indexOf(severity) < SEVERITY_ORDER.indexOf(current)) worst.set(mark.node, severity);
    }
    const origin = new Set<string>();
    const impacted = new Set<string>();
    for (const blast of graph.blast_radius) {
      if (focusFindingId && blast.finding_id !== focusFindingId) continue;
      blast.origin_nodes.forEach((id) => origin.add(id));
      blast.impacted_nodes.forEach((id) => impacted.add(id));
    }
    const files = new Map<string, { x: number; y: number; n: number }>();
    for (const node of graph.nodes) {
      const p = positions[node.id];
      if (!p) continue;
      const g = files.get(node.file) ?? { x: 0, y: 0, n: 0 };
      files.set(node.file, { x: g.x + p.x, y: Math.min(g.y || Infinity, p.y), n: g.n + 1 });
    }
    return { worst, origin, impacted, files: [...files.entries()].map(([file, g]) => ({ file, x: g.x / g.n, y: g.y })) };
  }, [graph, positions, focusFindingId]);

  const neighbors = useMemo(() => {
    const set = new Set<string>();
    if (!selectedId) return set;
    set.add(selectedId);
    for (const edge of graph.edges) {
      if (edge.source === selectedId) set.add(edge.target);
      if (edge.target === selectedId) set.add(edge.source);
    }
    return set;
  }, [graph.edges, selectedId]);

  const onKey = (event: KeyboardEvent, id: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(id === selectedId ? null : id);
    }
  };

  return (
    <svg
      viewBox={`0 0 ${GRAPH_W} ${GRAPH_H}`}
      role="group"
      aria-label={`Grafo de llamadas: ${graph.nodes.length} funciones y ${graph.edges.length} llamadas`}
      className="block h-auto w-full"
      onClick={() => onSelect(null)}
    >
      <defs>
        <style>{`
          @keyframes cg-flow { to { stroke-dashoffset: -16; } }
          .cg-flow { stroke-dasharray: 3 5; animation: cg-flow 0.9s linear infinite; }
          @media (prefers-reduced-motion: reduce) { .cg-flow { animation: none; } }
        `}</style>
      </defs>

      {derived.files.map((f) => (
        <text key={f.file} x={f.x} y={Math.max(14, f.y - 26)} textAnchor="middle" fontSize="10.5" className="fill-subtle font-mono">
          {f.file}
        </text>
      ))}

      {graph.edges.map((edge) => {
        const a = positions[edge.source];
        const b = positions[edge.target];
        if (!a || !b) return null;
        const active = selectedId !== null && (edge.source === selectedId || edge.target === selectedId);
        const inImpact = layers.impact && derived.impacted.has(edge.source) && (derived.impacted.has(edge.target) || derived.origin.has(edge.target));
        const mx = (a.x + b.x) / 2 + (b.y - a.y) * 0.12;
        const my = (a.y + b.y) / 2 - (b.x - a.x) * 0.12;
        const stroke = inImpact ? "var(--color-warning)" : active ? "var(--color-accent-hover)" : "var(--color-line-strong)";
        return (
          <path
            key={`${edge.source}>${edge.target}`}
            d={`M${a.x},${a.y} Q${mx},${my} ${b.x},${b.y}`}
            fill="none"
            stroke={stroke}
            strokeOpacity={selectedId && !active && !inImpact ? 0.35 : 1}
            strokeWidth={active || inImpact ? 1.5 : 1}
            className={active || inImpact ? "cg-flow" : undefined}
          />
        );
      })}

      {graph.nodes.map((node) => {
        const p = positions[node.id];
        if (!p) return null;
        const span = node.line_end - node.line_start + 1;
        const r = Math.max(4, Math.min(11, 3 + Math.sqrt(span) * 0.8));
        const worst = layers.findings ? derived.worst.get(node.id) : undefined;
        const isOrigin = layers.impact && derived.origin.has(node.id);
        const isImpacted = layers.impact && derived.impacted.has(node.id);
        const isSelected = node.id === selectedId;
        const dim = selectedId !== null && !neighbors.has(node.id);
        const showLabel = !dim && (isSelected || neighbors.has(node.id) || !!node.route || !!worst || isOrigin);
        const label = `${node.qualname} en ${node.file}:${node.line_start}${node.route ? `, ruta ${node.route.methods.join(",")} ${node.route.rule}` : ""}${worst ? `, hallazgo ${worst}` : ""}`;
        return (
          <g
            key={node.id}
            role="button"
            tabIndex={0}
            aria-label={label}
            aria-pressed={isSelected}
            opacity={dim ? 0.25 : 1}
            className="group cursor-pointer outline-none"
            onClick={(event) => {
              event.stopPropagation();
              onSelect(isSelected ? null : node.id);
            }}
            onKeyDown={(event) => onKey(event, node.id)}
          >
            <title>{label}</title>
            <circle cx={p.x} cy={p.y} r={r + 6} fill="none" stroke="var(--color-focus)" strokeWidth="2" className="opacity-0 group-focus-visible:opacity-100" />
            {(isOrigin || isImpacted) && <circle cx={p.x} cy={p.y} r={r + 7} fill={isOrigin ? "var(--color-danger)" : "var(--color-warning)"} opacity="0.18" />}
            {worst && <circle cx={p.x} cy={p.y} r={r + 3.5} fill="none" stroke={SEVERITY_VAR[worst]} strokeWidth="1.5" />}
            <circle
              cx={p.x}
              cy={p.y}
              r={r}
              fill={node.route ? "var(--color-fg)" : "var(--color-canvas)"}
              stroke={isSelected ? "var(--color-accent-hover)" : node.route ? "var(--color-fg)" : "var(--color-fg-2)"}
              strokeWidth={isSelected ? 2 : 1}
            />
            {showLabel && (
              <text x={p.x} y={p.y + r + 13} textAnchor="middle" fontSize="10.5" className="fill-fg-2 font-mono" paintOrder="stroke" stroke="var(--color-canvas)" strokeWidth="3">
                {node.name}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
