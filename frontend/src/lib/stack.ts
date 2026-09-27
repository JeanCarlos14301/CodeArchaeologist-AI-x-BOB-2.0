import type { ArchitectureData } from "../types";

/** Dependency declared in requirements.txt. Only what the file says: PyPI is never queried. */
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

/** Stack detected from measured facts: AST, routes, SQL and requirements.txt. */
export function detectStack(architecture: ArchitectureData | null, packages: DeclaredPackage[]): DetectedStack {
  const frameworks = packages.map((pkg) => FRAMEWORKS[pkg.name.toLowerCase()]).filter((name): name is string => !!name);
  if (architecture && architecture.routes.length > 0 && !frameworks.includes("Flask") && !frameworks.includes("FastAPI")) {
    frameworks.push("HTTP routes");
  }
  const tables = architecture?.tables.length ?? 0;
  return {
    language: architecture && architecture.totals.functions > 0 ? "Python" : null,
    frameworks: [...new Set(frameworks)],
    data: architecture && (tables > 0 || architecture.sql.total > 0)
      ? `SQL · ${tables} ${tables === 1 ? "table" : "tables"}`
      : null,
  };
}

/** Framework imported in a code file (literal detection, not inferred). */
export function importedFramework(code: string | null): string | null {
  if (!code) return null;
  if (/^\s*(from|import)\s+fastapi\b/m.test(code)) return "FastAPI";
  if (/^\s*(from|import)\s+flask\b/m.test(code)) return "Flask";
  if (/^\s*(from|import)\s+django\b/m.test(code)) return "Django";
  return null;
}
