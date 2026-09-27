# Historical correction plan — September 26

> This records the repository state at 20:00 (H10). Most items were later completed or superseded. It is not
> a current product specification.

## Findings at that time

Already working:

- No fake data remained in the interface.
- ZIP upload was real, secure, and token-protected.
- Architecture and blast radius were measured by code.
- Character encoding displayed accents correctly.
- 126 tests passed.

Release blockers:

1. Anyone could list uploaded jobs and read their code, graph, and dossier without a token.
2. Visitors without a token had no imported showcase, so every demo spent bobcoins.
3. Deliverables two and three—the board DOCX and tested first cut—were missing although the README promised them.
4. The README claimed four pillars and CBRS; `bob-usage.md` cited nonexistent files.
5. Zero of four required Bob session screenshots were on `main`.

Important issues:

6. PERT had been removed, although the memo needed effort ranges.
7. The proposed holdout was an identical copy of FacturaYa.
8. Legacy `/api/jobs` code remained, one timing test was flaky, requirements were not pinned, and `develop` still existed.
9. Decisions needed to be recorded from D22 because D13–D21 already existed.
10. Render and the 512 MB live mode had not been verified.

## Consolidated solution plan

### Block 0 · Security and public access

**S1. Close the privacy leak**

- Make `GET /api/audits` list registered samples only, unless a valid access token is present.
- Require the token for detail, source, graph, architecture, and files belonging to uploaded jobs.
- Have the frontend send the token and hide uploads when it is absent.
- Done when tests prove 403 without the token and 200 with it for every route.

**S2. Honest public showcase**

- Restore imported mode only for registered samples and replay the real September 25 run without a token.
- Label it `imported` with the original date.
- Offer one public showcase action and one live audit action.
- Done when a visitor can inspect the FacturaYa dossier, map, and architecture without spending bobcoins.

**S3. Repository hygiene**

- Commit Jean's screenshot.
- Record decisions D22–D27.
- Delete obsolete branches.

### Block 1 · Restore deliverables two and three

**E2a. Risk and effort from measured facts**

- Compute finding risk from severity × blast radius using graph callers.
- Compute first-cut PERT from affected routes, functions, lines, and complexity, with visible assumptions.
- Done when two repositories produce different figures and every figure shows its source.

**E2b. Code-verified Bob memo**

- Require every memo figure to exist in its input JSON; reject and retry once otherwise.
- If the retry fails, emit a clearly labeled data-only memo.
- Done when a test proves that an invented figure is rejected.

**E2c. DOCX from the real audit**

- Map real findings, risk, PERT, and memo data into the existing renderer.
- Add `board_memo.docx` to audit downloads.
- Remove LegacyLens, CBRS, and unsourced figures.
- Done when Word opens a document with the same job ID, hash, and mode as the web UI.

**E3a. Real tested first cut for registered samples only**

- Copy sample code to a sandbox.
- Apply the team's reference implementation.
- Run the characterization suite against legacy and modern code without credentials.
- Report each test as passed, failed, or not run. Never execute uploaded user code.
- Provide a downloadable diff.
- Done when intentionally breaking modern code produces a visible failed test.

**E3b. Minimal migration view**

- Show legacy and modern code side by side with real test results.
- Label it as the team's reference implementation, not Bob-generated code.
- Done when the view reflects failures as well as success.

Gate at H16: S1 and S2 complete, and a real audit downloads the DOCX even if its memo is still data-only.

### Block 2 · Truthfulness and stability

- Make the README describe only the three real deliverables and verify Quick Start from a clean clone.
- Back `bob-usage.md` entries with a result or screenshot, or mark them design-only.
- Use a genuinely independent holdout or remove the claim.
- Remove obsolete `/api/jobs` code, fix flaky tests, and pin requirements.
- Verify Render and run a live audit on the 512 MB plan; upgrade or record locally if memory is insufficient.
- Provide clear UI states for 403, 409, Bob failure, and a multi-minute live run; check phone width and dark mode.
- Put four credential-free, real-work Bob screenshots on `main`.

Gate at H24: real pytest first cut visible, verified DOCX memo, and truthful README.

### Block 3 · Freeze

- Pass the public acceptance journey three consecutive times.
- Tag v1.0 at H30. After the freeze, remove broken features instead of expanding scope.

### Block 4 · Submission

- Create an MP4 no longer than 3:00 with at least 90 seconds of the product working.
- Submit Long Description and IBM Bob Usage Statement at no more than 500 words each, using only backed claims.
- Submit before the internal cutoff and verify from another account.

If time runs out, cut scope in this order: holdout, Bob narrative in the memo, then UI-state polish. Never cut
privacy, the public showcase, the real DOCX, the pytest-backed first cut, or README truthfulness.

Optional only after everything else: three Bob architecture options, Bob-written tests/migration, and GitHub URL import.
