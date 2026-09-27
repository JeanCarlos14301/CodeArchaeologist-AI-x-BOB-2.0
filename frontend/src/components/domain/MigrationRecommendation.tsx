import type { Finding, MigrationRecommendation, RouteCandidate } from "../../types";
import { formatDecimal } from "../../lib/format";
import { SEVERITY } from "../../lib/severity";
import { Eyebrow } from "../ui/Layout";

interface Props {
  recommendation: MigrationRecommendation;
  findings: Finding[];
  onOpenFinding: (id: string) => void;
}

const TESTABILITY_LABEL: Record<string, string> = { "1": "JSON", "0.5": "view", "0.25": "write" };

/**
 * Deterministic route ranking (backend/app/pipeline/migration_ranking.py): recommended cut, alternatives,
 * route to avoid and waves with their PERT. Code computes everything on the call graph; Bob does not pick the cut.
 */
export function MigrationRecommendationView({ recommendation, findings, onOpenFinding }: Props) {
  const { recommended, alternatives, do_not_start_here: avoid, waves, candidates } = recommendation;
  if (!recommended) return null;
  const byId = new Map(findings.map((finding) => [finding.id, finding]));
  const showAvoid = !!avoid && avoid.endpoint !== recommended.endpoint;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 gap-x-10 gap-y-4 @4xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <div>
          <Eyebrow><span className="text-verified"><span aria-hidden>✓ </span>Recommended cut</span></Eyebrow>
          <h3 className="mt-1 font-mono text-title break-all text-fg">{recommended.endpoint}</h3>
          <p className="mt-1 font-mono text-caption text-subtle">
            {recommended.function_name} · {recommended.file_path}:{recommended.line_start}-{recommended.line_end}
          </p>
          <p className="mt-3 text-body text-pretty text-fg-2">{recommended.why}</p>
          {recommended.findings_mitigated.length > 0 && (
            <>
              <p className="mt-3 text-micro tracking-eyebrow text-subtle uppercase">Mitigates</p>
              <ul className="mt-1 flex flex-wrap gap-1.5">
                {recommended.findings_mitigated.map((id) => {
                  const finding = byId.get(id);
                  const info = finding ? SEVERITY[finding.severity] : null;
                  return (
                    <li key={id}>
                      <button
                        type="button"
                        onClick={() => onOpenFinding(id)}
                        title={finding?.title}
                        className="inline-flex h-5.5 items-center gap-1.5 rounded-pill border border-line px-2.5 font-mono text-caption text-fg-2 transition-[background-color] duration-150 ease-out hover:bg-raised"
                      >
                        {info && <span aria-hidden className={info.text}>{info.glyph}</span>}
                        {id}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </div>
        <div className="space-y-3">
          <Eyebrow>How it was computed</Eyebrow>
          <p className="font-mono text-caption text-pretty text-fg-2">{recommended.formula}</p>
          <p className="text-caption text-subtle">
            Score = value × testability × business data / risk. Value adds up the findings the cut
            mitigates; risk adds shared functions, written tables, complexity, lines and circular dependencies.
            A route that reads and writes no business data is weighted by half.
          </p>
          {recommendation.reference_comparison && (
            <p className="border-l-2 border-verified pl-3 text-caption text-pretty text-fg-2">{recommendation.reference_comparison}</p>
          )}
        </div>
      </div>

      <div>
        <Eyebrow>Alternatives and route to avoid</Eyebrow>
        <ul className="mt-2 divide-y divide-line-subtle border-y border-line-subtle">
          {alternatives.map((candidate) => (
            <CandidateRow key={candidate.endpoint} label="Alternative" glyph="○" tone="text-fg-2" candidate={candidate} />
          ))}
          {showAvoid && avoid && <CandidateRow label="Do not start here" glyph="✗" tone="text-danger" candidate={avoid} />}
        </ul>
      </div>

      {waves.length > 0 && (
        <div>
          <Eyebrow>Roadmap by waves</Eyebrow>
          <ol className="mt-2 grid grid-cols-1 gap-x-8 gap-y-5 @3xl:grid-cols-3">
            {waves.map((wave) => (
              <li key={wave.wave_number} className="border-t border-line pt-3">
                <p className="font-display text-body text-fg">{wave.name}</p>
                <p className="mt-1 text-caption text-pretty text-subtle">{wave.description}</p>
                <ul className="mt-2 space-y-0.5">
                  {wave.candidates.length === 0 && <li className="text-caption text-subtle">No routes in this wave.</li>}
                  {wave.candidates.map((candidate) => (
                    <li key={candidate.endpoint} className="truncate font-mono text-caption text-fg-2" title={candidate.endpoint}>{candidate.endpoint}</li>
                  ))}
                </ul>
                {wave.pert && (
                  <p className="mt-2 font-mono text-caption text-fg-2 tabular-nums">
                    E {formatDecimal(wave.pert.expected_days)} d <span className="text-subtle">· {formatDecimal(wave.pert.optimistic_days)}–{formatDecimal(wave.pert.pessimistic_days)} d</span>
                  </p>
                )}
              </li>
            ))}
          </ol>
          <p className="mt-3 text-caption text-subtle">PERT effort per wave computed on the code (uncalibrated heuristic; the assumptions are in the first-cut estimate).</p>
        </div>
      )}

      {candidates.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer text-caption text-fg-2 hover:text-fg">View the full ranking ({candidates.length} routes)</summary>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[34rem] text-left text-caption">
              <thead className="text-micro tracking-eyebrow text-subtle uppercase">
                <tr className="border-b border-line-subtle">
                  <th scope="col" className="py-1.5 pr-3 font-normal">Endpoint</th>
                  <th scope="col" className="py-1.5 pr-3 text-right font-normal">Value</th>
                  <th scope="col" className="py-1.5 pr-3 text-right font-normal">Testability</th>
                  <th scope="col" className="py-1.5 pr-3 text-right font-normal">Data</th>
                  <th scope="col" className="py-1.5 pr-3 text-right font-normal">Risk</th>
                  <th scope="col" className="py-1.5 text-right font-normal">Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-subtle tabular-nums">
                {candidates.map((candidate) => (
                  <tr key={candidate.endpoint} className={candidate.endpoint === recommended.endpoint ? "bg-raised" : ""}>
                    <td className="max-w-[18rem] truncate py-1.5 pr-3 font-mono text-fg-2" title={candidate.endpoint}>{candidate.endpoint}</td>
                    <td className="py-1.5 pr-3 text-right font-mono text-fg-2">{formatDecimal(candidate.value)}</td>
                    <td className="py-1.5 pr-3 text-right font-mono text-fg-2">{TESTABILITY_LABEL[String(candidate.testability)] ?? formatDecimal(candidate.testability)}</td>
                    <td className="py-1.5 pr-3 text-right font-mono text-fg-2">{candidate.touches_business_data === false ? "no" : candidate.touches_business_data ? "yes" : "—"}</td>
                    <td className="py-1.5 pr-3 text-right font-mono text-fg-2">{formatDecimal(candidate.risk)}</td>
                    <td className="py-1.5 text-right font-mono text-fg">{formatDecimal(candidate.score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}

function CandidateRow({ label, glyph, tone, candidate }: { label: string; glyph: string; tone: string; candidate: RouteCandidate }) {
  return (
    <li className="grid grid-cols-1 gap-x-6 gap-y-1 py-3 @2xl:grid-cols-[11rem_minmax(0,1fr)_auto]">
      <span className={`text-caption ${tone}`}><span aria-hidden>{glyph} </span>{label}</span>
      <span className="min-w-0">
        <span className="block truncate font-mono text-caption text-fg" title={candidate.endpoint}>{candidate.endpoint}</span>
        <span className="block text-caption text-pretty text-subtle">{candidate.why}</span>
      </span>
      <span className="font-mono text-caption text-fg-2 tabular-nums">score {formatDecimal(candidate.score)}</span>
    </li>
  );
}
