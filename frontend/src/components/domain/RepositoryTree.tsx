import { useState } from "react";
import { ChevronRight, FileCode2, Folder } from "lucide-react";
import { SEVERITY } from "../../lib/severity";
import type { TreeNode } from "../../lib/tree";

interface Props {
  root: TreeNode;
  selected: string | null;
  onSelect: (path: string) => void;
}

/** Árbol del repositorio integrado con el análisis: severidad, hallazgos y funciones por archivo. */
export function RepositoryTree({ root, selected, onSelect }: Props) {
  return (
    <ul aria-label="Archivos del repositorio analizado" className="py-1 font-mono text-caption">
      {root.children.map((node) => (
        <TreeItem key={node.path} node={node} depth={0} selected={selected} onSelect={onSelect} />
      ))}
    </ul>
  );
}

function TreeItem({ node, depth, selected, onSelect }: { node: TreeNode; depth: number; selected: string | null; onSelect: (path: string) => void }) {
  const [open, setOpen] = useState(true);
  const isFile = !!node.file && node.children.length === 0;
  const isSelected = node.path === selected;
  const severity = node.worst ? SEVERITY[node.worst] : null;
  const indent = { paddingLeft: `${depth * 14 + 8}px` };

  if (!isFile) {
    return (
      <li>
        <button type="button" aria-expanded={open} onClick={() => setOpen((value) => !value)} style={indent} className="flex h-7 w-full items-center gap-1.5 pr-3 text-left text-fg-2 hover:bg-raised">
          <ChevronRight size={12} aria-hidden className={`shrink-0 text-subtle transition-transform duration-150 ${open ? "rotate-90" : ""}`} />
          <Folder size={13} aria-hidden className="shrink-0 text-subtle" />
          <span className="truncate">{node.name}</span>
          {node.findingCount > 0 && <span className="ml-auto text-subtle tabular-nums">{node.findingCount}</span>}
        </button>
        {open && (
          <ul>
            {node.children.map((child) => <TreeItem key={child.path} node={child} depth={depth + 1} selected={selected} onSelect={onSelect} />)}
          </ul>
        )}
      </li>
    );
  }

  const file = node.file!;
  return (
    <li>
      <button
        type="button"
        aria-current={isSelected ? "true" : undefined}
        onClick={() => onSelect(node.path)}
        style={indent}
        aria-label={`${node.path}${file.findings.length ? `, ${file.findings.length} hallazgos, peor severidad ${severity?.label}` : ""}, ${file.functions} funciones`}
        className={`relative flex h-7 w-full items-center gap-1.5 pr-3 text-left transition-[background-color] duration-150 hover:bg-raised ${isSelected ? "bg-raised text-fg" : "text-fg-2"}`}
      >
        {isSelected && <span aria-hidden className="absolute inset-y-1 left-0 w-0.5 rounded-pill bg-accent-hover" />}
        <span className="w-3 shrink-0" />
        <FileCode2 size={13} aria-hidden className="shrink-0 text-subtle" />
        <span className="truncate">{node.name}</span>
        <span className="ml-auto flex shrink-0 items-center gap-2">
          {file.functions > 0 && <span className="text-subtle tabular-nums" title={`${file.functions} funciones`}>{file.functions}ƒ</span>}
          {severity && (
            <span className={`${severity.text} tabular-nums`} title={`${file.findings.length} hallazgos · ${severity.label}`}>
              <span aria-hidden>{severity.glyph}</span> {file.findings.length}
            </span>
          )}
        </span>
      </button>
    </li>
  );
}
