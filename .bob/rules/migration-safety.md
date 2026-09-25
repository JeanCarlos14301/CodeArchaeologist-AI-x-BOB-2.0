# Migration Safety Rules

Core invariants governing all code migration, test execution, and refactoring operations.

## The Six Invariants

1. **Never Migrate Without Characterization Tests First**
   - Writing modern code before establishing characterization tests is strictly prohibited.
   - Behavior must be pinned down before any architectural alteration occurs.

2. **Tests Must Pass Against Legacy Before Modern Coding Begins**
   - The test suite authored by `contract-keeper` must achieve a 100% pass rate against the existing legacy endpoint.
   - If tests fail against legacy, the assertions must be reconciled with reality.

3. **Modern Code Goes Exclusively Under `modern/`**
   - Legacy files are immutable during the initial Strangler Fig cut.
   - All FastAPI routes, Pydantic schemas, and facades must reside strictly under `modern/`.

4. **One Repair Attempt Maximum If Modern Tests Fail**
   - If characterization tests fail against the new modern service, the engineer agent is permitted exactly ONE repair iteration.
   - If the second run fails, stop execution immediately. Infinite retry loops are prohibited.

5. **Report Results Transparently**
   - Never suppress, hide, or fabricate test outcomes.
   - A failing migration cut with an accurate traceback diff is an honest engineering result.

6. **Decoupled Value of Deliverables**
   - Even if a migration cut encounters an unresolvable failure, the audit dossier, risk assessment, and executive board memo remain 100% valid deliverables.
