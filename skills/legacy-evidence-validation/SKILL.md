---
name: legacy-evidence-validation
description: >
  Verifies that every finding in a technical dossier cites real files, valid 
  line ranges, and verbatim snippets. Guarantees 100% verifiable evidence.
metadata:
  origin: CodeArchaeologist
---

# Legacy Evidence Validation

A verification skill to ensure that every finding produced by audit agents is mathematically and textually grounded in the analyzed repository.

## When to Use

- Before accepting any sub-agent finding into a technical dossier or report.
- During automated pipeline validation gates (Task D-06 / F-03).
- When filtering hallucinated line references or obsolete file paths.
- To enforce the zero-fabrication invariant required by board-level dossiers.

## Verification Pipeline

```
Raw Finding
     │
     ▼
[Step 1: Path Integrity & Existence]
  - No path traversal (../), no symlinks outside root
  - File exists in repository
     │ Pass
     ▼
[Step 2: Line Boundary Bounds Check]
  - 1 <= line_start <= line_end <= total_lines_in_file
     │ Pass
     ▼
[Step 3: Snippet Grounding Check]
  - Text at line_start..line_end contains/matches snippet
     │ Pass
     ▼
[Step 4: Epistemic Classification]
  - Tagged as 'observed' (direct text) or 'inferred' (call trace)
     │ Pass
     ▼
Validated Finding (Ready for Dossier)
```

## Detailed Verification Steps

### Step 1: Path Integrity & Existence Check
1. Strip leading slashes and normalize relative path:
   `os.path.normpath(evidence.file)`
2. Ensure path does not escape the repository boundary:
   Reject if path starts with `..` or references absolute system paths (`/etc/`, `/tmp/`).
3. Check filesystem existence:
   File must exist in the analyzed directory snapshot.

### Step 2: Line Range Bounds Check
1. Read the target file and count total lines ($N$).
2. Validate:
   - $1 \le \text{line\_start} \le N$
   - $\text{line\_start} \le \text{line\_end} \le N$
   - Maximum range sanity: if a single snippet spans $> 100$ lines without clear justification, flag for review.

### Step 3: Verbatim Snippet Grounding
1. Extract lines between `line_start` and `line_end` (inclusive).
2. Compare the recorded `snippet` against the extracted source lines.
3. Normalize whitespace (strip trailing carriage returns/spaces).
4. If the snippet does not match the file content, the finding is **REJECTED** as a hallucination or stale reference.

### Step 4: Epistemic Status Tagging
Ensure finding explicitly labels the mode of observation:
- `observed`: The vulnerability or anti-pattern is directly visible in the specified snippet (e.g., `f"SELECT * FROM users WHERE id = {user_id}"`).
- `inferred`: The finding is deduced from the combination of multiple components (e.g., an endpoint is unprotected because no auth middleware is mounted in `app.py`). Inferred findings must include the reasoning chain.

## Validation Output Format

```json
{
  "total_findings_evaluated": 15,
  "validated_count": 14,
  "rejected_count": 1,
  "rejection_log": [
    {
      "finding_id": "FINDING-SQL-009",
      "reason": "LINE_OUT_OF_BOUNDS",
      "details": "File 'legacy/models.py' has 85 lines, but evidence cited line_start=110."
    }
  ],
  "validation_status": "PASSED_WITH_CORRECTIONS"
}
```

## Best Practices

- **Automate with Python**: Use deterministic scripts to validate evidence whenever possible, not LLM self-evaluation.
- **Fail Closed**: If a file cannot be found or lines cannot be confirmed, reject the evidence immediately.
- **Trim Snippets Cleanly**: Ensure snippets only include the minimum context necessary to prove the finding.
