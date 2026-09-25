# Bob session screenshots (required deliverable)

The updated hackathon rules require the public repository to include screenshots of
**each team member's own** IBM Bob task session summaries — not just Felipe's, who owns
the Bob integration. This folder is tracked in git and is **not** listed in `.gitignore`.

## What goes here

One subfolder per person, each with at least one screenshot of a Bob session summary
taken from that person's own account:

- `jean/`
- `felipe/`
- `daniel/`
- `edgar/`

File naming: `YYYY-MM-DD_<short-task-id>.png` (e.g. `2026-09-26_D-02.png`).

## Before committing a screenshot

Per [SECURITY.md](../SECURITY.md), crop or blur anything that isn't the session summary
itself — in particular, no visible API key, token, or credential. `.bobignore` stops Bob
from *logging* credentials, but a screenshot can still capture one on screen; that's a
manual check.

This is separate from [bob-report/](../bob-report/), which holds Felipe's exported
technical report on the Bob integration itself, and from [docs/bob-usage.md](../docs/bob-usage.md),
which is the running log of sessions.
