# Legacy Migration Context

Mode: Controlled code generation & test verification
Focus: Strangler Fig first cut with characterization test safety net

## Behavior
- **Characterization Tests FIRST**: Never write modern replacement code before locking down observable behavior with golden-master characterization tests.
- **Legacy Baseline Pass**: Characterization tests MUST pass against the legacy endpoint before any migration code is drafted.
- **Strict Directory Sandboxing**: All new modernized code must be written strictly under `modern/` (or the configured modern target directory). Never overwrite legacy files in-place during the initial cut.
- **One Repair Attempt Maximum**: If modernized code fails the characterization tests, only one structured repair iteration is permitted to prevent non-terminating loops.
- **Radical Transparency**: Report results honestly. If the cut fails, provide full pytest traceback evidence and keep the audit/plan deliverables intact.

## Priorities
1. **Safety**: Behavioral parity verified by passing characterization tests.
2. **Correctness**: Preserving edge cases, status codes, and exact response bodies.
3. **Cleanliness**: Modern Python 3.11+, FastAPI, Pydantic v2 schemas, type annotations.

## Tools to Favor
- `Write` & `Edit` for creating test files under `tests/characterization/` and new modules under `modern/`.
- `Bash` for running `pytest` test suites inside the sandbox.
- `Read` for inspecting the legacy implementation and contracts.
