"""Deterministic validator of physical evidence in source code (D-06).

Golden rule: 100% of the file, line and snippet references must be real and
verifiable against the physical files of the analyzed repository.
Rejects or downgrades any hallucination produced by language models.
"""

from pathlib import Path
from typing import List, Tuple
from backend.app.models import EvidenceLocation, Finding, ValidationReport


def normalize_fragment(text: str) -> str:
    """Normalizes whitespace and line breaks for a robust comparison."""
    return " ".join(text.strip().split())


def validate_evidence_location(repo_dir: Path, loc: EvidenceLocation) -> Tuple[bool, str]:
    """Checks whether a code citation exists in the repository at the given lines."""
    file_path = repo_dir / loc.path
    if not file_path.exists():
        # Try whether the path carries prefixes such as 'samples/facturaya-v1/'
        parts = Path(loc.path).parts
        found_alt = None
        for i in range(len(parts)):
            candidate = repo_dir.joinpath(*parts[i:])
            if candidate.is_file():
                found_alt = candidate
                break
        if not found_alt:
            return False, f"The file '{loc.path}' does not exist in the analyzed repository."
        file_path = found_alt

    if not file_path.is_file():
        return False, f"'{loc.path}' is not a valid file."

    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as e:
        return False, f"Error leyendo '{loc.path}': {str(e)}"

    total_lines = len(lines)
    if loc.line_start < 1 or loc.line_start > total_lines:
        return False, f"Start line {loc.line_start} out of range (1-{total_lines}) in '{loc.path}'."

    if loc.line_end < loc.line_start or loc.line_end > total_lines:
        return False, f"End line {loc.line_end} invalid for the range (1-{total_lines}) in '{loc.path}'."

    # Extract the real content in that range (1-indexed)
    actual_lines = lines[loc.line_start - 1 : loc.line_end]
    actual_content = "\n".join(actual_lines)

    norm_target = normalize_fragment(loc.fragment)
    norm_actual = normalize_fragment(actual_content)

    if norm_target in norm_actual or norm_actual in norm_target:
        return True, "Citation verified."

    # Nearby fuzzy match (in case of a ±5 line drift)
    window_start = max(0, loc.line_start - 6)
    window_end = min(total_lines, loc.line_end + 6)
    window_content = normalize_fragment("\n".join(lines[window_start:window_end]))

    if norm_target in window_content:
        return True, f"Citation verified with a shift in window [{window_start+1}-{window_end}]."

    return False, f"The given snippet does not match the real code at lines {loc.line_start}-{loc.line_end}."


def validate_dossier_evidence(
    repo_dir: Path | str,
    findings: List[Finding],
) -> Tuple[List[Finding], ValidationReport]:
    """Audits every finding against the real repository and issues the validation report."""
    repo_path = Path(repo_dir)
    total_refs = 0
    valid_refs = 0
    invalid_refs = 0
    details: List[str] = []

    validated_findings: List[Finding] = []

    for f in findings:
        # Negative test controls do not require a mandatory physical citation
        if not f.expected_detection and not f.evidence:
            validated_findings.append(f)
            continue

        finding_valid = True
        if not f.evidence:
            f.status = "inferred"
            details.append(f"[{f.id}] No physical evidence cited; classified as inferred.")
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
                details.append(f"[{f.id}] Invalid at {ev.path}:{ev.line_start}-{ev.line_end}: {msg}")

        if finding_valid:
            f.status = "accepted"
        else:
            # With broken references, it is marked rejected or inferred
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
