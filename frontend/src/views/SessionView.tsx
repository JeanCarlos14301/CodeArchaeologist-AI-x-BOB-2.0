import { AnalysisConsole } from "../components/domain/console/AnalysisConsole";
import { useWorkspace } from "../lib/workspace";
import { JobGate } from "./JobGate";

/** Sesión de Bob: en vivo mientras el análisis corre y reproducible cuando termina. */
export function SessionView() {
  const { flow, accessDenied, jobError, offline, route } = useWorkspace();
  // Acceso, errores y carga se resuelven en JobGate; con el análisis cargado, la consola en cualquier estado.
  if (!flow || accessDenied || jobError || (offline && !flow)) return <JobGate>{() => null}</JobGate>;
  return (
    <div className="px-6 py-6 @3xl:px-10">
      <AnalysisConsole autoplay={route.play} />
    </div>
  );
}
