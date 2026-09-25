"""Genera `contracts/schema-v1.json` desde los modelos Pydantic: `python -m app.contracts.export`."""

import json
from pathlib import Path

from app.contracts.schema_v1 import AuditorOutput, Dossier

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_DIR = REPO_ROOT / "contracts"


def build_schema_document() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CodeArchaeologist contract v1",
        "dossier": Dossier.model_json_schema(),
        "auditor_output": AuditorOutput.model_json_schema(),
    }


def main() -> None:
    target = CONTRACTS_DIR / "schema-v1.json"
    target.write_text(json.dumps(build_schema_document(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Esquema escrito en {target}")


if __name__ == "__main__":
    main()
