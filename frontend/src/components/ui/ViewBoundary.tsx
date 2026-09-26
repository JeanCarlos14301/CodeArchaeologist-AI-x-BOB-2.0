import { Component, type ErrorInfo, type ReactNode } from "react";
import { ErrorState } from "./States";

interface State {
  failed: boolean;
}

/**
 * Si una vista no puede cargarse (p. ej. tras un redespliegue el navegador pide un fragmento del bundle
 * que ya no existe), se muestra un error accionable en lugar de una pantalla en blanco.
 */
export class ViewBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Sin logger en el cliente: la traza queda en la consola del navegador para diagnóstico.
    console.error("La vista falló al renderizarse", error, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="px-6 py-6 @3xl:px-10">
        <ErrorState
          title="No se pudo cargar esta vista."
          message="La aplicación se actualizó o falló al mostrar la sección."
          hint="Recarga la página para obtener la versión actual."
          onRetry={() => window.location.reload()}
          retryLabel="Recargar"
        />
      </div>
    );
  }
}
