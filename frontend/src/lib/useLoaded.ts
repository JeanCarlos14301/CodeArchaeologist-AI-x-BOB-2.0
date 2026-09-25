import { useCallback, useEffect, useState } from "react";
import type { Loaded } from "../api";

/** Carga un recurso por jobId con estados de carga y error explícitos (nunca pantalla en blanco). */
export function useLoaded<T>(loader: (jobId: string) => Promise<Loaded<T>>, jobId: string | null) {
  const [result, setResult] = useState<Loaded<T> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    setResult(null);
    setError(null);
    loader(jobId)
      .then((value) => !cancelled && setResult(value))
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [jobId, loader, tick]);

  const retry = useCallback(() => setTick((value) => value + 1), []);
  return { result, error, retry, loading: !!jobId && !result && !error };
}
