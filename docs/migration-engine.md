# Deterministic Migration & Strangler Fig Engine

## 1. Overview & Architecture

CodeArchaeologist provides an evidence-based, deterministic decision engine for legacy software modernization. Rather than allowing generative language models to invent timelines, migration order, or risk scores, CodeArchaeologist separates concerns:
1. **IBM Bob 2.0 Shell**: Functions as a forensic evidence auditor inspecting the codebase and citing file paths, exact line ranges, verbatim code snippets, and structured explanations.
2. **Deterministic Analysis Engine (Python / AST)**: Parses code syntax trees, resolves call graphs, inventories SQL queries and database schemas, and calculates exact mathematical scores for every route candidate without executing untrusted code.

```mermaid
flowchart TD
    A[Legacy Repository / Uploaded ZIP] --> B[Static AST & Callgraph Analysis]
    B --> C[Route Extractor: FlaskRouteVisitor]
    B --> D[SQL & Table Write Mapper]
    B --> E[Verified Finding Scope Resolver]
    C & D & E --> F[Deterministic Scoring Engine: Value, Risk, Testability]
    F --> G[Route Ranking & 'Do Not Start Here' Detector]
    G --> H[Strangler Fig 3-Wave Planner]
    H --> I[Dynamic PERT Calculator with Heuristic Notice]
    I --> J[REST API: GET /api/audits/{id}/migration]
```

---

## 2. Deterministic Candidate Ranking Engine

### 2.1 Scope & Metric Definitions

For every detected route candidate $r$, its scope $S(r)$ is defined statically as its handler function plus all transitively reachable functions in the call graph:
$$S(r) = \{\text{handler}(r)\} \cup \text{Callees}^*(\text{handler}(r))$$

The engine calculates three orthogonal dimensions:

#### 1. Value ($V$)
Measures the vulnerability and architectural debt mitigated by migrating the route:
$$V(r) = 1 + \sum_{f \in \text{Findings}(S(r))} W(\text{severity}(f))$$
Where weights $W$ are defined as:
- `critical`: 4
- `high`: 3
- `medium`: 2
- `low`: 1

#### 2. Risk ($R$)
Measures architectural coupling, database write surface, cyclomatic complexity, lines of code, and circular dependencies:
$$R(r) = 1 + N_{\text{shared\_funcs}} + 2 \times N_{\text{tables\_written}} + \frac{\text{CC}_{\text{scope}}}{5} + \frac{\text{LOC}_{\text{scope}}}{50} + \delta_{\text{circular}}$$
Where $\delta_{\text{circular}} = 2$ if any file in scope participates in an import cycle, 0 otherwise.

#### 3. Testability / Ease of Verification ($T$)
Quantifies characterization test reliability:
- $T = 1.0$: Route returns structured JSON (`jsonify` or `/api/` endpoint) with deterministic contracts.
- $T = 0.5$: Read-only endpoint rendering HTML templates.
- $T = 0.25$: Route performs database mutations (POST/PUT/DELETE) or writes to persistent storage.

#### 4. Composite Score
$$\text{Score}(r) = \frac{V(r) \times T(r)}{R(r)}$$

### 2.2 Concrete FacturaYa Reference Evaluation
On the benchmark dataset `samples/facturaya-v1` (10 Flask routes detected), the engine deterministically ranks all candidates:

| Rank | Route | Handler | Methods | Value | Risk | Testability | Score | Decision |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | `/invoices` | `invoices_list` | GET | 5.0 | 4.54 | 0.50 | **0.551** | Alternative candidate (read view) |
| **2** | `/invoices/<id>` | `invoice_json` | GET | 4.0 | 10.06 | 1.00 | **0.398** | **Recommended First Cut** (Pure JSON, leaf contract) |
| **3** | `/logout` | `logout` | POST | 5.0 | 3.48 | 0.25 | **0.359** | Alternative (simple auth mutation) |
| **4** | `/` | `index` | GET | 1.0 | 1.58 | 0.50 | **0.316** | Safe static view |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |
| **10** | `/invoices/new` | `create_invoice` | POST | 5.0 | **30.54** | 0.25 | **0.041** | **DO NOT START HERE** |

#### Why `/invoices/new` is flagged as "Do Not Start Here":
- Highest risk score in the codebase: **30.54**.
- **225 lines of code** and **65 cyclomatic complexity** in its transitive scope.
- Mutates multiple transactional tables concurrently (`invoices`, `invoice_items`).
- High coupling with customer validation, tax calculations, and sequential numbering.

---

## 3. Strangler Fig 3-Wave Roadmap & Dynamic PERT

Routes are automatically partitioned into three progressive migration waves:
- **Wave 1 — Safe First Cuts (Leaf Endpoints & JSON Contracts)**: Endpoints with low coupling and clear contracts (`/invoices/<id>`, `/invoices`, `/`).
- **Wave 2 — Intermediate Domain Services**: Read views, reports, and customer management (`/reports/sales`, `/customers`, `/login`).
- **Wave 3 — Core Transactional Engine**: Transactional mutations and financial integrity (`/invoices/new`, `/invoices/edit`).

### 3.1 Three-Point PERT Calculation
For any migration scope (whether a single cut or an entire wave), effort points are derived from measurable metrics:
$$\text{Points} = 2 \times N_{\text{routes}} + N_{\text{functions}} + \lceil \text{LOC} / 25 \rceil + \lceil \text{Complexity} / 5 \rceil$$
$$M = \text{Points} \times 0.5 \text{ days}$$
$$O = 0.6 \times M, \quad P = 1.8 \times M, \quad E = \frac{O + 4M + P}{6}, \quad \text{Variance} = \left(\frac{P - O}{6}\right)^2$$

### 3.2 Mandatory Uncalibrated Disclaimer
Every PERT estimation returned by the API and displayed in the frontend explicitly contains the assumption:
> *"Estimación heurística, no calibrada (0,5 días por punto de complejidad y acoplamiento)."*

This guarantees transparency and prevents presenting heuristic estimations as calibrated commitments.

---

## 4. API Endpoints & Security Architecture

### 4.1 Endpoint: `GET /api/audits/{id}/migration`
Returns the complete migration recommendation payload:
```json
{
  "job_id": "3f1618e87c54",
  "recommendation": {
    "recommended": {
      "endpoint": "GET /invoices/<int:invoice_id>",
      "rule": "/invoices/<int:invoice_id>",
      "function_name": "invoice_json",
      "score": 0.398,
      "why": "Responde JSON puro con contrato formal, sin escrituras en base de datos, mitiga 1 hallazgo(s) (F-2)."
    },
    "alternatives": [...],
    "do_not_start_here": {
      "endpoint": "GET, POST /invoices/new",
      "rule": "/invoices/new",
      "function_name": "create_invoice",
      "risk": 30.54,
      "tables_written": ["invoices", "invoice_items"],
      "why": "Endpoint con mutación o método POST, escribe en tablas invoices, invoice_items..."
    },
    "candidates": [...],
    "waves": [
      {
        "wave_number": 1,
        "name": "Ola 1 — Primeros Cortes Seguros (Leaf Endpoints & JSON)",
        "pert": {
          "optimistic_days": 6.3,
          "most_likely_days": 10.5,
          "pessimistic_days": 18.9,
          "expected_days": 11.2,
          "assumptions": [
            "Estimación heurística, no calibrada (0,5 días por punto de complejidad y acoplamiento)."
          ]
        }
      }
    ],
    "first_cut_pert": {...}
  },
  "result": {...},
  "legacy_code": "...",
  "modern_code": "...",
  "facade_code": "..."
}
```

### 4.2 Security & Isolation Guarantees
- **No Untrusted Execution**: Uploaded ZIP repositories are statically parsed using Python's `ast` standard library module. Code is **never imported, evaluated (`eval`/`exec`), or run in a subshell**.
- **Path Traversal Protection**: All file requests are validated via strict boundary checking (`resolve_inside`), rejecting `../`, `..\`, and URL-encoded traversal attempts with HTTP 404.
- **Access Control**: Uploaded private repositories require `X-Live-Token` authentication (`HTTP 403 Forbidden` if missing or invalid).

---

## 5. Verification & Testing Suite

| Category | Tool | Scope | Result |
| :--- | :--- | :--- | :---: |
| **Unit & Integration Tests** | `pytest` | 209 test cases across all modules | **100% PASSED** |
| **Static Security (SAST)** | `bandit` | 7,399 LOC scanned across `backend/app` | **0 Vulnerabilities** |
| **Dynamic Security (DAST)** | `curl.exe` | 25 real-world attack & functional assertions | **25/25 PASSED** |
| **IBM Bob Shell 2.0 (Live)** | `bob` CLI | Live execution: `evidence-auditor`, `migration-architect`, `stream-json` | **3/3 PASSED** |
| **CI/CD Pipeline** | GitHub Actions | Ubuntu runner: backend, frontend, docker smoke test | **ALL GREEN** |
