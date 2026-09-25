"""Validador Determinista de Evidencia Física en Código Fuente (D-06).

Regla de oro: 100% de las referencias de archivo, línea y fragmento deben ser
reales y verificables contra los archivos físicos del repositorio analizado.
Rechaza o degrada cualquier alucinación producida por modelos de lenguaje.
"""

from pathlib import Path
from typing import List, Tuple
from backend.app.models import EvidenceLocation, Finding, ValidationReport


def normalize_fragment(text: str) -> str:
    """Normaliza espacios en blanco y saltos de línea para comparación robusta."""
    return " ".join(text.strip().split())


def validate_evidence_location(repo_dir: Path, loc: EvidenceLocation) -> Tuple[bool, str]:
    """Verifica si una cita de código existe en el repositorio en las líneas indicadas."""
    file_path = repo_dir / loc.path
    if not file_path.exists():
        # Intentar buscar si la ruta tiene prefijos como 'samples/facturaya-v1/'
        parts = Path(loc.path).parts
        found_alt = None
        for i in range(len(parts)):
            candidate = repo_dir.joinpath(*parts[i:])
            if candidate.is_file():
                found_alt = candidate
                break
        if not found_alt:
            return False, f"El archivo '{loc.path}' no existe en el repositorio analizado."
        file_path = found_alt

    if not file_path.is_file():
        return False, f"'{loc.path}' no es un archivo válido."

    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as e:
        return False, f"Error leyendo '{loc.path}': {str(e)}"

    total_lines = len(lines)
    if loc.line_start < 1 or loc.line_start > total_lines:
        return False, f"Línea de inicio {loc.line_start} fuera de rango (1-{total_lines}) en '{loc.path}'."

    if loc.line_end < loc.line_start or loc.line_end > total_lines:
        return False, f"Línea final {loc.line_end} inválida para rango (1-{total_lines}) en '{loc.path}'."

    # Extraer el contenido real en ese rango (1-indexed)
    actual_lines = lines[loc.line_start - 1 : loc.line_end]
    actual_content = "\n".join(actual_lines)

    norm_target = normalize_fragment(loc.fragment)
    norm_actual = normalize_fragment(actual_content)

    if norm_target in norm_actual or norm_actual in norm_target:
        return True, "Cita verificada con éxito."

    # Búsqueda de coincidencia difusa cercana (en caso de desplazamiento de ±5 líneas)
    window_start = max(0, loc.line_start - 6)
    window_end = min(total_lines, loc.line_end + 6)
    window_content = normalize_fragment("\n".join(lines[window_start:window_end]))

    if norm_target in window_content:
        return True, f"Cita verificada con desplazamiento en ventana [{window_start+1}-{window_end}]."

    return False, f"El fragmento especificado no coincide con el código real de las líneas {loc.line_start}-{loc.line_end}."


def validate_dossier_evidence(
    repo_dir: Path | str,
    findings: List[Finding],
) -> Tuple[List[Finding], ValidationReport]:
    """Audita todos los hallazgos contra el repositorio real y emite el informe de validación."""
    repo_path = Path(repo_dir)
    total_refs = 0
    valid_refs = 0
    invalid_refs = 0
    details: List[str] = []

    validated_findings: List[Finding] = []

    for f in findings:
        # Los controles negativos de prueba no requieren cita física obligatoria
        if not f.expected_detection and not f.evidence:
            validated_findings.append(f)
            continue

        finding_valid = True
        if not f.evidence:
            f.status = "inferred"
            details.append(f"[{f.id}] Sin evidencia física citada; clasificado como inferido.")
            validated_findings.append(f)
            continue

        for ev in f.evidence:
            total_refs += 1
            is_valid, msg = validate_evidence_location(repo_path, ev)
            if is_valid:
                valid_refs += 1
                ev.observed_or_inferred = "observed"
            else:
                invalid_refs += 1
                finding_valid = False
                ev.observed_or_inferred = "inferred"
                details.append(f"[{f.id}] Invalidez en {ev.path}:{ev.line_start}-{ev.line_end}: {msg}")

        if finding_valid:
            f.status = "accepted"
        else:
            # Si tiene referencias rotas, se marca rejected o inferred
            f.status = "inferred" if valid_refs > 0 else "rejected"

        validated_findings.append(f)

    fidelity = (valid_refs / total_refs) if total_refs > 0 else 1.0

    report = ValidationReport(
        total_references=total_refs,
        valid_references=valid_refs,
        invalid_references=invalid_refs,
        fidelity_ratio=round(fidelity, 4),
        details=details,
    )

    return validated_findings, report
