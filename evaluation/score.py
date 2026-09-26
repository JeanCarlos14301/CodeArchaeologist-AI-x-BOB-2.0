"""Mide un expediente (`dossier.json`) contra la verdad de referencia `expected-findings.json`.

Reglas (las únicas que definen "acierto"; no hay comparación a mano):
- Solo cuentan los hallazgos VALIDADOS (`findings`); los `rejected_findings` no cuentan.
- Un esperado con `expected_detection: true` es un ACIERTO si algún hallazgo validado tiene una
  evidencia en el mismo archivo cuyo rango de líneas se solapa con alguna evidencia del esperado.
- Un control con `expected_detection: false` es un FALSO POSITIVO si algún hallazgo validado solapa.
- Un esperado que solo aparece entre los rechazados se informa como "rechazado por el validador".

Uso:
    python evaluation/score.py <dossier.json> [--expected evaluation/expected-findings.json]

Código de salida: 0 si se detectan todos los esperados y no hay falsos positivos; 1 en otro caso.
Solo usa la biblioteca estándar.
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
                return "acierto"
            return "rechazado por el validador" if self.rejected_by else "no detectado"
        return "falso positivo" if self.matched_by else "control limpio"

    @property
    def ok(self) -> bool:
        return self.outcome in {"acierto", "control limpio"}


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
    """Compara un expediente con la verdad de referencia."""
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
    lines = [f"Recall sobre hallazgos validados: {result.hits}/{len(result.expected)}"]
    for item in result.results:
        by = item.matched_by or item.rejected_by
        detail = f" ← {', '.join(by)}" if by else ""
        lines.append(f"  {'✔' if item.ok else '✘'} {item.id} {item.outcome}{detail} — {item.title}")
    lines.append(f"Falsos positivos sobre controles: {len(result.false_positives)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Puntúa un dossier.json contra expected-findings.json.")
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
        print("ERROR: el archivo no parece un dossier.json (falta `findings`).", file=sys.stderr)
        return 2
    result = score(dossier, expected)
    print(format_report(result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
