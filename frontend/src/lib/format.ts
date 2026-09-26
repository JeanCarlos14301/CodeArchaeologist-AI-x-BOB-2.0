const DATE = new Intl.DateTimeFormat("es", { dateStyle: "medium", timeStyle: "short" });
const PERCENT = new Intl.NumberFormat("es", { style: "percent", maximumFractionDigits: 0 });
const DECIMAL = new Intl.NumberFormat("es", { maximumFractionDigits: 1 });

export const formatDate = (iso: string) => {
  const time = Date.parse(iso);
  return Number.isNaN(time) ? iso : DATE.format(time);
};

export const formatPercent = (ratio: number) => PERCENT.format(ratio);
export const formatDecimal = (value: number) => DECIMAL.format(value);

export const formatSeconds = (ms: number | null | undefined) => (ms == null ? "—" : `${Math.round(ms / 1000)} s`);
export const formatCost = (cost: number | null | undefined) => (cost == null ? "—" : `${cost.toFixed(2)} bc`);

export const plural = (count: number, one: string, many: string) => `${count} ${count === 1 ? one : many}`;

export const lineRange = (start: number, end: number) => (end !== start ? `${start}–${end}` : `${start}`);

/** Etiqueta legible de un job: las subidas llevan el prefijo `upload:`. */
export const jobLabel = (sample: string) => sample.replace(/^upload:/, "");
