/**
 * Marca: testigo de sondeo arqueológico (columna vertical con estratos). El estrato más profundo,
 * el que se analiza, en naranja señal: la única nota de color de la marca.
 */
export function BrandMark({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <defs>
        <clipPath id="ca-core">
          <rect x="5.5" y="1.5" width="9" height="17" rx="4.5" />
        </clipPath>
      </defs>
      <g clipPath="url(#ca-core)">
        <rect x="5.5" y="1.5" width="9" height="17" fill="var(--color-canvas)" />
        <rect x="5.5" y="6" width="9" height="1.6" fill="var(--color-fg)" />
        <rect x="5.5" y="9.6" width="9" height="1.6" fill="var(--color-fg-2)" />
        <rect x="5.5" y="13.2" width="9" height="5.3" fill="var(--color-accent)" />
      </g>
      <rect x="5.5" y="1.5" width="9" height="17" rx="4.5" fill="none" stroke="var(--color-fg)" strokeOpacity="0.55" />
    </svg>
  );
}
