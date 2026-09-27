"""Deterministic evidence validator (D-06).

Every piece of evidence Bob cites is checked against the real repository:
- the path is relative, does not escape the root and points to an existing file;
- the line range exists in the file;
- the cited snippet appears in those lines (ignoring redundant whitespace; `...` separates
  pieces that must appear in order).
A finding is accepted only if all its evidence is valid.
"""

import re
from pathlib import Path

from app.contracts.schema_v1 import Evidence, EvidenceCheck, Finding

# Line margin tolerated around the cited range (Bob sometimes drifts by one line).
LINE_TOLERANCE = 1
_WHITESPACE = re.compile(r"\s+")
# Bob sometimes abbreviates long snippets with "..." or "…"; each piece must appear in order.
_ELLIPSIS = re.compile(r"\.\.\.|…")


def _normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def _segments_in_order(snippet: str, window: str) -> bool:
    """True if every non-empty piece of the snippet appears, in order, inside window."""
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
    """Returns the absolute path if it stays inside repo_root; otherwise None."""
    if Path(relative).is_absolute():
        return None
    candidate = (repo_root / relative).resolve()
    if not candidate.is_relative_to(repo_root):
        return None
    return candidate


def check_evidence(repo_root: Path, evidence: Evidence) -> tuple[bool, str]:
    """Validates one piece of evidence; returns (is_valid, reason)."""
    root = repo_root.resolve()
    target = resolve_inside(root, evidence.path)
    if target is None:
        return False, "path outside the repository"
    if not target.is_file():
        return False, "the file does not exist"
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    if evidence.line_start > len(lines):
        return False, f"line_start {evidence.line_start} exceeds the file's {len(lines)} lines"
    start = max(evidence.line_start - 1 - LINE_TOLERANCE, 0)
    end = min(evidence.line_end + LINE_TOLERANCE, len(lines))
    window = _normalize("\n".join(lines[start:end]))
    if _segments_in_order(evidence.snippet, window):
        return True, "snippet found in the cited range"
    return False, "the snippet does not appear in the cited range"


def validate_findings(
    repo_root: Path, findings: list[Finding]
) -> tuple[list[Finding], list[Finding], list[EvidenceCheck]]:
    """Splits accepted and rejected findings and returns the detail of every check."""
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
