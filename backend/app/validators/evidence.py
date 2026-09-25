"""Validador determinista de evidencia (etapa 3, D-06).

Cada evidencia que cita Bob se comprueba contra el repositorio real:
- la ruta es relativa, no escapa de la raíz y apunta a un archivo existente;
- el rango de líneas existe en el archivo;
- el fragmento citado aparece en esas líneas (sin espacios redundantes; `...` separa
  trozos que deben aparecer en orden).
Un hallazgo se acepta solo si todas sus evidencias son válidas.
"""

import re
from pathlib import Path

from app.contracts.schema_v1 import Evidence, EvidenceCheck, Finding

# Margen de líneas tolerado alrededor del rango citado (Bob a veces se desplaza una línea).
LINE_TOLERANCE = 1
_WHITESPACE = re.compile(r"\s+")
# Bob a veces abrevia fragmentos largos con "..." o "…"; cada trozo debe aparecer en orden.
_ELLIPSIS = re.compile(r"\.\.\.|…")


def _normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def _segments_in_order(snippet: str, window: str) -> bool:
    """True si todos los trozos no vacíos del fragmento aparecen en orden dentro de window."""
    segments = [_normalize(part) for part in _ELLIPSIS.split(snippet)]
    segments = [segment for segment in segments if segment]
    if not segments:
        return False
    position = 0
    for segment in segments:
        found = window.find(segment, position)
        if found < 0:
            return False
        position = found + len(segment)
    return True


def resolve_inside(repo_root: Path, relative: str) -> Path | None:
    """Devuelve la ruta absoluta si queda dentro de repo_root; si no, None."""
    if Path(relative).is_absolute():
        return None
    candidate = (repo_root / relative).resolve()
    if not candidate.is_relative_to(repo_root):
        return None
    return candidate


def check_evidence(repo_root: Path, evidence: Evidence) -> tuple[bool, str]:
    """Valida una evidencia; devuelve (es_válida, motivo)."""
    root = repo_root.resolve()
    target = resolve_inside(root, evidence.path)
    if target is None:
        return False, "ruta fuera del repositorio"
    if not target.is_file():
        return False, "el archivo no existe"
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    if evidence.line_start > len(lines):
        return False, f"line_start {evidence.line_start} supera las {len(lines)} líneas del archivo"
    start = max(evidence.line_start - 1 - LINE_TOLERANCE, 0)
    end = min(evidence.line_end + LINE_TOLERANCE, len(lines))
    window = _normalize("\n".join(lines[start:end]))
    if _segments_in_order(evidence.snippet, window):
        return True, "fragmento encontrado en el rango citado"
    return False, "el fragmento no aparece en el rango citado"


def validate_findings(
    repo_root: Path, findings: list[Finding]
) -> tuple[list[Finding], list[Finding], list[EvidenceCheck]]:
    """Separa hallazgos aceptados y rechazados y devuelve el detalle de cada comprobación."""
    accepted: list[Finding] = []
    rejected: list[Finding] = []
    checks: list[EvidenceCheck] = []
    for finding in findings:
        finding_checks = [
            EvidenceCheck(
                finding_id=finding.id,
                evidence_index=index,
                status="valid" if ok else "invalid",
                reason=reason,
            )
            for index, (ok, reason) in enumerate(
                check_evidence(repo_root, evidence) for evidence in finding.evidence
            )
        ]
        checks.extend(finding_checks)
        if all(check.status == "valid" for check in finding_checks):
            accepted.append(finding)
        else:
            rejected.append(finding)
    return accepted, rejected, checks
