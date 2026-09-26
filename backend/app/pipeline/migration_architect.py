"""Etapa migration-architect: Bob redacta 3 opciones de migración sobre el ranking de RUTAS.

El motor determinista (migration_ranking.py) ya eligió el primer corte por relación valor/riesgo (D3).
Bob recibe como DATOS los mejores candidatos (endpoint, justificación medida y hallazgos que mitiga)
y redacta una opción por candidato: nombre, patrón, ventajas y riesgos cualitativos. No recibe código
fuente ni produce cifras: días, riesgo y puntajes los calcula el código.

Garantías del validador:
- Una opción por candidato, con el `endpoint` exacto de ese candidato y sin repetir.
- `finding_ids` solo puede citar hallazgos que ese candidato mitiga según el motor.
- Ninguna cifra, porcentaje ni estimación en palabras dentro de pros/cons.
- Exactamente una opción recomendada y debe ser el corte que eligió el motor: Bob explica la
  decisión, no la contradice.
- Fallback: si Bob falla o la respuesta se rechaza, migration_options queda vacío y se registra
  el motivo. Nunca se rellena con plantillas.
"""

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.adapters.bob_adapter import BobAdapter, BobError, BobRunSettings
from app.contracts.schema_v1 import Dossier, MigrationOption, RouteCandidate

logger = logging.getLogger(__name__)

ARCHITECT_MODE = "migration-architect"
MAX_OPTIONS = 3

# The architect only writes qualitative text over data it receives: a short, cheap session is enough.
ARCHITECT_MAX_TURNS = 6
ARCHITECT_MAX_COST = 1.0
ARCHITECT_TIMEOUT_S = 240

# Detecta cualquier número (entero o decimal) o símbolo de porcentaje en un string.
_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b|%")
# Estimaciones escritas con palabras ("dos semanas", "tres meses"): tampoco se admiten.
_WORD_ESTIMATE_RE = re.compile(
    r"\b(?:un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|veinte|treinta|cien|mil)\s+"
    r"(?:d[ií]as?|semanas?|meses|horas?|sprints?)\b",
    re.IGNORECASE,
)

ARCHITECT_PROMPT_TEMPLATE = """Eres el migration-architect. El motor determinista de CodeArchaeologist ya ordenó las rutas
del repositorio por relación valor/riesgo para una migración Strangler Fig. Redactas UNA opción por
cada candidato de la lista, explicando cualitativamente por qué convendría (o no) empezar por él.

CANDIDATOS (datos, ordenados por el motor; el primero es el corte recomendado):
{candidates_json}

REGLAS ABSOLUTAS
- Devuelve exactamente {count} opciones, una por candidato, con su `endpoint` copiado literalmente.
- `finding_ids` solo puede contener IDs de `findings_mitigated` de ESE candidato (puede ir vacío).
- Exactamente UNA opción con recommended=true: la del endpoint {recommended_endpoint}.
- pros y cons son texto cualitativo. PROHIBIDO incluir números, porcentajes, códigos numéricos,
  estimaciones de días, semanas o meses ni cifras de ningún tipo.
- No inventes rutas, hallazgos, archivos ni métricas. No leas ni cites código: trabaja con estos datos.
- Redacta name, pattern, pros y cons en español.

FORMATO DE SALIDA
Tu mensaje final debe ser ÚNICAMENTE un objeto JSON válido (sin texto adicional, sin markdown)
que cumpla este esquema:
{schema_json}
"""

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def architect_settings() -> BobRunSettings:
    """Bounded settings for the architect: few turns, low cost, no subagents or MCP."""
    base = BobRunSettings.from_env()
    return base.model_copy(update={
        "max_turns": ARCHITECT_MAX_TURNS,
        "max_cost": min(base.max_cost, ARCHITECT_MAX_COST),
        "timeout_s": min(base.timeout_s, ARCHITECT_TIMEOUT_S),
        "disable_subagents": True,
        "disable_mcp": True,
    })


def top_candidates(dossier: Dossier) -> list[RouteCandidate]:
    """The engine's recommended cut first, then its alternatives (at most MAX_OPTIONS)."""
    recommendation = dossier.recommendation
    if recommendation is None or recommendation.recommended is None:
        return []
    return [recommendation.recommended, *recommendation.alternatives][:MAX_OPTIONS]


def _build_prompt(candidates: list[RouteCandidate], titles: dict[str, str]) -> str:
    data = [
        {
            "endpoint": candidate.endpoint,
            "why": candidate.why,
            "testability": candidate.testability,
            "tables_written": candidate.tables_written,
            "findings_mitigated": [{"id": fid, "title": titles.get(fid, "")} for fid in candidate.findings_mitigated],
        }
        for candidate in candidates
    ]
    schema = {
        "migration_options": {
            "type": "array",
            "items": MigrationOption.model_json_schema(),
            "minItems": len(candidates),
            "maxItems": len(candidates),
        }
    }
    return ARCHITECT_PROMPT_TEMPLATE.format(
        candidates_json=json.dumps(data, ensure_ascii=False, indent=2),
        count=len(candidates),
        recommended_endpoint=candidates[0].endpoint,
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


def _validate_options(options: list[dict[str, Any]], candidates: list[RouteCandidate]) -> list[MigrationOption]:
    """Valida las opciones con reglas deterministas; lanza ValueError con motivo si alguna falla."""
    parsed: list[MigrationOption] = []
    for raw in options:
        try:
            parsed.append(MigrationOption.model_validate(raw))
        except ValidationError as exc:
            raise ValueError(f"Opción inválida según el esquema: {exc}") from exc

    expected = len(candidates)
    if len(parsed) != expected:
        raise ValueError(f"Se esperaban exactamente {expected} opciones; llegaron {len(parsed)}.")
    if len({opt.id for opt in parsed}) != len(parsed):
        raise ValueError("Las opciones repiten su identificador.")

    # 1. Cada opción corresponde a un candidato distinto del motor
    by_endpoint = {candidate.endpoint: candidate for candidate in candidates}
    seen: set[str] = set()
    for opt in parsed:
        if opt.endpoint not in by_endpoint:
            raise ValueError(f"La opción {opt.id!r} usa un endpoint que no está en el ranking: {opt.endpoint!r}")
        if opt.endpoint in seen:
            raise ValueError(f"Dos opciones describen el mismo endpoint {opt.endpoint!r}.")
        seen.add(opt.endpoint)

    # 2. Solo hallazgos que ese candidato mitiga
    for opt in parsed:
        allowed = set(by_endpoint[opt.endpoint].findings_mitigated)
        unknown = set(opt.finding_ids) - allowed
        if unknown:
            raise ValueError(
                f"La opción {opt.id!r} cita hallazgos que {opt.endpoint} no mitiga: {sorted(unknown)}"
            )

    # 3. Prohibición de números en pros/cons
    for opt in parsed:
        for text in [*opt.pros, *opt.cons]:
            if _NUMBER_RE.search(text) or _WORD_ESTIMATE_RE.search(text):
                raise ValueError(f"La opción {opt.id!r} contiene cifras o porcentajes en pros/cons: {text!r}")

    # 4. Exactamente una recomendada, y es el corte que eligió el motor
    recommended = [opt for opt in parsed if opt.recommended]
    if len(recommended) != 1:
        raise ValueError(f"Debe haber exactamente una opción recomendada; se encontraron {len(recommended)}.")
    if recommended[0].endpoint != candidates[0].endpoint:
        raise ValueError(
            f"La opción recomendada ({recommended[0].endpoint!r}) no es el corte que eligió el motor "
            f"({candidates[0].endpoint!r})."
        )

    # Mismo orden que el ranking del motor
    order = {candidate.endpoint: index for index, candidate in enumerate(candidates)}
    return sorted(parsed, key=lambda opt: order[opt.endpoint or ""])


def run_migration_architect(dossier: Dossier, adapter: BobAdapter) -> tuple[list[MigrationOption], str]:
    """Invoca Bob en modo migration-architect y devuelve las opciones validadas.

    Returns:
        (options, reason): si la etapa tiene éxito, reason es ""; si falla, options es [] y reason
        describe el motivo (para registrar, no para mostrar al usuario como error fatal).
    """
    candidates = top_candidates(dossier)
    if not candidates:
        return [], "No hay rutas candidatas en el ranking; no hay nada que proponer al arquitecto."

    titles = {finding.id: finding.title for finding in dossier.findings}
    prompt = _build_prompt(candidates, titles)
    try:
        result = adapter.run(ARCHITECT_MODE, prompt)
    except BobError as exc:
        reason = f"Bob falló en migration-architect: {exc}"
        logger.warning(reason)
        return [], reason

    try:
        options = _validate_options(_extract_options(result.last_message), candidates)
    except (ValueError, json.JSONDecodeError) as exc:
        reason = f"Respuesta de migration-architect rechazada: {exc}"
        logger.warning(reason)
        return [], reason

    return options, ""
