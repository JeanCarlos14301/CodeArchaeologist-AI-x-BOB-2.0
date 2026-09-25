---
name: legacy-audit
description: Run a comprehensive legacy codebase audit with evidence-backed findings.
metadata:
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '[path-to-repo | demo | --depth fast|standard|deep]'
---

> Subagente principal: `legacy-archaeologist` (ver `.bob/agents/legacy-archaeologist.md`).

# Legacy Audit Command

Full forensic audit pipeline: reconnaissance → parallel domain analysis → evidence verification → structured dossier generation.

## Usage

```bash
/legacy-audit [path-to-repo | demo] [--depth fast|standard|deep]
```

## What This Command Does

1. **Reconnaissance**: Scans target repository, identifies entry points (`app.py`, `wsgi.py`), tech stack, dependencies, and database artifacts (`*.db`).
2. **Parallel Sub-Agent Delegation**:
   - `legacy-sql-auditor`: Inspects raw SQL, detects string interpolation vulnerabilities, infers database schema.
   - `legacy-route-mapper`: Maps all Flask routes, HTTP methods, input parameters, and authentication barriers.
   - `legacy-dependency-tracer`: Reconstructs internal import graph, detects circular imports, and computes blast radius.
   - `legacy-security-scanner`: Audits OWASP Top 10 vulnerabilities, hardcoded secrets, unsafe deserialization, and debug flags.
3. **Evidence Cross-Validation**:
   - Executes `legacy-evidence-validation` to verify that every finding cites an existing file, valid line coordinates, and exact matching snippets.
4. **Consolidation**:
   - Groups findings by category (`SECURITY`, `ARCHITECTURE`, `DATABASE`, `CODE_QUALITY`, `MAINTAINABILITY`) and severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
5. **Dossier Generation**:
   - Produces a machine-readable JSON dossier adhering to schema v1 and displays an executive summary.

## Agents Used

- `legacy-archaeologist` (Lead Coordinator)
- `legacy-sql-auditor`
- `legacy-route-mapper`
- `legacy-dependency-tracer`
- `legacy-security-scanner`

## Associated Skills & Rules

- Skill: `legacy-audit`
- Skill: `legacy-evidence-validation`
- Skill: `legacy-flask-patterns`
- Rules: `.bob/rules/evidence-standards.md`
- Rules: `.bob/rules/code-legacy-treatment.md`

## Output Deliverables

- Structured Technical Dossier in JSON format (ready for `/legacy-report` or frontend display).
- Summary table with findings count by severity and category.
- List of top 3 Strangler Fig migration candidate endpoints.
