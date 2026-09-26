import type { GraphData } from "../types";

export const GRAPH_W = 1000;
export const GRAPH_H = 640;

export interface Positioned {
  x: number;
  y: number;
}

function hash(text: string): number {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967295;
}

/**
 * Disposición por fuerzas (determinista): repulsión entre nodos, muelles en las llamadas y una
 * atracción hacia el centro de su archivo, con los archivos repartidos en un anillo.
 */
export function layoutCallGraph(graph: Pick<GraphData, "nodes" | "edges">): Record<string, Positioned> {
  const files = [...new Set(graph.nodes.map((node) => node.file))].sort();
  const cx = GRAPH_W / 2;
  const cy = GRAPH_H / 2;
  const ringX = GRAPH_W * 0.4;
  const ringY = GRAPH_H * 0.38;
  const center = new Map(
    files.map((file, index) => {
      const angle = (index / Math.max(files.length, 1)) * Math.PI * 2 - Math.PI / 2;
      return [file, { x: cx + Math.cos(angle) * ringX, y: cy + Math.sin(angle) * ringY }];
    }),
  );

  const pos = graph.nodes.map((node) => {
    const home = center.get(node.file)!;
    return { id: node.id, file: node.file, x: home.x + (hash(node.id) - 0.5) * 60, y: home.y + (hash(`${node.id}y`) - 0.5) * 60, vx: 0, vy: 0 };
  });
  const index = new Map(pos.map((p, i) => [p.id, i]));

  for (let step = 0; step < 320; step++) {
    const cooling = 1 - step / 320;
    for (let i = 0; i < pos.length; i++) {
      for (let j = i + 1; j < pos.length; j++) {
        const dx = pos[i].x - pos[j].x;
        const dy = pos[i].y - pos[j].y;
        const dist2 = Math.max(dx * dx + dy * dy, 25);
        const force = 7000 / dist2;
        const dist = Math.sqrt(dist2);
        pos[i].vx += (dx / dist) * force;
        pos[i].vy += (dy / dist) * force;
        pos[j].vx -= (dx / dist) * force;
        pos[j].vy -= (dy / dist) * force;
      }
    }
    for (const edge of graph.edges) {
      const a = pos[index.get(edge.source)!];
      const b = pos[index.get(edge.target)!];
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.max(Math.hypot(dx, dy), 1);
      const pull = (dist - 120) * 0.01;
      a.vx += (dx / dist) * pull;
      a.vy += (dy / dist) * pull;
      b.vx -= (dx / dist) * pull;
      b.vy -= (dy / dist) * pull;
    }
    for (const p of pos) {
      const home = center.get(p.file)!;
      p.vx += (home.x - p.x) * 0.012 + (cx - p.x) * 0.001;
      p.vy += (home.y - p.y) * 0.012 + (cy - p.y) * 0.001;
      p.x += Math.max(-12, Math.min(12, p.vx)) * cooling;
      p.y += Math.max(-12, Math.min(12, p.vy)) * cooling;
      p.vx *= 0.6;
      p.vy *= 0.6;
    }
  }

  return Object.fromEntries(
    pos.map((p) => [p.id, { x: Math.max(40, Math.min(GRAPH_W - 40, p.x)), y: Math.max(40, Math.min(GRAPH_H - 40, p.y)) }]),
  );
}

export interface LayeredNode {
  id: string;
  layer: number;
  row: number;
}

/** Aristas que cierran un ciclo (DFS): se ignoran al asignar capas para que un ciclo no alargue el diagrama. */
function backEdges(ids: string[], edges: { source: string; target: string }[]): Set<string> {
  const out = new Map(ids.map((id) => [id, [] as string[]]));
  for (const edge of edges) out.get(edge.source)?.push(edge.target);
  const state = new Map<string, 0 | 1 | 2>();
  const back = new Set<string>();
  const visit = (id: string) => {
    state.set(id, 1);
    for (const next of [...(out.get(id) ?? [])].sort()) {
      if (state.get(next) === 1) back.add(`${id}>${next}`);
      else if (!state.get(next)) visit(next);
    }
    state.set(id, 2);
  };
  const indegree = new Map(ids.map((id) => [id, 0]));
  for (const edge of edges) indegree.set(edge.target, (indegree.get(edge.target) ?? 0) + 1);
  // Se empieza por las raíces (sin llamadores) para que las aristas "hacia atrás" sean las del ciclo.
  for (const id of [...ids].sort((a, b) => indegree.get(a)! - indegree.get(b)! || a.localeCompare(b))) {
    if (!state.get(id)) visit(id);
  }
  return back;
}

/**
 * Disposición por capas (izquierda → derecha) para el mapa de módulos: la capa de un nodo es la
 * longitud del camino más largo desde un nodo sin llamadores, sin contar las aristas de un ciclo.
 */
export function layoutLayers(ids: string[], edges: { source: string; target: string }[]): LayeredNode[] {
  const known = new Set(ids);
  const valid = edges.filter((edge) => known.has(edge.source) && known.has(edge.target) && edge.source !== edge.target);
  const back = backEdges(ids, valid);
  const forward = valid.filter((edge) => !back.has(`${edge.source}>${edge.target}`));
  const layer = new Map(ids.map((id) => [id, 0]));
  for (let round = 0; round < ids.length; round++) {
    let changed = false;
    for (const edge of forward) {
      const next = layer.get(edge.source)! + 1;
      if (next > layer.get(edge.target)!) {
        layer.set(edge.target, next);
        changed = true;
      }
    }
    if (!changed) break;
  }
  const rows = new Map<number, number>();
  return [...ids]
    .sort((a, b) => layer.get(a)! - layer.get(b)! || a.localeCompare(b))
    .map((id) => {
      const l = layer.get(id)!;
      const row = rows.get(l) ?? 0;
      rows.set(l, row + 1);
      return { id, layer: l, row };
    });
}
