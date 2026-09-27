import { Component, type ErrorInfo, type ReactNode } from "react";
import { ErrorState } from "./States";

interface State {
  failed: boolean;
}

/**
 * If a view cannot load (e.g. after a redeploy the browser requests a bundle chunk that no longer
 * exists), an actionable error is shown instead of a blank screen.
 */
export class ViewBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // No client-side logger: the trace stays in the browser console for diagnosis.
    console.error("The view failed to render", error, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="px-6 py-6 @3xl:px-10">
        <ErrorState
          title="This view could not be loaded."
          message="The application was updated or failed to show the section."
          hint="Reload the page to get the current version."
          onRetry={() => window.location.reload()}
          retryLabel="Reload"
        />
      </div>
    );
  }
}
