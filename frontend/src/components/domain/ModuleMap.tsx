import { useMemo, useState, type KeyboardEvent } from "react";
import { layoutLayers } from "../../lib/graphLayout";
import { SEVERITY_VAR } from "../../lib/severity";
import type { ArchitectureData } from "../../types";

const NODE_W = 176;
const NODE_H = 54;
const COL_GAP = 96;
const ROW_GAP = 18;
const PAD = 24;
const ISOLATED_GAP = 56;
/** Por debajo de este ancho el texto sería ilegible: se permite scroll horizontal. */
const MIN_RENDER_W = 640;

interface Props {
  data: ArchitectureData;
  selected: string | null;
  onSelect: (file: string | null) => void;
}

/**
 * Mapa de módulos por capas: de los puntos de entrada (izquierda) a las dependencias (derecha).
 * Aristas = llamadas medidas por AST entre archivos. Aristas de un ciclo: discontinuas y en rojo.
 */
export function ModuleMap({ data, selected, onSelect }: Props) {
  const [hover, setHover] = useState<string | null>(null);

  const layout = useMemo(() => {
    const connected = new Set(data.dependencies.flatMap((dep) => [dep.source, dep.target]));
    const linked = data.modules.filter((module) => connected.has(module.file)).map((module) => module.file);
    const isolated = data.modules.filter((module) => !connected.has(module.file)).map((module) => module.file);
    const layered = layoutLayers(linked, data.dependencies);
    const pos = new Map<string, { x: number; y: number }>();
    for (const item of layered) pos.set(item.id, { x: PAD + item.layer * (NODE_W + COL_GAP), y: PAD + item.row * (NODE_H + ROW_GAP) });
    const layers = Math.max(1, ...layered.map((item) => item.layer + 1));
    const rows = Math.max(1, ...layered.map((item) => item.row + 1));
    const isolatedTop = PAD + rows * (NODE_H + ROW_GAP) + (isolated.length ? ISOLATED_GAP : 0);
    const perRow = Math.max(1, layers);
    isolated.forEach((file, i) => pos.set(file, {
      x: PAD + (i % perRow) * (NODE_W + COL_GAP),
      y: isolatedTop + Math.floor(i / perRow) * (NODE_H + ROW_GAP),
    }));
    const isolatedRows = Math.ceil(isolated.length / perRow);
    return {
      pos,
      isolatedTop,
      hasIsolated: isolated.length > 0,
      width: PAD * 2 + layers * NODE_W + (layers - 1) * COL_GAP,
      height: isolatedRows
        ? isolatedTop + isolatedRows * (NODE_H + ROW_GAP) - ROW_GAP + PAD
        : PAD + rows * (NODE_H + ROW_GAP) - ROW_GAP + PAD,
    };
  }, [data]);

  const cyclePairs = useMemo(() => {
    const pairs = new Set<string>();
    for (const cycle of data.circular_dependencies) {
      for (let i = 0; i < cycle.length - 1; i++) pairs.add(`${cycle[i]}>${cycle[i + 1]}`);
    }
    return pairs;
  }, [data.circular_dependencies]);

  const focus = hover ?? selected;
  const neighbors = useMemo(() => {
    const set = new Set<string>();
    if (!focus) return set;
    set.add(focus);
    for (const dep of data.dependencies) {
      if (dep.source === focus) set.add(dep.target);
      if (dep.target === focus) set.add(dep.source);
    }
    return set;
  }, [focus, data.dependencies]);

  const onKey = (event: KeyboardEvent, file: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(file === selected ? null : file);
    }
  };

  return (
    <div className="overflow-auto rounded-panel border border-line bg-surface">
      <svg
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        preserveAspectRatio="xMinYMin meet"
        style={{ width: "100%", minWidth: Math.min(layout.width, MIN_RENDER_W) }}
        className="block h-auto"
        role="group"
        aria-label="Mapa de módulos y sus dependencias medidas"
      >
        <defs>
          <marker id="mm-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L8,4 L0,8 z" fill="currentColor" />
          </marker>
        </defs>

        {layout.hasIsolated && (
          <text x={PAD} y={layout.isolatedTop - 16} className="fill-subtle font-sans" fontSize="10" letterSpacing="1.4">
            SIN LLAMADAS ENTRE MÓDULOS
          </text>
        )}

        {data.dependencies.map((dep) => {
          const a = layout.pos.get(dep.source);
          const b = layout.pos.get(dep.target);
          if (!a || !b) return null;
          const inCycle = cyclePairs.has(`${dep.source}>${dep.target}`);
          const lit = focus !== null && (dep.source === focus || dep.target === focus);
          const forward = b.x > a.x;
          const x1 = forward ? a.x + NODE_W : a.x + NODE_W / 2;
          const y1 = forward ? a.y + NODE_H / 2 : a.y + NODE_H;
          const x2 = forward ? b.x : b.x + NODE_W / 2;
          const y2 = forward ? b.y + NODE_H / 2 : b.y + NODE_H;
          const d = forward
            ? `M${x1},${y1} C${x1 + COL_GAP / 2},${y1} ${x2 - COL_GAP / 2},${y2} ${x2},${y2}`
            : `M${x1},${y1} C${x1},${y1 + 40} ${x2},${y2 + 40} ${x2},${y2}`;
          const stroke = inCycle ? "var(--color-danger)" : lit ? "var(--color-accent-hover)" : "var(--color-line-strong)";
          return (
            <g key={`${dep.source}>${dep.target}`} style={{ color: stroke }} opacity={focus && !lit ? 0.25 : 1}>
              <path d={d} fill="none" stroke={stroke} strokeWidth={lit ? 1.5 : 1} strokeDasharray={inCycle ? "4 4" : undefined} markerEnd="url(#mm-arrow)" />
              <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 5} textAnchor="middle" fontSize="10" className="fill-subtle font-mono">
                {dep.calls}
              </text>
            </g>
          );
        })}

        {data.modules.map((module) => {
          const p = layout.pos.get(module.file);
          if (!p) return null;
          const isSelected = module.file === selected;
          const dim = focus !== null && !neighbors.has(module.file);
          const severity = module.worst_severity ? SEVERITY_VAR[module.worst_severity] : null;
          const label = `${module.file}: ${module.functions} funciones, ${module.findings} hallazgos${module.worst_severity ? `, peor severidad ${module.worst_severity}` : ""}`;
          return (
            <g
              key={module.file}
              transform={`translate(${p.x},${p.y})`}
              role="button"
              tabIndex={0}
              aria-label={label}
              aria-pressed={isSelected}
              opacity={dim ? 0.35 : 1}
              className="group cursor-pointer outline-none"
              onClick={() => onSelect(isSelected ? null : module.file)}
              onKeyDown={(event) => onKey(event, module.file)}
              onMouseEnter={() => setHover(module.file)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(module.file)}
              onBlur={() => setHover(null)}
            >
              <rect x="-4" y="-4" width={NODE_W + 8} height={NODE_H + 8} rx="12" fill="none" stroke="var(--color-focus)" strokeWidth="2" className="opacity-0 group-focus-visible:opacity-100" />
              <rect width={NODE_W} height={NODE_H} rx="8.57" fill="var(--color-canvas)" stroke={isSelected ? "var(--color-accent-hover)" : "var(--color-line-strong)"} strokeWidth={isSelected ? 1.5 : 1} />
              {severity && <rect x="0" y="10" width="2.5" height={NODE_H - 20} rx="1.25" fill={severity} />}
              <text x="14" y="22" fontSize="12" className="fill-fg font-mono">{module.file.length > 22 ? `…${module.file.slice(-21)}` : module.file}</text>
              <text x="14" y="40" fontSize="11" className="fill-subtle font-sans">
                {module.functions} fn{module.findings > 0 ? ` · ${module.findings} hallazgo${module.findings === 1 ? "" : "s"}` : ""}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
