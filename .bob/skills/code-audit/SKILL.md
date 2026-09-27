---
name: code-audit
description: Bob command that runs the evidence audit (`evidence-auditor` mode) on the input repository and emits the technical dossier in schema v1 (`contracts/schema-v1.json`).
metadata:
  user-invocable: true
  disable-model-invocation: true
---
# /code-audit

Bob command that runs the evidence audit (`evidence-auditor` mode) on the input repository and emits the technical dossier in schema v1 (`contracts/schema-v1.json`).

## Usage
```bash
bob run --mode evidence-auditor /code-audit <repo-path>
```

## Arguments
- `<repo-path>`: absolute or relative path to the directory of the repository to audit.
- `--depth`: depth level (`fast` | `standard` | `deep`). Default `standard`.

## Behavior
1. **Reconnaissance:** identifies the technical stack (Python, Flask, SQLite).
2. **Parallel delegation:**
   - SQL and injection audit (`legacy-sql-auditor`).
   - Route and authentication mapping (`legacy-route-mapper`).
   - Dependency tracing and import graph (`legacy-dependency-tracer`).
   - OWASP Top 10 vulnerability scan (`legacy-security-scanner`).
3. **Evidence validation:** filters out any claim without a real, verifiable file and line range.
4. **Output:** emits JSON that follows `contracts/schema-v1.json` with `execution_mode: "live"`, with every human-readable field in English.
