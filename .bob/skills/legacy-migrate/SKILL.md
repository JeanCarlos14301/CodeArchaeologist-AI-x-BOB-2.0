---
name: legacy-migrate
description: Execute first migration cut using Strangler Fig pattern with characterization tests.
metadata:
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '[endpoint-path | --auto-select]'
---

> Subagente principal: `migration-architect` (ver `.bob/agents/migration-architect.md`).

# Legacy Migrate Command

Executes an end-to-end incremental migration of a selected legacy endpoint using the Strangler Fig pattern, protected by golden-master characterization tests.

## Usage

```bash
/legacy-migrate [--auto-select | /api/v1/endpoint]
```

## What This Command Does

1. **Endpoint Selection**:
   - Dispatches `migration-architect` to select the optimal First Cut based on blast radius, isolation, and business value (or uses user-provided endpoint).
2. **Behavioral Characterization**:
   - Dispatches `contract-keeper` to generate pytest characterization tests in `tests/characterization/test_first_cut.py`.
   - Runs tests against the legacy endpoint to establish 100% green baseline.
3. **Modern Implementation**:
   - Dispatches `strangler-surgeon` to implement the endpoint in FastAPI with Python 3.11+ type hints, Pydantic v2 schemas, and safe parameterized queries exclusively under `modern/`.
   - Mounts the Strangler Fig routing facade.
4. **Parity Validation & Repair**:
   - Dispatches `migration-validator` to execute tests against both systems.
   - If tests fail, `strangler-surgeon` executes at most one targeted repair attempt.
5. **Certification**:
   - Emits migration certificate JSON and summary report.

## Agents Used

- `migration-architect`
- `contract-keeper`
- `strangler-surgeon`
- `migration-validator`

## Associated Skills & Rules

- Skill: `strangler-fig-migration`
- Skill: `characterization-testing`
- Rules: `.bob/rules/migration-safety.md`
