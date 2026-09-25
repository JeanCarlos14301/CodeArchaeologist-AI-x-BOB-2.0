---
description: Mine version control history with PyDriller to uncover hotspots, churn, and author bus factor.
argument-hint: "[--since <date>] [--top <number>] [--author-risk]"
agent: git-archaeologist
---

# Code Archaeology Command (Git History & Churn Mining)

Performs deep archaeological mining on the git history of the repository using PyDriller and commit defect analysis.

## Usage

```bash
/code-archaeology --since 2023-01-01 --top 10
/code-archaeology --author-risk
```

## What This Command Does

1. **Commit Log Extraction**: Analyzes commit frequency, churn volume (insertions + deletions), and commit messages.
2. **Defect Hotspot Detection**: Flags files with high churn and recurring bug-fix commits.
3. **Temporal Coupling Identification**: Discovers unlinked files that co-change across commits, revealing hidden architectural entanglements.
4. **Knowledge Ownership & Bus Factor**: Measures author concentration across critical modules to identify orphaned systems.

## Agents Used

- `git-archaeologist` (Lead Mining Agent)
- `ast-cartographer`
- `telemetry-bridge`

## Associated Skills & Rules

- Skill: `git-archaeology`
- Skill: `ast-analysis`
- Rules: `rules/legacy-migration/code-legacy-treatment.md`
