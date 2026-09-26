"""Etapa migration-architect: propone 3 opciones de migración basadas en el ranking de riesgo.

Invoca el modo `migration-architect` de Bob pasando como DATOS el ranking ordenado
(finding_id, título, score) y el esquema de salida esperado.  No incluye código fuente
del repositorio auditado ni métricas numéricas de días, riesgo o radio; esos valores
los calcula el código determinista (decision_metrics.py) y se leen del Dossier.

Garantías:
- Validador determinista rechaza finding_ids inventados, cifras en pros/cons, más de
  una opción recomendada, y una recomendada que no sea la de mayor score del ranking.
- Fallback: si Bob falla o la respuesta se rechaza, migration_options queda vacío y
  se registra el motivo. Nunca se rellena con plantillas.
"""

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.adapters.bob_adapter import BobAdapter, BobError
from app.contracts.schema_v1 import Dossier, MigrationOption, RiskMetric

logger = logging.getLogger(__name__)

ARCHITECT_MODE = "migration-architect"

# Detecta cualquier número (entero o decimal) o símbolo de porcentaje en un string.
_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b|%")
# Estimaciones escritas con palabras ("dos semanas", "tres meses"): tampoco se admiten.
_WORD_ESTIMATE_RE = re.compile(
    r"\b(?:un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|veinte|treinta|cien|mil)\s+"
    r"(?:d[ií]as?|semanas?|meses|horas?|sprints?)\b",
    re.IGNORECASE,
)
EXPECTED_OPTIONS = 3

ARCHITECT_PROMPT_TEMPLATE = """Eres el migration-architect. Propones exactamente 3 opciones de migración para el
repositorio analizado, basándote ÚNICAMENTE en el ranking de riesgo que se te entrega como datos.

DATOS DE ENTRADA (ranking de hallazgos ordenados por score descendente):
{ranking_json}

REGLAS ABSOLUTAS
- finding_ids de cada opción deben ser un subconjunto de los IDs del ranking anterior.
- pros y cons deben ser texto cualitativo. PROHIBIDO incluir números, porcentajes,
  estimaciones de días, semanas o meses, porcentajes de riesgo ni cifras de ningún tipo.
- Exactamente UNA opción debe tener recommended=true: la que ataque el hallazgo de mayor score.
- No inventes hallazgos, archivos ni métricas. No menciones código del repositorio.
- Redacta name, pattern, pros y cons en español.

FORMATO DE SALIDA
Tu mensaje final debe ser ÚNICAMENTE un objeto JSON válido (sin texto adicional, sin markdown)
que cumpla este esquema:
{schema_json}
"""

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _build_prompt(ranking: list[RiskMetric], findings_by_id: dict[str, str]) -> str:
    ranking_data = [
        {
            "finding_id": item.finding_id,
            "title": findings_by_id.get(item.finding_id, ""),
            "score": item.score,
        }
        for item in ranking
    ]
    schema = {
        "migration_options": {
            "type": "array",
            "items": MigrationOption.model_json_schema(),
            "minItems": 3,
            "maxItems": 3,
        }
    }
    return ARCHITECT_PROMPT_TEMPLATE.format(
        ranking_json=json.dumps(ranking_data, ensure_ascii=False, indent=2),
        schema_json=json.dumps(schema, ensure_ascii=False, indent=2),
    )


def _extract_options(message: str) -> list[dict[str, Any]]:
    """Obtiene la lista de opciones del JSON en la respuesta de Bob."""
    fenced = _FENCE_RE.search(message)
    raw = fenced.group(1) if fenced else message[message.find("{") : message.rfind("}") + 1]
    if not raw:
        raise ValueError("La respuesta de Bob no contiene JSON.")
    data = json.loads(raw)
    if isinstance(data, dict) and "migration_options" in data:
        return data["migration_options"]
    raise ValueError("El JSON no tiene la clave 'migration_options'.")


def _validate_options(
    options: list[dict[str, Any]],
    valid_ids: set[str],
    top_id: str,
) -> list[MigrationOption]:
    """Valida las opciones con reglas deterministas; lanza ValueError con motivo si alguna falla."""
    parsed: list[MigrationOption] = []
    for raw in options:
        try:
            opt = MigrationOption.model_validate(raw)
        except ValidationError as exc:
            raise ValueError(f"Opción inválida según el esquema: {exc}") from exc
        parsed.append(opt)

    if len(parsed) != EXPECTED_OPTIONS:
        raise ValueError(f"Se esperaban exactamente {EXPECTED_OPTIONS} opciones; llegaron {len(parsed)}.")
    if len({opt.id for opt in parsed}) != len(parsed):
        raise ValueError("Las opciones repiten su identificador.")

    # 1. finding_ids deben pertenecer al ranking
    for opt in parsed:
        unknown = set(opt.finding_ids) - valid_ids
        if unknown:
            raise ValueError(
                f"La opción {opt.id!r} referencia finding_ids que no están en el ranking: {sorted(unknown)}"
            )

    # 2. Prohibición de números en pros/cons
    for opt in parsed:
        for text in [*opt.pros, *opt.cons]:
            if _NUMBER_RE.search(text) or _WORD_ESTIMATE_RE.search(text):
                raise ValueError(
                    f"La opción {opt.id!r} contiene cifras o porcentajes en pros/cons: {text!r}"
                )

    # 3. Exactamente una recomendada
    recommended = [opt for opt in parsed if opt.recommended]
    if len(recommended) != 1:
        raise ValueError(
            f"Debe haber exactamente una opción recomendada; se encontraron {len(recommended)}."
        )

    # 4. La recomendada debe ser la del hallazgo de mayor score
    rec = recommended[0]
    if top_id not in rec.finding_ids:
        raise ValueError(
            f"La opción recomendada {rec.id!r} no incluye el hallazgo de mayor score ({top_id!r})."
        )

    return parsed


def run_migration_architect(dossier: Dossier, adapter: BobAdapter) -> tuple[list[MigrationOption], str]:
    """Invoca Bob en modo migration-architect y devuelve las opciones validadas.

    Returns:
        (options, reason): si la etapa tiene éxito, reason es ""; si falla, options es [] y reason
        describe el motivo (para registrar, no para mostrar al usuario como error fatal).
    """
    if not dossier.risk_matrix:
        return [], "El risk_matrix está vacío; no hay ranking para el arquitecto."

    findings_by_id = {f.id: f.title for f in dossier.findings}
    ranking_sorted = sorted(dossier.risk_matrix, key=lambda r: (r.score, r.finding_id), reverse=True)
    valid_ids = {r.finding_id for r in ranking_sorted}
    # Mismo criterio de desempate que decision_metrics.calculate_decision_metrics para el primer corte.
    top_id = max(dossier.risk_matrix, key=lambda r: (r.score, r.severity_weight, r.finding_id)).finding_id

    prompt = _build_prompt(ranking_sorted, findings_by_id)
    try:
        result = adapter.run(ARCHITECT_MODE, prompt)
    except BobError as exc:
        reason = f"Bob falló en migration-architect: {exc}"
        logger.warning(reason)
        return [], reason

    try:
        raw_options = _extract_options(result.last_message)
        options = _validate_options(raw_options, valid_ids, top_id)
    except (ValueError, json.JSONDecodeError) as exc:
        reason = f"Respuesta de migration-architect rechazada: {exc}"
        logger.warning(reason)
        return [], reason

    return options, ""
