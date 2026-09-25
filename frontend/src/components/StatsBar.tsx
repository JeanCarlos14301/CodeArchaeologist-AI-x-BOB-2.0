import type { Dossier } from "../types";

const MODE_LABEL: Record<Dossier["execution_mode"], string> = {
  live: "LIVE",
  imported: "IMPORTADO",
  example: "EJEMPLO",
};

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-stone-200 bg-white px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-stone-500">{label}</p>
      <p className="text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}

export function StatsBar({ dossier }: { dossier: Dossier }) {
  const { stats } = dossier;
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="rounded bg-stone-900 px-2 py-0.5 font-mono text-xs font-semibold text-white">
          {MODE_LABEL[dossier.execution_mode]}
        </span>
        <span className="font-medium">{dossier.repo_name}</span>
        <span className="text-stone-500">· {new Date(dossier.generated_at).toLocaleString()}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Hallazgos validados" value={`${stats.findings_validated}/${stats.findings_reported}`} />
        <Stat label="Evidencias válidas" value={`${stats.evidence_valid}/${stats.evidence_total} (${Math.round(stats.evidence_valid_ratio * 100)}%)`} />
        <Stat label="Coste Bob" value={stats.bob_cost === null ? "—" : `${stats.bob_cost.toFixed(2)} bc`} />
        <Stat label="Duración Bob" value={stats.bob_duration_ms === null ? "—" : `${Math.round(stats.bob_duration_ms / 1000)} s`} />
      </div>
      <p className="text-xs text-stone-500">Todas las cifras las calcula el pipeline en Python, no la IA.</p>
    </div>
  );
}
