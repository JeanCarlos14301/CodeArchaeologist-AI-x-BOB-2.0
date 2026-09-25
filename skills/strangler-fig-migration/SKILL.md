---
name: strangler-fig-migration
description: >
  Step-by-step methodology for executing incremental Strangler Fig migrations 
  from legacy Flask to modern FastAPI systems, protected by characterization tests.
metadata:
  origin: CodeArchaeologist
---

# Strangler Fig Migration Pattern

A safe, incremental migration methodology that gradually replaces legacy system components with modern services behind an interception facade, eliminating high-risk "big bang" rewrites.

## When to Use

- When migrating legacy Flask/Python applications to modern FastAPI/Python 3.11+.
- When executing the `/legacy-migrate` command.
- When extracting individual high-value or high-risk endpoints safely.
- When business operations require zero downtime and backwards compatibility.

## The Strangler Fig Lifecycle

```
[Incoming Request]
        │
        ▼
┌─────────────────────────────────┐
│     Strangler Fig Facade        │
└───────────────┬─────────────────┘
                │
         Is route migrated?
          /           \
     YES /             \ NO (Fallback)
        ▼               ▼
┌──────────────┐  ┌──────────────┐
│ Modern App   │  │ Legacy App   │
│ (FastAPI)    │  │ (Flask)      │
│ modern/      │  │ legacy/      │
└──────────────┘  └──────────────┘
```

### Phase 1: Candidate Selection & Interception Design
1. Analyze candidate endpoints scored by `legacy-route-mapper` and `legacy-dependency-tracer`.
2. Select an endpoint meeting the target risk profile (typically a leaf or discrete API endpoint).
3. Design the routing facade (e.g. FastAPI middleware, ASGI dispatcher, or reverse proxy rule).

### Phase 2: Behavioral Characterization
1. **Invariant**: Never write modern replacement code without characterization tests.
2. Generate golden master tests capturing:
   - Status codes for valid, invalid, and boundary inputs.
   - Exact JSON schemas, keys, and response formatting.
   - Database side effects.
3. Verify that 100% of characterization tests pass against the legacy endpoint.

### Phase 3: Modern Implementation in Sandboxed Target
1. Create new modern code exclusively inside `modern/`.
2. Use modern patterns:
   - Python 3.11+ type annotations.
   - Pydantic v2 data validation models.
   - Safe, parameterized database interactions.
3. Configure the facade to route requests matching the migrated endpoint pattern to the new FastAPI handler, forwarding all other traffic to legacy.

### Phase 4: Parity Validation & Repair
1. Run the characterization test suite against the modern endpoint.
2. If tests fail, diagnose the failure and execute at most **one repair attempt**.
3. If tests pass, certify the migration cut.
4. If the repair attempt fails, abort cleanly, log the error report, and keep the legacy route active.

### Phase 5: Decommissioning (Post-Cutover)
Once the modern endpoint operates stably in production:
1. Mark the legacy route handler as deprecated.
2. After confidence window passes, remove dead legacy code and update documentation.

## Best Practices

- **Never Overwrite In-Place**: Keep legacy code untouched so rollback is an instantaneous configuration toggle.
- **Strict One-Cut Scope**: Migrate one endpoint at a time. Do not attempt to refactor adjacent models during the same cut.
- **Preserve Quirks Intentionally**: If legacy returns `{"status": "ok"}` with HTTP 200 on an empty list, the modern service must return the exact same response until an intentional contract change is approved.
