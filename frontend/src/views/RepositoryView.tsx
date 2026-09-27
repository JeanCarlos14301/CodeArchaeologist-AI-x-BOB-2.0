import { useEffect, useMemo, useState } from "react";
import { MessageSquareText } from "lucide-react";
import { api } from "../api";
import { CodeViewer, type CodeMark } from "../components/domain/CodeViewer";
import { RepositoryTree } from "../components/domain/RepositoryTree";
import { SeverityBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Eyebrow } from "../components/ui/Layout";
import { EmptyState, ErrorState, Loading } from "../components/ui/States";
import { lineRange } from "../lib/format";
import { bySeverity } from "../lib/severity";
import { buildTree, collectFiles } from "../lib/tree";
import { useResource, useWorkspace } from "../lib/workspace";
import type { Dossier, SourceExcerpt } from "../types";
import { JobGate } from "./JobGate";

const PAGE = 400; // backend: MAX_SOURCE_LINES

export function RepositoryView() {
  return <JobGate>{(dossier) => <Repository dossier={dossier} />}</JobGate>;
}

function Repository({ dossier }: { dossier: Dossier }) {
  const { route, go, token, seedComposer } = useWorkspace();
  const architecture = useResource("architecture");
  const files = useMemo(() => collectFiles(architecture.data, dossier), [architecture.data, dossier]);
  const tree = useMemo(() => buildTree(files), [files]);
  const fallback = files.find((f) => f.worst === "critical") ?? files.find((f) => f.findings.length) ?? files[0];
  const path = route.file ?? fallback?.path ?? null;

  const [excerpt, setExcerpt] = useState<SourceExcerpt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pageState, setPageState] = useState<{ path: string | null; start: number }>({ path, start: 1 });
  const page = pageState.path === path ? pageState.start : 1;
  const setPage = (start: number) => setPageState({ path, start });
  useEffect(() => {
    if (!path || !route.jobId) return;
    let cancelled = false;
    setError(null);
    setExcerpt(null);
    api.source(route.jobId, path, page, page + PAGE - 1, token)
      .then((data) => !cancelled && setExcerpt(data))
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [route.jobId, path, page, token]);

  const fileFindings = useMemo(
    () => dossier.findings.filter((f) => f.evidence.some((e) => e.path === path)).sort(bySeverity),
    [dossier.findings, path],
  );
  const marks: CodeMark[] = fileFindings.flatMap((f) =>
    f.evidence.filter((e) => e.path === path).map((e) => ({ start: e.line_start, end: e.line_end, severity: f.severity, label: `${f.id} · ${f.title}` })),
  );
  const openFile = (next: string) => go("repository", { file: next });
  const openFinding = (id: string, line: number) => go("repository", { file: path ?? undefined, line, finding: id });

  const findingsPanel = (
    <>
        <Eyebrow>Findings in this file · {fileFindings.length}</Eyebrow>
        {fileFindings.length === 0 ? (
          <p className="mt-2 text-body text-muted">Bob reported no findings with evidence in {path ?? "this file"}.</p>
        ) : (
          <ul className="mt-2 space-y-1">
            {fileFindings.map((finding) => {
              const evidence = finding.evidence.find((e) => e.path === path)!;
              const active = route.finding === finding.id;
              return (
                <li key={finding.id}>
                  <button type="button" onClick={() => openFinding(finding.id, evidence.line_start)} aria-current={active ? "true" : undefined}
                    className={`w-full rounded-inner px-2.5 py-2 text-left transition-[background-color] duration-150 hover:bg-raised ${active ? "bg-raised shadow-inset-accent" : ""}`}>
                    <span className="flex items-center justify-between gap-2">
                      <SeverityBadge severity={finding.severity} />
                      <span className="font-mono text-caption text-subtle">L{lineRange(evidence.line_start, evidence.line_end)}</span>
                    </span>
                    <span className="mt-1 block text-caption text-pretty text-fg">{finding.title}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {path && (
          <div className="mt-5 flex flex-col gap-2 border-t border-line pt-4">
            <Button size="sm" icon={<MessageSquareText size={14} aria-hidden />} onClick={() => seedComposer(`What does ${path} do, what depends on it and what risks does it have?`)}>
              Ask Bob about {path}
            </Button>
            {route.finding && <Button size="sm" variant="ghost" onClick={() => go("risks", { finding: route.finding })}>View {route.finding} in Risks</Button>}
          </div>
        )}
    </>
  );

  return (
    <div className="grid grid-cols-1 @2xl:h-full @2xl:min-h-0 @2xl:grid-cols-[240px_minmax(0,1fr)] @5xl:grid-cols-[240px_minmax(0,1fr)_300px]">
      <h1 className="sr-only">Repository{path ? ` · ${path}` : ""}</h1>
      <div className="border-b border-line @2xl:min-h-0 @2xl:overflow-y-auto @2xl:border-r @2xl:border-b-0">
        <div className="flex h-10 items-center border-b border-line px-3">
          <Eyebrow>Repository · {files.length} files</Eyebrow>
        </div>
        {architecture.loading && !architecture.data ? <p className="p-3 text-caption text-subtle">Loading files…</p> : <RepositoryTree root={tree} selected={path} onSelect={openFile} />}
        <p className="border-t border-line-subtle p-3 text-caption text-subtle">Files measured by AST and files cited as evidence are listed.</p>
      </div>

      <div className="p-4 @2xl:min-h-0 @2xl:overflow-y-auto">
        {!path ? (
          <EmptyState title="No files to show">This analysis found no Python files and no cited evidence.</EmptyState>
        ) : error ? (
          <ErrorState title={`${path} could not be read.`} message={error} hint="The file may not exist in this analysis's workspace." />
        ) : !excerpt ? (
          <Loading label={`Opening ${path}…`} />
        ) : (
          <>
            <CodeViewer
              path={path}
              lines={excerpt.lines}
              marks={marks}
              focusLine={route.line}
              maxHeight="calc(100dvh - 12rem)"
              caption={`lines ${lineRange(excerpt.start, excerpt.end)} of ${excerpt.total_lines}`}
              onMarkClick={(mark) => {
                const finding = fileFindings.find((f) => mark.label?.startsWith(f.id));
                if (finding) openFinding(finding.id, mark.start);
              }}
            />
            {excerpt.total_lines > PAGE && (
              <div className="mt-3 flex gap-2">
                <Button size="sm" disabled={page === 1} onClick={() => setPage(Math.max(1, page - PAGE))}>Previous lines</Button>
                <Button size="sm" disabled={excerpt.end >= excerpt.total_lines} onClick={() => setPage(page + PAGE)}>Next {PAGE} lines</Button>
              </div>
            )}
          </>
        )}
        <div className="mt-6 border-t border-line pt-4 @5xl:hidden">{findingsPanel}</div>
      </div>

      <aside aria-label="Findings in the file" className="hidden border-l border-line p-4 @5xl:block @5xl:min-h-0 @5xl:overflow-y-auto">
        {findingsPanel}
      </aside>
    </div>
  );
}
