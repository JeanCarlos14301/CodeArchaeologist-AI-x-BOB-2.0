import { useCallback, useEffect, useState } from "react";

/** Carga un recurso por jobId con estados de carga y error explícitos (nunca pantalla en blanco). */
export function useLoaded<T>(loader: (jobId: string) => Promise<T>, jobId: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    setData(null);
    setError(null);
    loader(jobId)
      .then((value) => !cancelled && setData(value))
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [jobId, loader, tick]);

  const retry = useCallback(() => setTick((value) => value + 1), []);
  return { data, error, retry, loading: !!jobId && !data && !error };
}
