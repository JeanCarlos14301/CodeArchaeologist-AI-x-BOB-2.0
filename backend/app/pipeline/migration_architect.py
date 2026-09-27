"""migration-architect stage: Bob writes 3 migration options over the ROUTE ranking.

The deterministic engine (migration_ranking.py) has already picked the first cut by value/risk (D3).
Bob receives the top candidates as DATA (endpoint, measured justification and the findings each one
mitigates) and writes one option per candidate: name, pattern, qualitative pros and cons. It receives no
source code and produces no figures: days, risk and scores are computed by code.

Validator guarantees:
- One option per candidate, with that candidate's exact `endpoint` and no repeats.
- `finding_ids` may only cite findings that candidate mitigates according to the engine.
- No figures, percentages or estimates in words inside pros/cons.
- Exactly one recommended option, and it must be the cut the engine picked: Bob explains the
  decision, it does not contradict it.
- Fallback: if Bob fails or the reply is rejected, migration_options stays empty and the reason is
  recorded. It is never filled with templates.
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

# Detects any number (integer or decimal) or percent sign in a string.
_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b|%")
# Estimates written in words ("two weeks", "three months"): not allowed either (English and Spanish).
_WORD_ESTIMATE_RE = re.compile(
    r"\b(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten|twelve|twenty|thirty|hundred|thousand|"
    r"un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|veinte|treinta|cien|mil)\s+"
    r"(?:days?|weeks?|months?|hours?|d[ií]as?|semanas?|meses|horas?|sprints?)\b",
    re.IGNORECASE,
)

ARCHITECT_PROMPT_TEMPLATE = """You are the migration-architect. The CodeArchaeologist deterministic engine has already ranked the
repository's routes by value/risk for a Strangler Fig migration. You write ONE option for
each candidate in the list, explaining qualitatively why starting with it would (or would not) pay off.

CANDIDATES (data, ordered by the engine; the first one is the recommended cut):
{candidates_json}

ABSOLUTE RULES
- Return exactly {count} options, one per candidate, with its `endpoint` copied verbatim.
- `finding_ids` may only contain IDs from THAT candidate's `findings_mitigated` (it may be empty).
- Exactly ONE option with recommended=true: the one for the endpoint {recommended_endpoint}.
- pros and cons are qualitative text. Do NOT include numbers, percentages, numeric codes,
  estimates in days, weeks or months, or figures of any kind.
- Do not invent routes, findings, files or metrics. Do not read or cite code: work with this data.
- Write name, pattern, pros and cons in English.

OUTPUT FORMAT
Your final message must be ONLY a valid JSON object (no extra text, no markdown)
that follows this schema:
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
    """Gets the list of options from the JSON in Bob's reply."""
    fenced = _FENCE_RE.search(message)
    raw = fenced.group(1) if fenced else message[message.find("{") : message.rfind("}") + 1]
    if not raw:
        raise ValueError("Bob's reply contains no JSON.")
    data = json.loads(raw)
    if isinstance(data, dict) and "migration_options" in data:
        return data["migration_options"]
    raise ValueError("The JSON has no 'migration_options' key.")


def _validate_options(options: list[dict[str, Any]], candidates: list[RouteCandidate]) -> list[MigrationOption]:
    """Validates the options with deterministic rules; raises ValueError with the reason if one fails."""
    parsed: list[MigrationOption] = []
    for raw in options:
        try:
            parsed.append(MigrationOption.model_validate(raw))
        except ValidationError as exc:
            raise ValueError(f"Option invalid under the schema: {exc}") from exc

    expected = len(candidates)
    if len(parsed) != expected:
        raise ValueError(f"Expected exactly {expected} options; got {len(parsed)}.")
    if len({opt.id for opt in parsed}) != len(parsed):
        raise ValueError("The options repeat their identifier.")

    # 1. Each option matches a different engine candidate
    by_endpoint = {candidate.endpoint: candidate for candidate in candidates}
    seen: set[str] = set()
    for opt in parsed:
        if opt.endpoint not in by_endpoint:
            raise ValueError(f"Option {opt.id!r} uses an endpoint that is not in the ranking: {opt.endpoint!r}")
        if opt.endpoint in seen:
            raise ValueError(f"Two options describe the same endpoint {opt.endpoint!r}.")
        seen.add(opt.endpoint)

    # 2. Only findings that candidate mitigates
    for opt in parsed:
        allowed = set(by_endpoint[opt.endpoint].findings_mitigated)
        unknown = set(opt.finding_ids) - allowed
        if unknown:
            raise ValueError(
                f"Option {opt.id!r} cites findings that {opt.endpoint} does not mitigate: {sorted(unknown)}"
            )

    # 3. No numbers in pros/cons
    for opt in parsed:
        for text in [*opt.pros, *opt.cons]:
            if _NUMBER_RE.search(text) or _WORD_ESTIMATE_RE.search(text):
                raise ValueError(f"Option {opt.id!r} contains figures or percentages in pros/cons: {text!r}")

    # 4. Exactly one recommended option, and it is the cut the engine picked
    recommended = [opt for opt in parsed if opt.recommended]
    if len(recommended) != 1:
        raise ValueError(f"There must be exactly one recommended option; found {len(recommended)}.")
    if recommended[0].endpoint != candidates[0].endpoint:
        raise ValueError(
            f"The recommended option ({recommended[0].endpoint!r}) is not the cut the engine picked "
            f"({candidates[0].endpoint!r})."
        )

    # Same order as the engine's ranking
    order = {candidate.endpoint: index for index, candidate in enumerate(candidates)}
    return sorted(parsed, key=lambda opt: order[opt.endpoint or ""])


def run_migration_architect(dossier: Dossier, adapter: BobAdapter) -> tuple[list[MigrationOption], str]:
    """Invokes Bob in migration-architect mode and returns the validated options.

    Returns:
        (options, reason): on success reason is ""; on failure options is [] and reason
        describes why (to be recorded, not shown to the user as a fatal error).
    """
    candidates = top_candidates(dossier)
    if not candidates:
        return [], "There are no candidate routes in the ranking; nothing to propose to the architect."

    titles = {finding.id: finding.title for finding in dossier.findings}
    prompt = _build_prompt(candidates, titles)
    try:
        result = adapter.run(ARCHITECT_MODE, prompt)
    except BobError as exc:
        reason = f"Bob failed in migration-architect: {exc}"
        logger.warning(reason)
        return [], reason

    try:
        options = _validate_options(_extract_options(result.last_message), candidates)
    except (ValueError, json.JSONDecodeError) as exc:
        reason = f"migration-architect reply rejected: {exc}"
        logger.warning(reason)
        return [], reason

    return options, ""
