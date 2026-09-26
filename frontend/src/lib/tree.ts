import type { ArchitectureData, Dossier, Severity } from "../types";
import { worstSeverity } from "./severity";

export interface FileInfo {
  path: string;
  functions: number;
  findings: string[];
  worst: Severity | null;
}

export interface TreeNode {
  name: string;
  path: string;
  children: TreeNode[];
  file: FileInfo | null;
  worst: Severity | null;
  findingCount: number;
}

/** Archivos conocidos del análisis: módulos medidos por AST + archivos citados como evidencia. */
export function collectFiles(architecture: ArchitectureData | null, dossier: Dossier | null): FileInfo[] {
  const files = new Map<string, FileInfo>();
  const ensure = (path: string) => {
    const existing = files.get(path);
    if (existing) return existing;
    const created: FileInfo = { path, functions: 0, findings: [], worst: null };
    files.set(path, created);
    return created;
  };
  for (const module of architecture?.modules ?? []) ensure(module.file).functions = module.functions;
  const severities = new Map<string, Severity[]>();
  for (const finding of dossier?.findings ?? []) {
    for (const path of new Set(finding.evidence.map((evidence) => evidence.path))) {
      ensure(path).findings.push(finding.id);
      severities.set(path, [...(severities.get(path) ?? []), finding.severity]);
    }
  }
  for (const [path, list] of severities) ensure(path).worst = worstSeverity(list);
  return [...files.values()].sort((a, b) => a.path.localeCompare(b.path));
}

export function buildTree(files: FileInfo[]): TreeNode {
  const root: TreeNode = { name: "", path: "", children: [], file: null, worst: null, findingCount: 0 };
  for (const file of files) {
    const parts = file.path.split("/");
    let node = root;
    parts.forEach((part, index) => {
      const path = parts.slice(0, index + 1).join("/");
      let child = node.children.find((item) => item.name === part);
      if (!child) {
        child = { name: part, path, children: [], file: null, worst: null, findingCount: 0 };
        node.children.push(child);
      }
      if (index === parts.length - 1) child.file = file;
      node = child;
    });
  }
  const finalize = (node: TreeNode): TreeNode => {
    const children = node.children.map(finalize).sort((a, b) => Number(!!a.file) - Number(!!b.file) || a.name.localeCompare(b.name));
    const severities = [node.file?.worst, ...children.map((child) => child.worst)].filter((s): s is Severity => !!s);
    const findingCount = (node.file?.findings.length ?? 0) + children.reduce((sum, child) => sum + child.findingCount, 0);
    return { ...node, children, worst: worstSeverity(severities), findingCount };
  };
  return finalize(root);
}
