# Rules for the `contract-keeper` mode

Bob Agent · Writes characterization tests (golden master with pytest) that pin the observable behavior of the endpoint chosen as the first cut. (Not used by the product: the reference cut's tests are versioned with the registered sample.)

- **Owner:** Felipe (F-02, F-05).
- **Equivalent ECC agent:** `.bob/agents/contract-keeper.md`.
- **Related skills:** `.bob/skills/characterization-testing/SKILL.md`.

## Scope and permissions
- **Read:** the legacy repository and the endpoint contracts.
- **Write:** STRICTLY RESTRICTED to `tests/characterization/`.
- **Execution:** `pytest` runs inside the controlled sandbox.

## Mandatory invariants
1. **Pin the real behavior:** the tests check what the legacy code really does (HTTP codes, JSON formats, errors), not what it "should" do.
2. **Green baseline:** the tests MUST pass 100% against the legacy system before the modern implementation starts.
3. **Database isolation:** use in-memory SQLite fixtures or temporary files (`tmp_path`) with fixed seed data.

## Output example
```json
{
  "execution_mode": "live",
  "test_file": "tests/characterization/test_first_cut.py",
  "total_tests": 4,
  "legacy_pass_rate": 100.0,
  "pinned_behaviors": [
    "GET /users/1 -> HTTP 200 with keys {'id', 'name'}",
    "GET /users/999 -> HTTP 404 with key {'error'}",
    "GET /users/abc -> HTTP 400"
  ]
}
```
