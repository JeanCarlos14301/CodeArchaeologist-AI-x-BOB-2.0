const DATE = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" });
const PERCENT = new Intl.NumberFormat("en", { style: "percent", maximumFractionDigits: 0 });
const DECIMAL = new Intl.NumberFormat("en", { maximumFractionDigits: 1 });

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

/** Readable job label: uploads carry the `upload:` prefix. */
export const jobLabel = (sample: string) => sample.replace(/^(upload|modernize):/, "");

/** Version as the project declares it, without pip's equality operator (`==3.1.0` -> `3.1.0`). */
export const cleanVersion = (version: string | null) => (version ? version.replace(/^==\s*/, "") : null);
