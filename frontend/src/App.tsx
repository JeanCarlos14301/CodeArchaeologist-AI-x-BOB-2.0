import { AppShell } from "./components/shell/AppShell";
import { WorkspaceProvider, useWorkspace } from "./lib/workspace";
import { ArchitectureView } from "./views/ArchitectureView";
import { DependenciesView } from "./views/DependenciesView";
import { ModernizationView } from "./views/ModernizationView";
import { OverviewView } from "./views/OverviewView";
import { ProjectsView } from "./views/ProjectsView";
import { ReportsView } from "./views/ReportsView";
import { RepositoryView } from "./views/RepositoryView";
import { RisksView } from "./views/RisksView";
import { SessionView } from "./views/SessionView";

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
  return <CurrentView key={route.jobId ?? "projects"} />;
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
