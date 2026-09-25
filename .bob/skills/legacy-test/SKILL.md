---
name: legacy-test
description: Generate characterization tests that pin current behavior of a legacy endpoint.
metadata:
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '[endpoint-path] [--framework pytest|unittest]'
---

> Subagente principal: `contract-keeper` (ver `.bob/agents/contract-keeper.md`).

# Legacy Test Command

Generates black-box characterization tests (Golden Master) that pin down and freeze the observable behavior of a legacy endpoint before any migration or refactoring occurs.

## Usage

```bash
/legacy-test [/api/v1/endpoint] [--framework pytest]
```

## What This Command Does

1. **Endpoint Analysis**: Inspects the specified endpoint's route definition, parameters, and database queries.
2. **Generates Characterization Tests**: Dispatches `contract-keeper` to construct a comprehensive `pytest` test suite under `tests/characterization/`.
3. **Executes Baseline Run**: Executes `pytest tests/characterization/ -v` against the legacy application.
4. **Verifies 100% Pass Rate**: Confirms that all tests pass against current legacy behavior.
5. **Emits Test Manifest**: Outputs the list of frozen behavioral contracts ready for migration safety.

## Agents & Skills Used

- Agent: `contract-keeper`
- Skill: `characterization-testing`
- Rule: `.bob/rules/migration-safety.md`
