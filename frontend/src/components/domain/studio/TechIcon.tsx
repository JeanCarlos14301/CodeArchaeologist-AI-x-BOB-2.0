import { TECH_ICONS } from "../../../lib/techIcons";

interface Props {
  slug: string | null;
  name: string;
  /** Size in px of the icon's square. */
  size?: number;
}

/**
 * Monochrome icon of a technology (simple-icons). It inherits `currentColor`, so the color is decided by
 * the context (DESIGN.md: color = meaning). Without a known icon, it shows the initials in mono.
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
