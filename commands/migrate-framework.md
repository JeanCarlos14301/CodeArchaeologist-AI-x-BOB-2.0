---
description: Plan and execute cross-stack framework migrations (e.g. FastAPI → NestJS, monolith → microservices).
argument-hint: "[--source <framework>] [--target <framework>] [--cut <endpoint/module>]"
agent: polyglot-migration-planner
---

# Migrate Framework Command

Orchestrates multi-language and cross-framework migration planning and execution without behavioral regressions.

## Usage

```bash
/migrate-framework --source fastapi --target nestjs [--cut /api/v1/orders]
/migrate-framework --source flask --target express [--cut /auth]
/migrate-framework --source monolith --target microservices [--service billing]
```

## What This Command Does

1. **Stack Fingerprinting**: Analyzes source codebase version, framework dependencies, async patterns, and validation libraries.
2. **Concept Mapping**: Produces a rigorous translation mapping for models, routes, dependency injection, and middleware.
3. **Contract Extraction**: Generates OpenAPI specifications and pytest/jest characterization tests capturing exact status codes and JSON payloads.
4. **Strangler Fig Facade**: Configures routing gateway to seamlessly divert migrated traffic to the new target framework service.
5. **Dual-Run Parity Verification**: Runs differential tests across both systems to confirm zero regressions.

## Agents Used

- `polyglot-migration-planner` (Lead Coordinator)
- `migration-architect`
- `strangler-surgeon`
- `contract-keeper`
- `ast-cartographer`

## Associated Skills & Rules

- Skill: `polyglot-migration`
- Skill: `characterization-testing`
- Skill: `strangler-fig-migration`
- Rules: `rules/legacy-migration/migration-safety.md`
