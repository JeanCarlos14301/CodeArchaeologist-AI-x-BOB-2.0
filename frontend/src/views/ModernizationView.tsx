import { useState } from "react";
import { MessageSquareText } from "lucide-react";
import { CodeViewer, toLines } from "../components/domain/CodeViewer";
import { MigrationOptions } from "../components/domain/MigrationOptions";
import { MigrationSequence } from "../components/domain/MigrationSequence";
import { PertRange } from "../components/domain/PertRange";
import { Button } from "../components/ui/Button";
import { Eyebrow, Meter, ScreenHeader, Section, Segmented } from "../components/ui/Layout";
import { EmptyState, ErrorState, Loading } from "../components/ui/States";
import { importedFramework } from "../lib/stack";
import { useResource, useWorkspace } from "../lib/workspace";
import type { Dossier, MigrationViewData } from "../types";
import { StudioGate } from "./JobGate";
import { StudioView } from "./StudioView";

type Tab = "studio" | "cut";

export function ModernizationView() {
  return <StudioGate>{() => <ModernizationTabs />}</StudioGate>;
}

/** Estudio (cualquier proyecto) y, si hubo auditoría, el primer corte y las opciones que salieron de ella. */
function ModernizationTabs() {
  const { dossier } = useWorkspace();
  const [tab, setTab] = useState<Tab>("studio");
  if (dossier && tab === "cut") {
    return (
      <>
        <div className="px-6 pt-5 @3xl:px-10"><TabSwitch tab={tab} onChange={setTab} /></div>
        <Modernization dossier={dossier} />
      </>
    );
  }
  return (
    <div className="px-6 py-6 @3xl:px-10">
      <ScreenHeader
        eyebrow="Modernización · ¿Cómo migrar con seguridad?"
        title="Estudio de modernización"
        description="Mide qué tecnologías usa tu proyecto, elige a dónde migrar (o deja que Bob lo recomiende), entiende qué se gana y qué se sacrifica, y pide a Bob un plan y su implementación."
        actions={dossier ? <TabSwitch tab={tab} onChange={setTab} /> : undefined}
      />
      <StudioView />
    </div>
  );
}

function TabSwitch({ tab, onChange }: { tab: Tab; onChange: (tab: Tab) => void }) {
  return (
    <Segmented<Tab>
      label="Vista de modernización"
      value={tab}
      onChange={onChange}
      options={[{ value: "studio", label: "Estudio" }, { value: "cut", label: "Primer corte de la auditoría" }]}
    />
  );
}

function Modernization({ dossier }: { dossier: Dossier }) {
  const { seedComposer, go } = useWorkspace();
  const options = dossier.migration_options ?? [];
  const hasMigration = !!dossier.migration;

  return (
    <div className="px-6 py-6 @3xl:px-10">
      <ScreenHeader
        eyebrow="Modernización · ¿Cómo migrar con seguridad?"
        title={dossier.migration ? `Primer corte: ${dossier.migration.endpoint}` : "Plan de modernización"}
        description="Strangler Fig: se extrae un endpoint cada vez detrás de una fachada, con pruebas que fijan el comportamiento del legado y deben pasar igual en el código nuevo."
        actions={<Button icon={<MessageSquareText size={14} aria-hidden />} onClick={() => seedComposer("¿Qué debería migrar después del primer corte y en qué orden? Justifica con el código.")}>Preguntar a Bob el siguiente corte</Button>}
      />
      <Section eyebrow="Opciones" title="Cómo podría migrarse">
        {options.length > 0 ? (
          <>
            <MigrationOptions options={options} findings={dossier.findings} onOpenFinding={(id) => go("risks", { finding: id })} />
            <p className="mt-3 text-caption text-subtle">
              Propuestas de Bob sobre el ranking de riesgo. El código comprobó que cada hallazgo citado existe y que no traen cifras:
              los días y el riesgo salen del ranking y de la estimación PERT, no de Bob.
            </p>
          </>
        ) : (
          <EmptyState title="Este análisis no incluye opciones de migración.">
            Bob las propone solo en análisis live y se descartan si su respuesta cita hallazgos que no existen o trae cifras.
            En análisis importados no se le consulta.
          </EmptyState>
        )}
      </Section>
      {hasMigration ? <MigrationDetail /> : (
        <Section>
          <EmptyState title="Este análisis no incluye un primer corte probado.">
            Por seguridad, el código subido nunca se ejecuta, así que no se corren pruebas de caracterización sobre él.
            El corte probado existe para las muestras registradas; abajo tienes la estimación del esfuerzo si el pipeline la calculó.
          </EmptyState>
        </Section>
      )}
      {dossier.first_cut_pert && (
        <Section eyebrow="Esfuerzo" title="Estimación PERT del primer corte">
          <div className="grid gap-x-12 gap-y-6 @4xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
            <PertRange pert={dossier.first_cut_pert} />
            <div>
              <Eyebrow>Medido sobre el código</Eyebrow>
              <p className="mt-1.5 font-mono text-caption text-fg-2">
                {dossier.first_cut_pert.affected_routes} rutas · {dossier.first_cut_pert.affected_functions} funciones · {dossier.first_cut_pert.affected_lines} líneas · complejidad {dossier.first_cut_pert.affected_complexity}
              </p>
              <Eyebrow className="mt-4">Supuestos</Eyebrow>
              <ul className="mt-1.5 list-disc space-y-1 pl-4 text-caption text-muted">
                {dossier.first_cut_pert.assumptions.map((a) => <li key={a}>{a}</li>)}
              </ul>
            </div>
          </div>
        </Section>
      )}
    </div>
  );
}

function MigrationDetail() {
  const migration = useResource("migration");
  if (migration.error) return <Section><ErrorState title="No se pudo cargar el primer corte." message={migration.error} onRetry={migration.retry} /></Section>;
  if (!migration.data) return <Section><Loading label="Cargando el primer corte…" /></Section>;
  const data = migration.data;
  const result = data.result;
  const legacy = importedFramework(data.legacy_code);
  const modern = importedFramework(data.modern_code);
  const count = (target: "legacy" | "modern", status: string) => result.tests.filter((t) => t.target === target && t.status === status).length;
  const total = (target: "legacy" | "modern") => result.tests.filter((t) => t.target === target).length;

  return (
    <>
      <Section eyebrow="Transformación" title="Actual → objetivo">
        <div className="grid items-stretch gap-3 @2xl:grid-cols-[1fr_auto_1fr]">
          <Endpoint tag="ACTUAL" framework={legacy} file={result.legacy_file} note="Monolito legado, sigue sirviendo el resto de rutas" />
          <div className="flex items-center justify-center font-mono text-caption text-subtle" aria-hidden>→ fachada →</div>
          <Endpoint tag="OBJETIVO" framework={modern} file={result.modern_file} note={result.implementation_origin} />
        </div>
        <p className="mt-3 text-caption text-subtle">Framework detectado en los imports de cada archivo · fachada: <span className="font-mono text-fg-2">{result.facade_file ?? "—"}</span></p>
      </Section>
      <div className="grid gap-x-12 @4xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <Section eyebrow="Secuencia" title="Pasos y dependencias">
          <MigrationSequence result={result} />
        </Section>
        <Section eyebrow="Validación" title="Pruebas de caracterización">
          <div className="space-y-5">
            <Meter label="Contra el legado" value={count("legacy", "passed")} max={total("legacy")} tone="bg-verified" />
            <Meter label="Contra el corte moderno" value={count("modern", "passed")} max={total("modern")} tone="bg-verified" />
          </div>
          <ul className="mt-5 divide-y divide-line-subtle border-t border-line-subtle">
            {result.tests.map((test, i) => (
              <li key={`${test.target}-${test.name}-${i}`} className="grid grid-cols-[4.5rem_1fr_auto] items-baseline gap-3 py-2 text-caption">
                <span className="font-mono text-subtle">{test.target === "legacy" ? "legado" : "moderno"}</span>
                <span className="truncate font-mono text-fg-2" title={test.name}>{test.name}{test.reason && <span className="block text-danger">{test.reason}</span>}</span>
                <span className={test.status === "passed" ? "text-verified" : test.status === "failed" ? "text-danger" : "text-subtle"}>
                  {test.status === "passed" ? "✓ pasó" : test.status === "failed" ? "✗ falló" : "○ sin ejecutar"} <span className="font-mono text-subtle tabular-nums">{Math.round(test.duration_ms)} ms</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-caption text-subtle">Que las pruebas pasen no demuestra que el cambio sea seguro: confirma que el comportamiento observado del endpoint es el mismo.</p>
        </Section>
      </div>
      <CodeComparison data={data} />
    </>
  );
}

function Endpoint({ tag, framework, file, note }: { tag: string; framework: string | null; file: string | null; note: string }) {
  return (
    <div className="rounded-panel border border-line bg-surface px-4 py-3">
      <Eyebrow>{tag}</Eyebrow>
      <p className="mt-1 font-display text-title text-fg">{framework ?? "Framework no detectado"}</p>
      <p className="mt-0.5 font-mono text-caption text-fg-2">{file ?? "—"}</p>
      <p className="mt-1.5 text-caption text-subtle">{note}</p>
    </div>
  );
}

type CodeTab = "legacy" | "modern" | "facade";

function CodeComparison({ data }: { data: MigrationViewData }) {
  const [tab, setTab] = useState<CodeTab>("modern");
  const code = { legacy: data.legacy_code, modern: data.modern_code, facade: data.facade_code }[tab];
  const file = { legacy: data.result.legacy_file, modern: data.result.modern_file, facade: data.result.facade_file }[tab];
  return (
    <Section eyebrow="Código" title="Legado, corte moderno y fachada" aside={
      <Segmented<CodeTab> label="Archivo" value={tab} onChange={setTab} options={[
        { value: "legacy", label: "Legado", disabled: !data.legacy_code },
        { value: "modern", label: "Moderno", disabled: !data.modern_code },
        { value: "facade", label: "Fachada", disabled: !data.facade_code },
      ]} />
    }>
      {code ? <CodeViewer path={file ?? tab} lines={toLines(code)} maxHeight="32rem" caption={`${code.split("\n").length} líneas`} /> : <p className="text-body text-muted">Archivo no disponible.</p>}
    </Section>
  );
}
