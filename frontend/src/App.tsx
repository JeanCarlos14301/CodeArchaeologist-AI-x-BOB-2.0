import { lazy, Suspense } from "react";
import { AppShell } from "./components/shell/AppShell";
import { Loading } from "./components/ui/States";
import { ViewBoundary } from "./components/ui/ViewBoundary";
import { WorkspaceProvider, useWorkspace } from "./lib/workspace";
import { OverviewView } from "./views/OverviewView";
import { ProjectsView } from "./views/ProjectsView";

// Proyectos y Resumen van en el bundle inicial; el resto se descarga al abrir su sección
// (el Estudio arrastra los iconos de tecnologías y la Arquitectura, los grafos).
const SessionView = lazy(() => import("./views/SessionView").then((m) => ({ default: m.SessionView })));
const ArchitectureView = lazy(() => import("./views/ArchitectureView").then((m) => ({ default: m.ArchitectureView })));
const RepositoryView = lazy(() => import("./views/RepositoryView").then((m) => ({ default: m.RepositoryView })));
const DependenciesView = lazy(() => import("./views/DependenciesView").then((m) => ({ default: m.DependenciesView })));
const RisksView = lazy(() => import("./views/RisksView").then((m) => ({ default: m.RisksView })));
const ModernizationView = lazy(() => import("./views/ModernizationView").then((m) => ({ default: m.ModernizationView })));
const ReportsView = lazy(() => import("./views/ReportsView").then((m) => ({ default: m.ReportsView })));

function CurrentView() {
  const { route } = useWorkspace();
  if (!route.jobId) return <ProjectsView />;
  switch (route.section) {
    case "session":
      return <SessionView />;
    case "architecture":
      return <ArchitectureView />;
    case "repository":
      return <RepositoryView />;
    case "dependencies":
      return <DependenciesView />;
    case "risks":
      return <RisksView />;
    case "modernization":
      return <ModernizationView />;
    case "reports":
      return <ReportsView />;
    default:
      return <OverviewView />;
  }
}

/** Remonta la vista al cambiar de análisis para que su estado local (pestañas, filtros) no se arrastre. */
function KeyedView() {
  const { route } = useWorkspace();
  return (
    <ViewBoundary key={`${route.jobId ?? "projects"}:${route.section}`}>
      <Suspense fallback={<div className="px-6 py-6 @3xl:px-10"><Loading label="Cargando la sección…" /></div>}>
        <CurrentView key={route.jobId ?? "projects"} />
      </Suspense>
    </ViewBoundary>
  );
}

export default function App() {
  return (
    <WorkspaceProvider>
      <AppShell>
        <KeyedView />
      </AppShell>
    </WorkspaceProvider>
  );
}
