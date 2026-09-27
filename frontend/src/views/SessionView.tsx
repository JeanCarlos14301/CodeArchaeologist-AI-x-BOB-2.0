import { AnalysisConsole } from "../components/domain/console/AnalysisConsole";
import { useWorkspace } from "../lib/workspace";
import { JobGate } from "./JobGate";

/** Bob session: live while the analysis runs and replayable once it finishes. */
export function SessionView() {
  const { flow, accessDenied, jobError, offline, route } = useWorkspace();
  // Access, errors and loading are resolved in JobGate; with the analysis loaded, the console in any state.
  if (!flow || accessDenied || jobError || (offline && !flow)) return <JobGate>{() => null}</JobGate>;
  return (
    <div className="px-6 py-6 @3xl:px-10">
      <AnalysisConsole autoplay={route.play} />
    </div>
  );
}
