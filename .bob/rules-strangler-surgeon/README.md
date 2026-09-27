# Rules for the `strangler-surgeon` mode

Bob Agent · Implements the first migration cut in FastAPI behind a Strangler Fig facade, making sure the characterization tests pass against both systems. (Not used by the product: the Modernization Studio uses `modernization-surgeon`.)

- **Owner:** Felipe (F-02, F-06).
- **Equivalent ECC agent:** `.bob/agents/strangler-surgeon.md` and `.bob/agents/migration-validator.md`.
- **Related skills:** `.bob/skills/strangler-fig-migration/SKILL.md`.

## Scope and permissions
- **Read:** the legacy repository and the tests in `tests/characterization/`.
- **Write:** STRICTLY RESTRICTED to the `modern/` folder. Do not modify the legacy system's original files.
- **Execution:** `pytest` runs on the sandbox.

## Invariants and constraints
1. **Modern conventions:** Python 3.11+, full type annotations, Pydantic v2 schemas, parameterized SQL queries.
2. **At most 1 repair attempt:** if the characterization tests fail against the modern implementation, a single repair attempt is allowed. If the second attempt fails, abort and document the failure honestly.
3. **Strangler Fig facade:** route the modern endpoint to FastAPI and keep every other route delegated to Flask.

## Output example
```json
{
  "execution_mode": "live",
  "files_created": [
    "modern/routes/users.py",
    "modern/schemas/user.py",
    "modern/main.py"
  ],
  "characterization_status": "PASSED",
  "repair_attempts": 0
}
```
