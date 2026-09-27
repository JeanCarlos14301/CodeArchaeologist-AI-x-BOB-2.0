"""Scores a dossier (`dossier.json`) against the ground truth `expected-findings.json`.

Rules (the only ones that define a "hit"; there is no manual comparison):
- Only VALIDATED findings (`findings`) count; `rejected_findings` do not.
- An expected finding with `expected_detection: true` is a HIT if some validated finding has a
  piece of evidence in the same file whose line range overlaps any evidence of the expected one.
- A control with `expected_detection: false` is a FALSE POSITIVE if some validated finding overlaps it.
- An expected finding that only shows up among the rejected ones is reported as "rejected by the validator".

Usage:
    python evaluation/score.py <dossier.json> [--expected evaluation/expected-findings.json]

Exit code: 0 if every expected finding is detected and there are no false positives; 1 otherwise.
Standard library only.
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_EXPECTED = Path(__file__).with_name("expected-findings.json")

Range = tuple[str, int, int]


@dataclass
class ExpectedResult:
    id: str
    title: str
    should_detect: bool
    matched_by: list[str] = field(default_factory=list)
    rejected_by: list[str] = field(default_factory=list)

    @property
    def outcome(self) -> str:
        if self.should_detect:
            if self.matched_by:
                return "hit"
            return "rejected by the validator" if self.rejected_by else "not detected"
        return "false positive" if self.matched_by else "clean control"

    @property
    def ok(self) -> bool:
        return self.outcome in {"hit", "clean control"}


@dataclass
class Score:
    results: list[ExpectedResult]

    @property
    def expected(self) -> list[ExpectedResult]:
        return [item for item in self.results if item.should_detect]

    @property
    def hits(self) -> int:
        return sum(1 for item in self.expected if item.matched_by)

    @property
    def false_positives(self) -> list[ExpectedResult]:
        return [item for item in self.results if not item.should_detect and item.matched_by]

    @property
    def passed(self) -> bool:
        return self.hits == len(self.expected) and not self.false_positives


def _ranges(evidence: list[dict[str, Any]]) -> list[Range]:
    return [(item["path"], int(item["line_start"]), int(item["line_end"])) for item in evidence]


def _overlap(a: Range, b: Range) -> bool:
    return a[0] == b[0] and a[1] <= b[2] and b[1] <= a[2]


def _touching(reference: list[Range], findings: list[dict[str, Any]]) -> list[str]:
    return sorted({
        finding["id"]
        for finding in findings
        if any(_overlap(cited, wanted) for cited in _ranges(finding.get("evidence", [])) for wanted in reference)
    })


def score(dossier: dict[str, Any], expected: dict[str, Any]) -> Score:
    """Compares a dossier with the ground truth."""
    validated = dossier.get("findings", [])
    rejected = dossier.get("rejected_findings", [])
    results = []
    for item in expected["findings"]:
        reference = _ranges(item["evidence"])
        results.append(ExpectedResult(
            id=item["id"],
            title=item["title"],
            should_detect=bool(item.get("expected_detection", True)),
            matched_by=_touching(reference, validated),
            rejected_by=_touching(reference, rejected),
        ))
    return Score(results)


def format_report(result: Score) -> str:
    lines = [f"Recall on validated findings: {result.hits}/{len(result.expected)}"]
    for item in result.results:
        by = item.matched_by or item.rejected_by
        detail = f" ← {', '.join(by)}" if by else ""
        lines.append(f"  {'✔' if item.ok else '✘'} {item.id} {item.outcome}{detail} — {item.title}")
    lines.append(f"False positives on controls: {len(result.false_positives)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scores a dossier.json against expected-findings.json.")
    parser.add_argument("dossier", type=Path)
    parser.add_argument("--expected", type=Path, default=DEFAULT_EXPECTED)
    args = parser.parse_args(argv)
    try:
        dossier = json.loads(args.dossier.read_text(encoding="utf-8"))
        expected = json.loads(args.expected.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if "findings" not in dossier:
        print("ERROR: the file does not look like a dossier.json (`findings` is missing).", file=sys.stderr)
        return 2
    result = score(dossier, expected)
    print(format_report(result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
