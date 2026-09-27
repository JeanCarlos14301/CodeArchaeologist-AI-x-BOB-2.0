# Lablab.ai submission form

Field by field, in form order. **Deadline: Sunday, September 27, 2026, 11:00 a.m. ET (10:00 a.m. in
Colombia).** Recheck the event page before submitting in case the organizer changes the deadline.

| Field | Value | Status |
|---|---|---|
| **Project Title** | CodeArchaeologist | Ready |
| **Short Description** | See below | Ready |
| **Long Description** (≤ 500 words) | [long-description.md](long-description.md) | Ready; recount after any edit |
| **IBM Bob Usage Statement** (≤ 500 words) | [bob-usage-statement.md](bob-usage-statement.md) | Ready; recount after any edit |
| **Technology & Category Tags** | See below | Select from the form's available list |
| **Cover Image** | Pending | Create a 16:9 image with the name and an app screenshot, with no sensitive data |
| **Video Presentation** (MP4, ≤ 3:00) | Pending | Follow [video-script.md](video-script.md) |
| **Slide Presentation** | Pending | Follow [slides.md](slides.md) and export to PDF |
| **Public GitHub Repository** | https://github.com/JeanCarlos14301/CodeArchaeologist-AI-x-BOB-2.0 | Verify it is public and `main` contains the final release |
| **Demo Application Platform** | Render (single Docker container) | Ready |
| **Application URL** | `https://<service>.onrender.com` | Replace with the real URL from the `codearchaeologist` Render service |
| Bob session screenshots | `bob-sessions/<member>/` in the repository | Jean needs a task with nonzero cost; Edgar is missing; see [bob-sessions/README.md](../../bob-sessions/README.md) |

## Short Description

> Audits legacy systems with IBM Bob, verifies every finding by file and line, calculates what to migrate first,
> and produces a board-ready decision memo.

Shorter alternative if the form has a tighter limit:

> IBM Bob audits your legacy system; deterministic code decides what to migrate first, with evidence.

## Suggested tags

- **Technology:** IBM Bob, Python, FastAPI, React, TypeScript, Tailwind CSS, SQLite, Docker, Render.
- **Category:** Developer Tools, Legacy Modernization, Code Analysis, Enterprise, AI Agents.

Use only tags that exist in the form; do not invent unsupported categories.

## Live-access note

> The recorded FacturaYa audit opens without credentials and spends no bobcoins. Judges can also upload a ZIP,
> run a live IBM Bob audit, ask Bob, and use the Modernization Studio without an access token. Live actions use
> the server's configured Bob API key and are protected by per-run and daily spending limits.

Never put the API key in the form, repository, screenshots, or video. Deployment details are in
[public-app.md](public-app.md).
