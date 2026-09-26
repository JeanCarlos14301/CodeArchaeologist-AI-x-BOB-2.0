import { useEffect, useRef, useState, type ReactNode } from "react";
import { useFocusTrap } from "../ui/useFocusTrap";
import { useWorkspace } from "../../lib/workspace";
import { AIPanel } from "./AIPanel";
import { CommandPalette } from "./CommandPalette";
import { NavRail } from "./NavRail";
import { StatusBar } from "./StatusBar";
import { TopBar } from "./TopBar";

const LG = "(min-width: 1024px)";

function useIsDesktop(): boolean {
  const [desktop, setDesktop] = useState(() => window.matchMedia(LG).matches);
  useEffect(() => {
    const query = window.matchMedia(LG);
    const onChange = () => setDesktop(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return desktop;
}

/** Shell de herramienta: barra superior · navegación · workspace · panel de Bob · barra de estado (DESIGN.md §3). */
export function AppShell({ children }: { children: ReactNode }) {
  const { aiOpen, setAiOpen, paletteOpen, setPaletteOpen, route } = useWorkspace();
  const [navOpen, setNavOpen] = useState(false);
  const desktop = useIsDesktop();

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const mod = event.metaKey || event.ctrlKey;
      if (mod && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen(!paletteOpen);
      } else if (mod && event.key.toLowerCase() === "j") {
        event.preventDefault();
        setAiOpen(!aiOpen);
      } else if (event.key === "Escape" && !desktop) {
        setNavOpen(false);
        if (aiOpen) setAiOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [aiOpen, paletteOpen, desktop, setAiOpen, setPaletteOpen]);

  useEffect(() => setNavOpen(false), [route.jobId, route.section]);

  const showAiDocked = desktop && aiOpen;
  const drawerOpen = !desktop && (navOpen || aiOpen);

  return (
    <div className="grid h-dvh grid-cols-[minmax(0,1fr)] grid-rows-[auto_minmax(0,1fr)_auto] bg-canvas">
      <a href="#workspace" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-pill focus:bg-overlay focus:px-3 focus:py-1.5 focus:text-caption">
        Saltar al contenido
      </a>
      <TopBar onOpenNav={() => setNavOpen(true)} />

      <div inert={drawerOpen} className={`grid min-h-0 grid-cols-[minmax(0,1fr)] ${showAiDocked ? "lg:grid-cols-[224px_minmax(0,1fr)_360px]" : "lg:grid-cols-[224px_minmax(0,1fr)]"}`}>
        <div className="hidden min-h-0 overflow-y-auto border-r border-line bg-surface lg:block">
          <NavRail />
        </div>

        <main id="workspace" tabIndex={-1} className="@container min-h-0 overflow-y-auto focus:outline-none">
          {children}
        </main>

        {showAiDocked && (
          <div className="min-h-0 border-l border-line">
            <AIPanel onClose={() => setAiOpen(false)} />
          </div>
        )}
      </div>

      <StatusBar />

      {!desktop && navOpen && (
        <Drawer side="left" label="Navegación" onClose={() => setNavOpen(false)}>
          <NavRail onNavigate={() => setNavOpen(false)} />
        </Drawer>
      )}
      {!desktop && aiOpen && (
        <Drawer side="right" label="Asistente IBM Bob" onClose={() => setAiOpen(false)}>
          <AIPanel onClose={() => setAiOpen(false)} />
        </Drawer>
      )}
      <CommandPalette />
    </div>
  );
}

function Drawer({ side, label, onClose, children }: { side: "left" | "right"; label: string; onClose: () => void; children: ReactNode }) {
  const panel = useRef<HTMLDivElement>(null);
  useFocusTrap(panel);
  return (
    <div className="fixed inset-0 z-40 bg-canvas/70" onMouseDown={onClose}>
      <div
        ref={panel}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        onMouseDown={(event) => event.stopPropagation()}
        className={`absolute inset-y-0 w-[min(360px,90vw)] animate-enter overflow-y-auto border-line bg-surface ${side === "left" ? "left-0 border-r" : "right-0 border-l"}`}
      >
        {children}
      </div>
    </div>
  );
}
