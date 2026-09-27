import type { Finding, Severity } from "../types";

/** The system's severity scale (DESIGN.md §2.2). Glyph + label: never color alone. */
export const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

export const SEVERITY: Record<Severity, { label: string; glyph: string; text: string; bg: string; border: string }> = {
  critical: { label: "Critical", glyph: "◆", text: "text-risk-critical", bg: "bg-risk-critical", border: "border-risk-critical" },
  high: { label: "High", glyph: "▲", text: "text-risk-high", bg: "bg-risk-high", border: "border-risk-high" },
  medium: { label: "Medium", glyph: "●", text: "text-risk-medium", bg: "bg-risk-medium", border: "border-risk-medium" },
  low: { label: "Low", glyph: "○", text: "text-risk-low", bg: "bg-risk-low", border: "border-risk-low" },
  info: { label: "Info", glyph: "·", text: "text-risk-info", bg: "bg-risk-info", border: "border-risk-info" },
};

/** CSS variables for SVG (the graph cannot use Tailwind classes in attributes). */
export const SEVERITY_VAR: Record<Severity, string> = {
  critical: "var(--color-risk-critical)",
  high: "var(--color-risk-high)",
  medium: "var(--color-risk-medium)",
  low: "var(--color-risk-low)",
  info: "var(--color-risk-info)",
};

export function toSeverity(value: string | null | undefined): Severity {
  const lower = (value ?? "").toLowerCase();
  return (SEVERITY_ORDER as string[]).includes(lower) ? (lower as Severity) : "info";
}

export const bySeverity = (a: Finding, b: Finding) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity);

export function worstSeverity(values: Severity[]): Severity | null {
  return values.length ? [...values].sort((a, b) => SEVERITY_ORDER.indexOf(a) - SEVERITY_ORDER.indexOf(b))[0] : null;
}

export function countBySeverity(findings: Finding[]): Record<Severity, number> {
  const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  for (const finding of findings) counts[finding.severity] += 1;
  return counts;
}

export const CATEGORY_LABEL: Record<string, string> = {
  security: "Security",
  maintainability: "Maintainability",
  "business-rule": "Business rule",
  "data-integrity": "Data integrity",
  performance: "Performance",
  architecture: "Architecture",
  testing: "Testing",
};

export const categoryLabel = (category: string) => CATEGORY_LABEL[category] ?? category;
