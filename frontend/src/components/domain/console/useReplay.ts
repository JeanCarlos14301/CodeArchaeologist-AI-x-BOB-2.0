import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import type { PipelineEvent } from "../../../types";

/** Duración objetivo de una reproducción: la sesión real se comprime a este tiempo. */
const REPLAY_SECONDS = 26;
const TICK_MS = 80;
const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

function subscribeReducedMotion(onChange: () => void): () => void {
  const query = window.matchMedia?.(REDUCED_MOTION);
  query?.addEventListener("change", onChange);
  return () => query?.removeEventListener("change", onChange);
}

const prefersReducedMotion = (): boolean => window.matchMedia?.(REDUCED_MOTION).matches ?? false;

export interface Replay {
  visible: PipelineEvent[];
  /** Segundos de sesión mostrados; null = todo (en vivo o reproducción terminada). */
  playhead: number | null;
  playing: boolean;
  progress: number;
  duration: number;
  /** false con movimiento reducido: la reproducción es una animación y se muestra la sesión completa. */
  available: boolean;
  start: () => void;
  stop: () => void;
}

/** Reproduce una sesión terminada respetando el ritmo real de los eventos (acelerado). */
export function useReplay(events: PipelineEvent[], autoplay: boolean): Replay {
  const duration = useMemo(() => events.reduce((max, event) => Math.max(max, event.t), 0), [events]);
  const reducedMotion = useSyncExternalStore(subscribeReducedMotion, prefersReducedMotion, () => false);
  const [cursor, setCursor] = useState<number | null>(null);
  const autoplayed = useRef(false);
  // Derivado en el render (no en un efecto): con movimiento reducido nunca se pinta una sesión a medias.
  const playhead = reducedMotion ? null : cursor;
  const playing = playhead !== null;

  const start = useCallback(() => setCursor(0), []);
  const stop = useCallback(() => setCursor(null), []);

  useEffect(() => {
    if (autoplay && !autoplayed.current && events.length > 0) {
      autoplayed.current = true;
      start();
    }
  }, [autoplay, events.length, start]);

  useEffect(() => {
    if (!playing) return;
    const step = Math.max(duration / REPLAY_SECONDS, 0.5) * (TICK_MS / 1000);
    const timer = window.setInterval(() => {
      setCursor((current) => {
        if (current === null) return null;
        const next = current + step;
        return next >= duration ? null : next;
      });
    }, TICK_MS);
    return () => window.clearInterval(timer);
  }, [playing, duration]);

  const visible = useMemo(
    () => (playhead === null ? events : events.filter((event) => event.t <= playhead)),
    [events, playhead],
  );

  return {
    visible,
    playhead,
    playing,
    progress: playhead === null || duration === 0 ? 1 : playhead / duration,
    duration,
    available: !reducedMotion,
    start,
    stop,
  };
}
