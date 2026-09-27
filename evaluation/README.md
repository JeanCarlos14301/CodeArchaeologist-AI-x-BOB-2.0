# Evaluation

- `expected-findings.json` is the curated **ground truth** for `samples/facturaya-v1`. It comes from
  [FacturaYa](https://github.com/JeanCarlos14301/FacturaYa) (`evaluation/expected-findings.json` in that
  repository), with evidence paths rewritten relative to the sample root (`app.py`, not
  `samples/facturaya-v1/app.py`) to match `evidence-auditor` citations.
- It contains seven entries: six with `expected_detection: true` and one (`EF-7`) with `false`, so the scorer
  measures false positives as well as recall.
- It is **NEVER passed to Bob** or included in any mode prompt or context. When building the sandbox,
  `evidence_audit.py` excludes `evaluation/` and `expected-findings*.json`.
- It is used only to measure `evidence-auditor` precision and recall (F-07).

## First measurement (informal, around H7, job `02833a24a7a7`)

The first real `live` `evidence-auditor` run on `facturaya-v1` (Jean, September 25, 2026 at 15:22; 120 s;
1.14 bobcoins), compared manually with `expected-findings.json`:

| Reference | Expected | Result |
|---|---|---|
| EF-1 SQL injection | detect | ✅ Detected and validated (`F-1`) |
| EF-2 long `invoice_new` function | detect | ✅ Detected and validated (`F-10`) |
| EF-3 duplicated discount logic | detect | ⚠️ Bob reported it (`F-5`), but the validator rejected half of the evidence because the `reports.py` snippet did not match the cited range; the finding did not enter the final dossier |
| EF-4 hardcoded secrets | detect | ✅ Detected and validated (`F-2`) |
| EF-5 circular dependency | detect | ✅ Detected and validated (`F-9`) |
| EF-6 invoice JSON IDOR | detect | ✅ Detected and validated (`F-3`) |
| EF-7 parameterized query (negative control) | do not detect | ✅ No false positive reported |

**Recall on validated findings: 5/6 (83%).** The EF-3 miss was not a discovery failure: Bob found and wrote
the issue, but its own citation did not match the code closely enough to pass stage 3. That is the intended
validator behavior (D7): rejecting a real issue with unsupported evidence is safer than accepting the claim.

Bob also reported seven findings outside this list: an invoice-number race, an N+1 monthly-report query, weak
hashing in `seed.py`, an invoice-count IDOR, money stored as SQLite `TEXT`, no tests, and inconsistent
`login_required` behavior. Each had a file-and-line citation verified by the validator. They are not in
`expected-findings.json` because it is a curated minimum, not an exhaustive truth set. They are not counted as
false positives without manual review, but the team should decide whether to add them to the ground truth.

## Automated measurement

```bash
python evaluation/score.py <dossier.json>      # exits 0 only when every expected issue is found and there are no false positives
```

An expected item is a hit when a **validated** finding overlaps its lines in the same file; rejected findings
do not count. The scorer is `evaluation/score.py`, with tests in `backend/tests/test_score.py`.

Using the real recorded Bob reply (`contracts/fixtures/bob-evidence-auditor-facturaya.json`) and validating it
against `samples/facturaya-v1` produces **6/6 and zero false positives**. The earlier **5/6** result above
(job `02833a24a7a7`) is not reproducible because its `dossier.json` is not versioned.

## Known gaps

- The 5/6 result from job `02833a24a7a7` cannot be reproduced until its credential-free `dossier.json` is added to
  `contracts/fixtures/`.
- The second `F-5` snippet did not match `reports.py`; a future change could adjust `LINE_TOLERANCE` or ask Bob for
  one representative evidence line instead of snippets containing `...`.
