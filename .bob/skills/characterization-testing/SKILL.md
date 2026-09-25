---
name: characterization-testing
description: >
  Methodology for writing Golden Master characterization tests that pin down 
  current observable behavior of legacy systems before migration or refactoring.
metadata:
  origin: CodeArchaeologist
---

# Characterization Testing (Golden Master)

A testing methodology designed to document and freeze the actual, observable behavior of a legacy software system before any refactoring or migration begins.

## When to Use

- When preparing to migrate or refactor a legacy endpoint without existing unit tests.
- When executing the `/legacy-test` command.
- To prevent unintended behavioral drift or regressions during Strangler Fig cutovers.
- When capturing legacy quirks, status codes, and exact response envelopes.

## Unit Testing vs Characterization Testing

| Characteristic | Traditional Unit Testing | Characterization Testing |
|---|---|---|
| **Goal** | Verify specification & intended design | Pin down current observable reality |
| **Bugs** | Assert correct behavior (expect bugs to fail) | Assert actual behavior (including quirks/bugs) |
| **Author Knowledge** | Written by developer knowing the spec | Written by observing existing code responses |
| **Pass Requirement** | Passes when code meets requirements | Passes when output matches legacy baseline |

## Step-by-Step Characterization Procedure

### Step 1: Establish Test Isolation & Fixtures
1. Never run tests against production or shared database files.
2. Create an isolated SQLite database fixture seeded with representative test records:
   ```python
   @pytest.fixture
   def test_db(tmp_path):
       db_file = tmp_path / "test.db"
       conn = sqlite3.connect(db_file)
       # seed schema and minimal test data
       conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, role TEXT)")
       conn.execute("INSERT INTO users VALUES (1, 'alice', 'admin'), (2, 'bob', 'user')")
       conn.commit()
       conn.close()
       return str(db_file)
   ```

### Step 2: Probe Input Dimensions
Systematically probe the target endpoint across 4 critical vectors:
- **Valid Nominal Inputs**: Existing entity IDs, standard payloads.
- **Boundary Conditions**: Zero, empty strings, extremely large numbers, Unicode strings.
- **Malformed Inputs**: Non-numeric IDs where integers are expected, missing JSON keys.
- **Missing Resource / 404**: Unmatched IDs to capture exact error response keys.

### Step 3: Record Observable Output Matrix
Record and assert on all four observable output dimensions:
1. **HTTP Status Code**: (e.g. 200 vs 201 vs 404 vs 400).
2. **Content-Type Header**: (e.g. `application/json; charset=utf-8`).
3. **Exact Response Body / Keys**: Verify key existence, nested dictionaries, null values.
4. **Database State Mutations**: (If mutating endpoint, check table row count or modified timestamp).

### Step 4: Run Baseline Against Legacy
Execute:
```bash
pytest tests/characterization/ -v
```
If any assertion fails against the legacy code, **update the assertion to match reality**. The legacy code is the ground truth.

### Step 5: Reuse Test Harness Against Modern Implementation
When `strangler-surgeon` implements the modern route, run the exact same test assertions against the new endpoint to prove behavioral parity.

## Best Practices

- **Pin Exact Response Envelopes**: Do not just assert `assert response.status_code == 200`. Assert the exact structure: `assert data == {"id": 1, "username": "alice", "role": "admin"}`.
- **Keep Tests Deterministic**: Mock external dependencies (time, external HTTP calls, random generators) so tests never fail intermittently.
- **Store in Dedicated Directory**: Always write characterization tests in `tests/characterization/` to distinguish them from standard unit tests.
