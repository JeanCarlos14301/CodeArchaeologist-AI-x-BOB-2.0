import { useCallback, useEffect, useState } from "react";

/**
 * Router por hash: el estado navegable vive en la URL (se puede compartir y el botón atrás funciona).
 *   #/                                   Proyectos
 *   #/p/<jobId>/<section>?f=F-1&file=app.py&line=78&node=<id>
 */
export const SECTIONS = ["overview", "session", "architecture", "repository", "dependencies", "risks", "modernization", "reports"] as const;
export type Section = (typeof SECTIONS)[number];

export interface Route {
  jobId: string | null;
  section: Section | null;
  finding: string | null;
  file: string | null;
  line: number | null;
  node: string | null;
  play: boolean;
}

const JOB_ID = /^[A-Za-z0-9_-]{1,64}$/;
const FINDING_ID = /^F-\d{1,4}$/;

export function parseHash(hash: string): Route {
  const [path, query = ""] = hash.replace(/^#/, "").split("?");
  const parts = path.split("/").filter(Boolean);
  const params = new URLSearchParams(query);
  const empty: Route = { jobId: null, section: null, finding: null, file: null, line: null, node: null, play: false };
  if (parts[0] !== "p" || !parts[1] || !JOB_ID.test(parts[1])) return empty;
  const section = (SECTIONS as readonly string[]).includes(parts[2]) ? (parts[2] as Section) : "overview";
  const finding = params.get("f");
  const line = Number(params.get("line"));
  return {
    jobId: parts[1],
    section,
    finding: finding && FINDING_ID.test(finding) ? finding : null,
    file: params.get("file")?.slice(0, 300) || null,
    line: Number.isInteger(line) && line > 0 ? line : null,
    node: params.get("node")?.slice(0, 300) || null,
    play: params.get("play") === "1",
  };
}

export function buildHash(route: Partial<Route>): string {
  if (!route.jobId) return "#/";
  const params = new URLSearchParams();
  if (route.finding) params.set("f", route.finding);
  if (route.file) params.set("file", route.file);
  if (route.line) params.set("line", String(route.line));
  if (route.node) params.set("node", route.node);
  if (route.play) params.set("play", "1");
  const query = params.toString();
  return `#/p/${route.jobId}/${route.section ?? "overview"}${query ? `?${query}` : ""}`;
}

export function useHashRoute(): [Route, (next: Partial<Route>) => void] {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash));

  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const navigate = useCallback((next: Partial<Route>) => {
    const hash = buildHash(next);
    if (hash !== window.location.hash) window.location.hash = hash;
    else setRoute(parseHash(hash));
  }, []);

  return [route, navigate];
}
