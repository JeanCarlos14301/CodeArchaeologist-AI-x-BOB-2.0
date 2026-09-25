import { useState } from "react";
import type { BobStatus } from "../types";

interface Props {
  status: BobStatus | null;
  error: string | null;
}

function Check({ ok, label }: { ok: boolean; label: string }) {
  return (
    <li className="flex items-center gap-2 text-sm">
      <span
        aria-hidden
        className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-emerald-500" : "bg-rose-500"}`}
      />
      <span className={ok ? "text-stone-700" : "text-rose-700"}>{label}</span>
    </li>
  );
}

function AssetList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-stone-500">
        {title} · {items.length}
      </p>
      <div className="flex flex-wrap gap-1">
        {items.map((item) => (
          <span key={item} className="rounded bg-stone-100 px-1.5 py-0.5 font-mono text-[11px] text-stone-700">
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

export function BobStatusPanel({ status, error }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (error) return <p className="text-sm text-rose-700">{error}</p>;
  if (!status) return <p className="text-sm text-stone-500">Consultando Bob…</p>;

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold text-stone-800">IBM Bob</h2>
      <ul className="space-y-1">
        <Check ok={status.installed} label={status.installed ? `Bob Shell ${status.version ?? ""}` : "Bob Shell no instalado"} />
        <Check ok={status.api_key_configured} label={status.api_key_configured ? "API key configurada" : "Falta BOB_API_KEY"} />
        <Check ok={status.subagents.length > 0} label={`${status.custom_modes.length} modos · ${status.subagents.length} subagentes · ${status.skills.length} skills`} />
      </ul>
      <p className="text-xs text-stone-500">
        Límite por auditoría live: {status.max_cost_per_run} bobcoins · {Math.round(status.timeout_s / 60)} min
      </p>
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        className="text-xs font-medium text-stone-600 underline-offset-2 hover:underline"
      >
        {expanded ? "Ocultar activos de Bob" : "Ver activos de Bob"}
      </button>
      {expanded && (
        <div className="space-y-3">
          <AssetList title="Modos" items={status.custom_modes} />
          <AssetList title="Subagentes" items={status.subagents} />
          <AssetList title="Skills" items={status.skills} />
        </div>
      )}
    </section>
  );
}
