---
name: legacy-report
description: Generate executive report (DOCX/HTML) from validated audit findings.
metadata:
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '[--format docx|html|both] [--audience board|technical]'
---

> Subagente principal: `board-narrator` (ver `.bob/agents/board-narrator.md`).

# Legacy Report Command

Generates polished executive board memorandums and technical audit dossiers in Markdown, HTML, and DOCX formats.

## Usage

```bash
/legacy-report [--format docx|html|both] [--audience board|technical]
```

## What This Command Does

1. **Ingests Validated Audit Data**:
   - Reads findings from the most recent `/legacy-audit` execution.
   - Extracts PERT timelines from `/legacy-risk`.
   - Incorporates characterization test results from `/legacy-migrate`.
2. **Drafts Executive Narrative**:
   - Dispatches `board-narrator` to transform technical data into an authoritative, C-level executive memorandum.
3. **Applies Style & Governance Guidelines**:
   - Enforces `board-memo-writing` standards: zero figure invention, bottom-line upfront, and strategic risk articulation.
4. **Builds Output Deliverable**:
   - Generates standalone Markdown/HTML summary or invokes the python-docx generator (`backend/renderers/`) to produce the final `.docx` document.

## Agents & Skills Used

- Agent: `board-narrator`
- Skill: `board-memo-writing`
- Rule: `.bob/rules/evidence-standards.md`
