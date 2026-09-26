import type { ArchitectureData } from "../types";

/** Dependencia declarada en requirements.txt. Solo lo que dice el archivo: no se consulta PyPI. */
export interface DeclaredPackage {
  name: string;
  spec: string | null;
  pinned: boolean;
  line: number;
}

const REQUIREMENT = /^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*((?:==|>=|<=|~=|!=|>|<)[^;#\s]+(?:\s*,\s*(?:==|>=|<=|~=|!=|>|<)[^;#\s]+)*)?/;

export function parseRequirements(lines: { number: number; text: string }[]): DeclaredPackage[] {
  const packages: DeclaredPackage[] = [];
  for (const { number, text } of lines) {
    const clean = text.split("#")[0].trim();
    if (!clean || clean.startsWith("-")) continue;
    const match = REQUIREMENT.exec(clean);
    if (!match) continue;
    const spec = match[3]?.replace(/\s+/g, "") ?? null;
    packages.push({ name: match[1], spec, pinned: !!spec && spec.startsWith("==") && !spec.includes(","), line: number });
  }
  return packages;
}

const FRAMEWORKS: Record<string, string> = {
  flask: "Flask",
  fastapi: "FastAPI",
  django: "Django",
  sqlalchemy: "SQLAlchemy",
  werkzeug: "Werkzeug",
  pydantic: "Pydantic",
  jinja2: "Jinja2",
};

export interface DetectedStack {
  language: string | null;
  frameworks: string[];
  data: string | null;
}

/** Stack detectado a partir de hechos medidos: AST, rutas, SQL y requirements.txt. */
export function detectStack(architecture: ArchitectureData | null, packages: DeclaredPackage[]): DetectedStack {
  const frameworks = packages.map((pkg) => FRAMEWORKS[pkg.name.toLowerCase()]).filter((name): name is string => !!name);
  if (architecture && architecture.routes.length > 0 && !frameworks.includes("Flask") && !frameworks.includes("FastAPI")) {
    frameworks.push("Rutas HTTP");
  }
  const tables = architecture?.tables.length ?? 0;
  return {
    language: architecture && architecture.totals.functions > 0 ? "Python" : null,
    frameworks: [...new Set(frameworks)],
    data: architecture && (tables > 0 || architecture.sql.total > 0)
      ? `SQL · ${tables} ${tables === 1 ? "tabla" : "tablas"}`
      : null,
  };
}

/** Framework importado en un archivo de código (detección literal, no inferida). */
export function importedFramework(code: string | null): string | null {
  if (!code) return null;
  if (/^\s*(from|import)\s+fastapi\b/m.test(code)) return "FastAPI";
  if (/^\s*(from|import)\s+flask\b/m.test(code)) return "Flask";
  if (/^\s*(from|import)\s+django\b/m.test(code)) return "Django";
  return null;
}
