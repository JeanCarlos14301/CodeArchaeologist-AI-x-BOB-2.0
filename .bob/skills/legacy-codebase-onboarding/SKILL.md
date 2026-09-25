---
name: legacy-codebase-onboarding
description: >
  Specialized onboarding workflow for legacy codebases. Combines technical 
  inventory, debt assessment, risk profiling, and architectural understanding 
  to ramp up engineers on undocumented systems.
metadata:
  origin: CodeArchaeologist
---

# Legacy Codebase Onboarding

A structured workflow to rapidly understand, map, and document an undocumented or aging legacy codebase without getting trapped in obscure rabbit holes.

## When to Use

- When an engineer or team takes ownership of an undocumented legacy project.
- When running the `/legacy-onboard` command.
- Before beginning refactoring or migration planning to ensure full system understanding.
- To produce a developer briefing and architecture summary.

## Onboarding Phases

```
┌─────────────────────────────────┐
│ 1. Runtime & Environment Survey │ ── Python version, dependencies, configs, entry scripts
└───────────────┬─────────────────┘
                │
┌───────────────▼─────────────────┐
│ 2. System Boundaries & I/O      │ ── HTTP routes, CLI scripts, background jobs, external APIs
└───────────────┬─────────────────┘
                │
┌───────────────▼─────────────────┐
│ 3. Data Model & Persistence     │ ── SQLite tables, schemas, relations, migrations
└───────────────┬─────────────────┘
                │
┌───────────────▼─────────────────┐
│ 4. Fragility & Hotspot Mapping  │ ── God classes, circular imports, high complexity modules
└───────────────┬─────────────────┘
                │
┌───────────────▼─────────────────┐
│ 5. Developer Briefing Synthesis │ ── Actionable summary with quickstart and risk warnings
└─────────────────────────────────┘
```

### Phase 1: Runtime & Environment Survey
1. Locate dependency manifests:
   - Examine `requirements.txt` or `Pipfile`.
   - Check for obsolete libraries (e.g. `Flask<1.0`, `Werkzeug<1.0`, deprecated crypto packages).
2. Inspect environment variables and configuration loading:
   - Identify expected environment variables (`.env.example`, `config.py`).
   - Check if database file paths are hardcoded or configurable.

### Phase 2: System Boundaries & I/O
1. Trace primary entry points:
   - How does the application boot? (`python app.py`, `flask run`, `gunicorn wsgi:app`).
2. Catalog external communication:
   - HTTP routes exposed to users or internal services.
   - Outgoing HTTP calls (`requests.get`, `urllib`).
   - File system reading/writing (e.g. writing PDF reports, reading CSVs).

### Phase 3: Data Model & Persistence
1. Locate database schema:
   - Check for SQL setup files (`schema.sql`, `init.sql`).
   - If missing, check `legacy-db-inspector` findings for inferred schema.
2. Identify core entities:
   - What are the primary tables? (e.g. `users`, `orders`, `transactions`).
   - How are relations managed? (Foreign keys vs application-level conventions).

### Phase 4: Fragility & Hotspot Mapping
1. Identify high-risk modules:
   - Which files have the highest cyclomatic complexity or line count?
   - Are there circular dependencies or shared mutable singletons?
2. Note missing safety nets:
   - Check for existing test suites (`tests/`, `pytest.ini`). If absent, flag system as unprotected.

### Phase 5: Developer Briefing Synthesis
Generate a succinct `LEGACY_BRIEFING.md` summarizing:
- **System Purpose**: What the application actually does in 2 sentences.
- **Tech Stack Snapshot**: Python version, framework, persistence layer.
- **Safe Zones vs Danger Zones**: Modules that can be touched safely vs fragile core bottlenecks.
- **Immediate Gotchas**: Hidden traps, unparameterized queries, global state quirks.

## Output Format

```markdown
# Legacy System Briefing: [Application Name]

## Executive Summary
This application is a monolithic Flask 1.1 system managing order processing and SQLite data storage.

## Key Topology
- **Entry Point**: `app.py`
- **Primary Routes**: 8 endpoints defined in `routes/`
- **Database**: SQLite file located at `data/app.db` (inferred 4 tables)
- **Test Coverage**: 0% (no automated test suite present)

## Danger Zones (Handle With Care)
1. `models/db_helper.py`: Shared global SQLite connection; prone to thread locks.
2. `routes/checkout.py`: 400-line route function executing raw SQL within nested loops.

## Recommended Next Steps
1. Run `/legacy-audit` to catalog security and debt findings.
2. Run `/legacy-test` on `/api/checkout` to generate characterization tests before modifications.
```

## Best Practices

- **Start Breadth-First**: Map the entire perimeter before diving into single functions.
- **Prioritize Verifiable Signals**: Focus on executable entry points and actual route bindings rather than comments or documentation which may be years out of date.
