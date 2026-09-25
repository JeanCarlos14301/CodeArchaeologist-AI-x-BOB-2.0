/** Estimación PERT clásica: (O + 4M + P) / 6. Calculada por código, nunca por la IA. */
export function pertExpected(o: number, m: number, p: number): number {
  return (o + 4 * m + p) / 6;
}

export function pertStdDev(o: number, p: number): number {
  return (p - o) / 6;
}
