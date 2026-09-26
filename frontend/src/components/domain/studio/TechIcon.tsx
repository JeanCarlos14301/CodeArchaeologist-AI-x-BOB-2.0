import { TECH_ICONS } from "../../../lib/techIcons";

interface Props {
  slug: string | null;
  name: string;
  /** Tamaño en px del cuadrado del icono. */
  size?: number;
}

/**
 * Icono monocromo de una tecnología (simple-icons). Hereda `currentColor`, así que el color lo decide
 * el contexto (DESIGN.md: color = significado). Sin icono conocido, muestra las iniciales en mono.
 */
export function TechIcon({ slug, name, size = 20 }: Props) {
  const path = slug ? TECH_ICONS[slug] : undefined;
  if (path) {
    return (
      <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor" aria-hidden className="shrink-0">
        <path d={path} />
      </svg>
    );
  }
  return (
    <span
      aria-hidden
      style={{ width: size, height: size }}
      className="inline-flex shrink-0 items-center justify-center rounded-tick border border-line-strong font-mono text-micro leading-none text-fg-2"
    >
      {name.replace(/[^A-Za-z0-9#+]/g, "").slice(0, 2)}
    </span>
  );
}
