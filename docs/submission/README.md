# IBM Bob 2.0 Hackathon submission

Everything lablab.ai asks for, with its status and where it lives. **Deadline: Sunday, September 27, 2026,
11:00 a.m. ET.**

## Documents in this folder

| File | What for |
|---|---|
| [submission-form.md](submission-form.md) | Every field of the form with its value and status |
| [long-description.md](long-description.md) | *Long Description* (≤ 500 words) |
| [bob-usage-statement.md](bob-usage-statement.md) | *IBM Bob Usage Statement* (≤ 500 words) |
| [video-script.md](video-script.md) | Script of the 3:00 video with 130 s of demo |
| [slides.md](slides.md) | Outline of the 9 slides |
| [public-app.md](public-app.md) | How the app is published for the judges: API key, open access, bobcoin caps and smoke test |

## Checklist

### Repository
- [x] Public, MIT license (`LICENSE`), created from the [official template](https://github.com/watsonxhackathon/ibm-hackathon-template); `.gitignore` and `.bobignore` unmodified.
- [x] `SECURITY.md` present; credentials only in environment variables.
- [x] Product code, UI, Bob prompts, tests and current docs are in English; raw historical recordings are retained only as input evidence (D41).
- [x] README: problem, solution, Bob usage, architecture, how to evaluate, security and limitations.
- [x] Earlier material that does not describe the product, archived in [docs/archive/](../archive/).
- [x] Decisions up to date (`docs/decisions.md`, up to D41) and Bob log (`docs/bob-usage.md`).
- [ ] Final credential review: `git log -p | grep -iE "api[_-]?key|token|secret"` with no real values; screenshots with no sensitive data.
- [ ] `main` holding the final version (merge this branch's PR) and the `develop` branch deleted or up to date.

### Bob session screenshots (at least one per team member)
- [x] Felipe: `bob-sessions/felipe/` (terminal with the task summary, and the live session in the app).
- [ ] Daniel: the current screenshots have a paid task summary, but the run stopped at its turn limit with zero assistant messages. Add a completed run with Bob's final answer.
- [ ] Jean: the current screenshot shows a task with 0 bobcoins. Add one of a real session (with cost).
- [ ] Edgar: empty folder. The screenshot is missing.

How to take them: [bob-sessions/README.md](../../bob-sessions/README.md).

### Public app
- [ ] Render URL working and pasted in the README and in the form.
- [ ] Daniel's `BOB_API_KEY` loaded in Render, and his account's budget checked.
- [ ] `LIVE_AUDIT_TOKEN` deleted from Render → Environment if it was created by the earlier blueprint (open mode).
- [ ] `render.yaml` caps applied (they sync when merging into `main`), including `BOB_DAILY_SPEND_LIMIT`.
- [ ] Uptime monitor or Starter plan during judging.
- [ ] The [public-app.md](public-app.md#7-smoke-test-before-submitting) smoke test passed from an incognito window.

### Form material
- [x] Title, short description, long description and Bob usage statement.
- [ ] Cover image.
- [ ] MP4 video ≤ 3:00, narrated, with ≥ 90 s of demo.
- [ ] Slides (PDF).
- [ ] Form submitted and checked from another account.

## Judging criteria and where they show

| Criterion | Where it shows |
|---|---|
| Application of Technology | Bob in 5 product modes, parallel subagents, live activity, session rescue (`docs/bob-usage.md`) |
| Presentation | Video, slides and the public showcase with no credentials |
| Business Value | Board memo, migration recommendation with PERT, tested first cut |
| Originality | The AI proposes and code decides: line-by-line validated evidence and an auditable deterministic ranking |
