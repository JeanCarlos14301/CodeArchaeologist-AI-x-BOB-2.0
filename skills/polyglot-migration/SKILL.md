---
name: polyglot-migration
description: >
  Systematic methodology for cross-stack, cross-framework, and monolithic-to-microservice
  migrations (e.g., FastAPI → NestJS, Flask → Express, Django → Spring Boot, Python microservices).
  Provides concept mapping matrices, contract preservation patterns, and phased Strangler Fig execution.
metadata:
  origin: CodeArchaeologist
---

# Polyglot Migration Workflow

A structured, risk-contained methodology for migrating software systems across programming languages, web frameworks, and architectural topologies without runtime regressions.

## When to Use

- Migrating a Python backend (FastAPI/Flask/Django) to a Node.js/TypeScript backend (NestJS/Express).
- Modernizing a legacy monolith into modular microservices or a modern decoupled framework.
- Translating data validation logic (e.g. Pydantic v2 → TypeScript Zod or class-validator).
- Migrating database layers (e.g. raw SQL/SQLAlchemy → Prisma/TypeORM/Kysely).
- When executing the `/migrate-framework` slash command.

## Core Architectural Matrices

### Framework Concept Translation Table

| Architecture Dimension | FastAPI (Python) | NestJS (TypeScript) | Spring Boot (Java) | Go (Gin / Echo) |
|---|---|---|---|---|
| **Dependency Injection** | `Depends(get_db)` | `@Injectable()`, `@Inject()` | `@Autowired`, `@Component` | Struct embedding, manual wiring |
| **Data Validation** | Pydantic `BaseModel` | `class-validator` + DTOs | Jakarta Bean Validation (`@Valid`) | `go-playground/validator` |
| **Routing / Endpoints** | `@router.get("/path")` | `@Get("/path")` | `@GetMapping("/path")` | `r.GET("/path", handler)` |
| **Middleware / Interceptors**| Starlette middleware / ASGI | `NestMiddleware`, `Interceptors` | Filter / HandlerInterceptor | Gin Middleware (`c.Next()`) |
| **ORM / Query Engine** | SQLAlchemy / SQLModel | TypeORM / Prisma / MikroORM | Spring Data JPA / Hibernate | sqlc / GORM / ent |
| **Async Execution Model** | `async def` (asyncio event loop)| `async`/`await` (V8 event loop) | Threads / Virtual Threads (Loom)| Goroutines + Channels |
| **Test Framework** | `pytest` + `pytest-asyncio` | `Jest` + `@nestjs/testing` | `JUnit 5` + `MockMvc` | `testing` + `testify` |

## Migration Execution Phases

```
┌────────────────────────────────────────┐
│ Phase 1: Contract Pinning & Snapshot  │ ── Characterization tests & OpenAPI spec dump
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Phase 2: Schema & Model Translation   │ ── Pydantic to TypeScript DTOs / Zod schemas
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Phase 3: Strangler Facade Deployment   │ ── Reverse proxy routing traffic per route
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Phase 4: Modern Cut Implementation    │ ── Target framework implementation + DI wiring
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Phase 5: Dual-Run Differential Testing │ ── Verifying byte-for-byte or semantic parity
└────────────────────────────────────────┘
```

### Phase 1: Contract Pinning & OpenAPI Extraction
Before any line in the target stack is written:
1. Export the active OpenAPI / Swagger specification from the source system.
2. Formulate golden master payloads for success (200, 201), client errors (400, 401, 403, 404, 422), and server errors (500).
3. Validate HTTP header behavior (CORS, content-type, cache-control).

### Phase 2: Schema Translation & Idiomatic Typing
- **Type Safety Preservation**: Guarantee that strict typing in the source system is not degraded (e.g. Python Union/Optional mapped to TypeScript discriminated unions).
- **Serialization Semantics**: Match timestamp formats (ISO-8601 UTC), decimal precision, and null vs undefined handling.

### Phase 3: Strangler Facade & Gateway Routing
- Implement an API Gateway (Nginx, Envoy, or reverse proxy middleware) that conditionally routes:
  - Unmigrated routes $\rightarrow$ Legacy backend
  - Migrated routes $\rightarrow$ New framework service
- Maintain shared authentication session tokens or JWT public keys across both runtimes.

### Phase 4: Dual-Run Differential Verification
- Run test suites concurrently against legacy and modern endpoints.
- Ensure status codes, response headers, and response payload JSON diffs are zero-delta.
