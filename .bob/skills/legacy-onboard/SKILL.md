---
name: legacy-onboard
description: Understand, map, and document an unfamiliar legacy codebase for developers.
metadata:
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '[path-to-repo | .]'
---

> Subagente principal: `legacy-archaeologist` (ver `.bob/agents/legacy-archaeologist.md`).

# Legacy Onboard Command

Rapid architectural ramp-up and system briefing for legacy and undocumented repositories.

## Usage

```bash
/legacy-onboard [path-to-repo]
```

## What This Command Does

1. **Environmental Topology Scan**:
   - Identifies Python version, package manifests, and external runtime requirements.
   - Detects presence of local SQLite database files and configuration templates.
2. **Boundary & Route Discovery**:
   - Dispatches `legacy-route-mapper` to inventory all external HTTP entry points and handlers.
3. **Data Storage & Schema Inspection**:
   - Dispatches `legacy-db-inspector` and `legacy-sql-auditor` to outline primary tables and models.
4. **Architectural Danger Zones**:
   - Traces top circular dependencies and God modules using `legacy-dependency-tracer`.
5. **Generates Developer Briefing**:
   - Outputs a clean, actionable `LEGACY_BRIEFING.md` in the current working directory.

## Agents Used

- `legacy-archaeologist` (Coordinator)
- `legacy-route-mapper`
- `legacy-db-inspector`
- `legacy-dependency-tracer`

## Associated Skills

- `legacy-codebase-onboarding`
- `legacy-flask-patterns`
