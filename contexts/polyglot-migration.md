# Polyglot Migration Context

Mode: Cross-stack and cross-framework translation
Focus: Behavioral equivalence, type safety, Strangler Fig facade isolation

## Behavior
- **Never perform big-bang rewrites**: All migrations must be sliced into granular, independently deployable cuts.
- **Contract-first execution**: Before writing target code, freeze the OpenAPI contract and run characterization tests against the source system.
- **Idiomatic target patterns**: Do not mechanically translate syntax; adopt the idiomatic conventions of the target ecosystem (e.g. NestJS dependency injection, TypeScript strict null checks).
- **Dual-run validation**: Validate that output JSON structures and HTTP response codes match with zero variance across both implementations.

## Priorities
1. **Behavioral fidelity over speed**: Ensuring zero regression takes precedence over rapid feature parity.
2. **Deterministic type mapping**: Preserve precision, validation boundaries, and error codes.
3. **Observability**: Maintain consistent trace headers across legacy and modern services during the coexistence phase.
