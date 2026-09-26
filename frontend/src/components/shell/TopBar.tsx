import { ChevronDown, Menu, PanelRightClose, PanelRightOpen, Search } from "lucide-react";
import { useWorkspace } from "../../lib/workspace";
import { Kbd, ModeBadge } from "../ui/Badge";
import { IconButton } from "../ui/Button";
import { BrandMark } from "./BrandMark";

export function TopBar({ onOpenNav }: { onOpenNav: () => void }) {
  const { flow, dossier, route, navigate, setPaletteOpen, aiOpen, setAiOpen } = useWorkspace();
  const mode = dossier?.execution_mode ?? flow?.execution_mode;

  return (
    <header className="flex h-12 items-center gap-2 border-b border-line bg-canvas px-3">
      <IconButton label="Abrir navegación" className="lg:hidden" onClick={onOpenNav}>
        <Menu size={16} aria-hidden />
      </IconButton>
      <button type="button" onClick={() => navigate({ jobId: null })} className="flex items-center gap-2.5 rounded-inner px-1.5 py-1" aria-label="CodeArchaeologist, ir a Proyectos">
        <BrandMark />
        <span className="hidden font-display text-body text-fg sm:inline">CodeArchaeologist</span>
      </button>

      <span aria-hidden className="mx-1 hidden h-4 w-px bg-line-strong sm:block" />

      {route.jobId ? (
        <button
          type="button"
          onClick={() => setPaletteOpen(true)}
          className="flex min-w-0 items-center gap-2 rounded-pill px-2.5 py-1 text-body hover:bg-raised"
          aria-label="Cambiar de proyecto o análisis"
        >
          <span className="truncate font-mono text-caption text-fg">{flow?.label ?? route.jobId}</span>
          {mode && <span className="hidden sm:inline-flex"><ModeBadge mode={mode} /></span>}
          <ChevronDown size={14} aria-hidden className="shrink-0 text-subtle" />
        </button>
      ) : (
        <span className="text-caption text-subtle">Sin proyecto abierto</span>
      )}

      <button
        type="button"
        onClick={() => setPaletteOpen(true)}
        className="ml-auto hidden h-8 w-80 items-center gap-2 rounded-pill border border-line bg-control px-3 text-caption whitespace-nowrap text-subtle transition-[border-color] duration-150 hover:border-line-strong md:flex"
      >
        <Search size={14} aria-hidden />
        <span className="truncate">Buscar hallazgos, archivos o acciones…</span>
        <span className="ml-auto flex gap-0.5"><Kbd>⌘</Kbd><Kbd>K</Kbd></span>
      </button>
      <IconButton label="Buscar o ejecutar acción" className="ml-auto md:hidden" onClick={() => setPaletteOpen(true)}>
        <Search size={16} aria-hidden />
      </IconButton>

      <IconButton label={aiOpen ? "Cerrar panel de Bob (⌘J)" : "Abrir panel de Bob (⌘J)"} active={aiOpen} onClick={() => setAiOpen(!aiOpen)}>
        {aiOpen ? <PanelRightClose size={16} aria-hidden /> : <PanelRightOpen size={16} aria-hidden />}
      </IconButton>
    </header>
  );
}
