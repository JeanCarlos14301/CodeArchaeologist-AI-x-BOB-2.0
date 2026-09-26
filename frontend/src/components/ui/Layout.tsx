import type { KeyboardEvent, ReactNode } from "react";

/** Eyebrow: kicker en mayúsculas sobre un título (DESIGN.md §2.3, text-micro). */
export function Eyebrow({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <p className={`text-micro font-medium tracking-eyebrow text-subtle uppercase ${className}`}>{children}</p>;
}

/** Cabecera de pantalla: objeto principal + pregunta que responde + acciones. */
export function ScreenHeader({ eyebrow, title, description, meta, actions }: {
  eyebrow: string;
  title: ReactNode;
  description?: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3 border-b border-line pb-5">
      <div className="min-w-0">
        <Eyebrow>{eyebrow}</Eyebrow>
        <h1 className="mt-1.5 font-display text-heading font-normal text-balance text-fg">{title}</h1>
        {description && <p className="mt-1.5 max-w-3xl text-body text-pretty text-muted">{description}</p>}
        {meta && <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-caption text-subtle">{meta}</div>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

/** Sección separada por hairline: la unidad de layout por defecto (no tarjetas). */
export function Section({ eyebrow, title, aside, children, className = "", id }: {
  eyebrow?: string;
  title?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section id={id} aria-labelledby={id && title ? `${id}-title` : undefined} className={`border-b border-line py-6 last:border-b-0 ${className}`}>
      {(eyebrow || title || aside) && (
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
          <div>
            {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
            {title && <h2 id={id ? `${id}-title` : undefined} className="mt-1 font-display text-title font-normal text-fg">{title}</h2>}
          </div>
          {aside && <div className="text-caption text-subtle">{aside}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

/** Panel para objetos reales o superficies de herramienta (inspector, árbol, visor). */
export function Panel({ children, className = "", as: Tag = "div" }: { children: ReactNode; className?: string; as?: "div" | "section" | "aside" | "article" }) {
  return <Tag className={`rounded-panel border border-line bg-surface ${className}`}>{children}</Tag>;
}

/** Filas clave–valor densas para datos técnicos. */
export function DataList({ rows, className = "" }: { rows: { label: ReactNode; value: ReactNode; hint?: ReactNode }[]; className?: string }) {
  return (
    <dl className={`divide-y divide-line-subtle ${className}`}>
      {rows.map((row, index) => (
        <div key={index} className="flex items-baseline justify-between gap-4 py-2">
          <dt className="text-body text-muted">{row.label}</dt>
          <dd className="text-right">
            <span className="font-mono text-body text-fg tabular-nums">{row.value}</span>
            {row.hint && <span className="block text-caption text-subtle">{row.hint}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/** Barra de medida de 4px con valor tabular. El relleno usa un color semántico explícito. */
export function Meter({ label, value, max, tone = "bg-fg", detail }: { label: string; value: number; max: number; tone?: string; detail?: string }) {
  const ratio = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0;
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <span className="text-body text-fg-2">{label}</span>
        <span className="font-mono text-caption text-fg tabular-nums">{max > 0 ? `${value}/${max}` : "—"}</span>
      </div>
      <div className="h-1 overflow-hidden rounded-pill bg-raised" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={max} aria-valuenow={value}>
        <div className={`h-full rounded-pill ${tone}`} style={{ width: `${ratio * 100}%` }} />
      </div>
      {detail && <p className="mt-1 text-caption text-subtle">{detail}</p>}
    </div>
  );
}

/** Segmentado accesible (radiogroup) en píldora. */
export function Segmented<T extends string>({ value, options, onChange, label }: {
  value: T;
  options: { value: T; label: ReactNode; disabled?: boolean; hint?: string }[];
  onChange: (value: T) => void;
  label: string;
}) {
  const enabled = options.filter((option) => !option.disabled);
  const onKey = (event: KeyboardEvent<HTMLDivElement>) => {
    const index = enabled.findIndex((option) => option.value === value);
    const moves: Record<string, number> = { ArrowRight: index + 1, ArrowDown: index + 1, ArrowLeft: index - 1, ArrowUp: index - 1, Home: 0, End: enabled.length - 1 };
    if (!(event.key in moves) || enabled.length === 0) return;
    event.preventDefault();
    const next = enabled[(moves[event.key] + enabled.length) % enabled.length];
    onChange(next.value);
    event.currentTarget.querySelector<HTMLButtonElement>(`[data-value="${next.value}"]`)?.focus();
  };
  return (
    <div role="radiogroup" aria-label={label} onKeyDown={onKey} className="inline-flex flex-wrap gap-0.5 rounded-pill border border-line bg-surface p-0.5">
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            data-value={option.value}
            tabIndex={active ? 0 : -1}
            aria-checked={active}
            disabled={option.disabled}
            title={option.hint}
            onClick={() => onChange(option.value)}
            className={`inline-flex h-7 items-center gap-1.5 rounded-pill px-3 text-caption transition-[color,background-color] duration-150 ease-out disabled:cursor-not-allowed disabled:opacity-40 ${active ? "bg-raised text-fg shadow-inset-accent" : "text-muted hover:text-fg"}`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
