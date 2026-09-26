import type { ReactNode } from "react";

/** Estado vacío que ayuda a actuar: qué falta, por qué y la acción concreta (PRODUCT.md §28). */
export function EmptyState({ title, children, action, className = "" }: { title: string; children?: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <div className={`rounded-panel border border-dashed border-line-strong px-6 py-10 ${className}`}>
      <h2 className="font-display text-title font-normal text-fg">{title}</h2>
      {children && <div className="mt-1.5 max-w-xl text-body text-pretty text-muted">{children}</div>}
      {action && <div className="mt-5 flex flex-wrap gap-2">{action}</div>}
    </div>
  );
}

/** Error con qué pasó · por qué importa · qué hacer (PRODUCT.md §29). */
export function ErrorState({ title, message, hint, onRetry, retryLabel = "Reintentar" }: {
  title: string;
  message: string;
  hint?: ReactNode;
  onRetry?: () => void;
  retryLabel?: string;
}) {
  return (
    <div role="alert" className="rounded-panel border border-danger/40 bg-danger/5 px-5 py-4">
      <p className="text-body font-medium text-fg"><span aria-hidden className="mr-2 text-danger">✗</span>{title}</p>
      <p className="mt-1 font-mono text-caption text-fg-2">{message}</p>
      {hint && <p className="mt-2 text-caption text-muted">{hint}</p>}
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-3 inline-flex h-7 items-center rounded-pill border border-line-strong px-3 text-caption text-fg hover:bg-raised">
          {retryLabel}
        </button>
      )}
    </div>
  );
}

export function Loading({ label }: { label: string }) {
  return (
    <div role="status" className="flex items-center gap-2.5 py-10 text-body text-muted">
      <span aria-hidden className="h-3 w-3 animate-spin rounded-pill border-2 border-line-strong border-t-activity" />
      {label}
    </div>
  );
}
