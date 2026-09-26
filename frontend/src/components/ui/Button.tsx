import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md";

const BASE =
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-pill font-medium whitespace-nowrap " +
  "transition-[color,background-color,border-color,box-shadow,transform] duration-150 ease-out " +
  "active:scale-[0.97] disabled:pointer-events-none disabled:opacity-40";

const VARIANT: Record<Variant, string> = {
  primary: "border border-accent-hover bg-accent font-semibold text-on-accent shadow-glow hover:bg-accent-hover",
  secondary: "border border-line-strong bg-control text-fg hover:border-fg/40 hover:bg-raised",
  ghost: "border border-transparent text-fg-2 hover:bg-raised hover:text-fg",
};

const SIZE: Record<Size, string> = {
  sm: "h-7 px-3 text-caption",
  md: "h-9 px-4 text-caption",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  icon?: ReactNode;
}

/** Botón píldora. `primary` es la acción principal: una por pantalla (DESIGN.md §4). */
export function Button({ variant = "secondary", size = "md", icon, className = "", children, type = "button", ...rest }: ButtonProps) {
  return (
    <button type={type} className={`${BASE} ${VARIANT[variant]} ${SIZE[size]} ${className}`} {...rest}>
      {icon}
      {children}
    </button>
  );
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  active?: boolean;
}

/** Botón de icono de 32px con área táctil de 40px y etiqueta accesible obligatoria. */
export function IconButton({ label, active = false, className = "", children, type = "button", ...rest }: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      className={`relative inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-pill text-fg-2 transition-[color,background-color] duration-150 ease-out before:absolute before:-inset-1 before:content-[''] hover:bg-raised hover:text-fg ${active ? "bg-raised text-fg" : ""} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
