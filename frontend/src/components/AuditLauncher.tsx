import { useState } from "react";
import type { ExecutionMode, SampleInfo } from "../types";

interface Props {
  samples: SampleInfo[];
  busy: boolean;
  liveRequiresToken: boolean;
  onStart: (sample: string, mode: ExecutionMode, liveToken: string) => void;
}

const MODES: { value: ExecutionMode; label: string; hint: string }[] = [
  { value: "live", label: "Live", hint: "Bob audita en vivo (≈1–2 min, consume bobcoins)" },
  { value: "imported", label: "Importado", hint: "Reutiliza una respuesta real de Bob ya guardada" },
  { value: "example", label: "Ejemplo", hint: "Expediente de ejemplo, instantáneo" },
];

export function AuditLauncher({ samples, busy, liveRequiresToken, onStart }: Props) {
  const [sample, setSample] = useState<string>("");
  const [mode, setMode] = useState<ExecutionMode>("imported");
  const [liveToken, setLiveToken] = useState<string>("");
  const selectedSample = sample || samples[0]?.id || "";
  const needsToken = mode === "live" && liveRequiresToken;

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (selectedSample) onStart(selectedSample, mode, liveToken);
      }}
    >
      <h2 className="text-sm font-semibold text-stone-800">Nueva auditoría</h2>
      <label className="block text-sm">
        <span className="mb-1 block text-stone-600">Repositorio</span>
        <select
          value={selectedSample}
          onChange={(event) => setSample(event.target.value)}
          className="w-full rounded-md border border-stone-300 bg-white px-2 py-1.5 text-sm"
        >
          {samples.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      <fieldset className="space-y-1.5">
        <legend className="mb-1 text-sm text-stone-600">Modo de ejecución</legend>
        {MODES.map((option) => (
          <label key={option.value} className="flex cursor-pointer items-start gap-2 text-sm">
            <input
              type="radio"
              name="mode"
              value={option.value}
              checked={mode === option.value}
              onChange={() => setMode(option.value)}
              className="mt-1"
            />
            <span>
              <span className="font-medium">{option.label}</span>
              <span className="block text-xs text-stone-500">{option.hint}</span>
            </span>
          </label>
        ))}
      </fieldset>
      {needsToken && (
        <label className="block text-sm">
          <span className="mb-1 block text-stone-600">Token de acceso a live</span>
          <input
            type="password"
            value={liveToken}
            onChange={(event) => setLiveToken(event.target.value)}
            autoComplete="off"
            className="w-full rounded-md border border-stone-300 bg-white px-2 py-1.5 text-sm"
          />
          <span className="mt-1 block text-xs text-stone-500">
            En la demo pública, live gasta bobcoins del equipo y pide token. Importado y Ejemplo no lo piden.
          </span>
        </label>
      )}
      <button
        type="submit"
        disabled={busy || !selectedSample || (needsToken && !liveToken)}
        className="w-full rounded-md bg-stone-900 px-3 py-2 text-sm font-medium text-white hover:bg-stone-700 disabled:cursor-not-allowed disabled:bg-stone-400"
      >
        {busy ? "Auditoría en curso…" : "Auditar"}
      </button>
    </form>
  );
}
