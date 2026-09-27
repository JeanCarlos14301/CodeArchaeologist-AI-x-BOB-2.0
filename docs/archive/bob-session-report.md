# Archived integration report: IBM Bob 2.0 × CodeArchaeologist

> Historical document only. The features claimed below were early proposals and do not all exist in the
> shipped product. Use `README.md` and `docs/bob-usage.md` as the current sources of truth.

**Author:** Felipe Gonzalez

**Date:** 2026-09-24

**Ecosystem version:** v1.1.0

**Task reference:** F-01 through F-14

**Decision record:** D1 through D17 in [docs/decisions.md](../decisions.md)

---

## 1. Executive summary of the proposed extension

This early design described a multi-agent infrastructure intended to turn IBM Bob 2.0 into a system for
**forensic auditing, polyglot modernization, shift-left pull-request risk control, and adversarial review**.

It followed the core rule from `AGENTS.md`:

> Risk, effort, and blast-radius figures are calculated by code, not AI.

The proposal paired Bob recommendations with deterministic Python tools including NetworkX, `ast`, PyDriller,
FastMCP, and DuckDB. Some of those ideas were later removed from the public product.

## 2. Four proposed pillars

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PROPOSED EXTENDED BOB 2.0 ARCHITECTURE                  │
├─────────────────────────┬─────────────────────────┬─────────────────────────────┤
│ 1. Shift-Left Risk Gate │ 2. Adversarial Tribunal │ 3. Code Archaeology         │
│    blast-radius-guard   │    code-skeptic        │    git-archaeologist        │
│    • Call graph         │    • Four-step debate  │    • PyDriller churn/bugs   │
│    • Transitive impact │    • No complacency    │    • AST / Tree-sitter      │
│    • CBRS score 0–100   │    • Binding verdicts │    • Mermaid ER diagrams    │
├─────────────────────────┴─────────────────────────┴─────────────────────────────┤
│ 4. FastMCP telemetry injection (telemetry-bridge)                               │
│    • DuckDB access-log analytics • Read-only SQLite snapshots                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Pillar 1: shift-left risk and blast-radius simulation

- **Goal:** protect human reviewer capacity from large volumes of autonomous-agent pull requests.
- **Proposed implementation:**
  - Code: `backend/app/pipeline/blast_radius.py`
  - Bob mode: `blast-radius-guard`
  - Skill: `.bob/skills/blast-radius-simulation/SKILL.md`
  - Command: `/risk-simulate`

### Pillar 2: adversarial multi-agent tribunals

- **Goal:** make AI challenge AI under strict evidence rules.
- **Proposed implementation:**
  - Prosecutor agent: `.bob/agents/code-skeptic.md`
  - Bob mode: `code-skeptic` against `migration-architect` / `polyglot-architect`
  - Skill: `.bob/skills/adversarial-tribunal/SKILL.md`
  - Command: `/code-tribunal`

### Pillar 3: code archaeology and AST cartography

- **Goal:** extract repository history through commits and syntax topology.
- **Proposed implementation:**
  - Git mining: `backend/app/extractors/git_archaeology.py`
  - AST cartography: `backend/app/extractors/ast_cartography.py`
  - Bob modes: `git-archaeologist`, `ast-cartographer`
  - Skills: `.bob/skills/git-archaeology/SKILL.md`, `.bob/skills/ast-analysis/SKILL.md`
  - Command: `/code-archaeology`

### Pillar 4: external telemetry injection through FastMCP

- **Goal:** connect Bob to production behavior without risking data or allowing unauthorized mutations.
- **Proposed implementation:**
  - Code: `backend/app/adapters/telemetry_mcp.py`
  - Connections: in-memory DuckDB / Parquet, read-only SQLite (`mode=ro`), and GitHub issues
  - Agent: `.bob/agents/telemetry-bridge.md`

## 3. Catalog claimed by the early report

| Component type | Count | Main location |
|---|---:|---|
| Specialized agents | 16 | `.bob/agents/*.md` |
| Skills | 13 | `.bob/skills/*/SKILL.md` |
| Slash commands | 10 | `.bob/skills/<command>/SKILL.md` |
| Bob Shell modes | 9 | `.bob/custom_modes.yaml` |
| Restricted contexts | 5 | `contexts/*.md` |
| Deterministic Python modules | 4 | `backend/app/pipeline/`, `backend/app/extractors/`, `backend/app/adapters/` |
| Architecture decisions | 17 | `docs/decisions.md` |
| Assigned Felipe tasks | 14 | historical task plan |

## 4. Validation status claimed by the early report

1. Python compilation completed without errors using `python3 -m py_compile`.
2. Pydantic 2.13.5, NetworkX 3.7, FastAPI 0.141.1, Uvicorn, and Pytest were installed and checked.
3. `pyrightconfig.json` and `.vscode/settings.json` were generated for editor type resolution.
4. The issue-creation script parsed the historical task table idempotently.

These statements are retained as historical claims, not current product acceptance evidence.
