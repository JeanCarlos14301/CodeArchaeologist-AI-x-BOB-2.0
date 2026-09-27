# Daniel's screenshots

## Completed Bob Task Session (Required Deliverable)

- `2026-09-26_blast-radius-guard-extended-01.png` to `2026-09-26_blast-radius-guard-extended-06.png`:
  Full headless `bob run --mode blast-radius-guard --max-cost 3 --trust` run executed in the Bob IDE terminal against `samples/facturaya-v1/db.py` (`connect()`, `get_db()`, and `invoice_by_id()`).
  - **Task ID**: `4420fca2456d0b7786a0d589feaeb829`
  - **Metrics**: 0.323 bobcoins, 1m 16s duration, 3 assistant messages, 16 tool calls, 0 errors.
  - **Screenshot Breakdown**:
    - **`01.png`**: Executive summary table of risks per function (`connect()`, `get_db()`, `invoice_by_id()`), guaranteed test regressions in test suites (`tests/test_invoice_contract.py`, `test_business_rules.py`, `test_known_legacy_behavior.py`, `test_seed.py`, `conftest.py`), and the official **Task Summary** block (0.323 bobcoins, 1m 16s, Task ID `4420fca2456d0b7786a0d589feaeb829`).
    - **`02.png`**: Bob tool execution traces executing `read_file` across project files (`auth.py`, `billing.py`, `customers.py`, `reports.py`, `app.py`, `seed.py`, `tests/test_invoice_contract.py`).
    - **`03.png`**: Phase 1 repository symbol inventory (33 functions across 8 modules) and Phase 2 transitive call graph for `connect()` (`db.py:7-11`).
    - **`04.png`**: Phase 2 transitive call analysis for `invoice_by_id()` (`db.py:37-41`), SQL query inspection, column access matrix consumed by callers (`invoice_json()`, `invoice_html()`), and direct call-sites.
    - **`05.png`**: Phase 3 database mutation matrix and Phase 4 quantitative blast radius metrics: Direct Impact Ratio (DIR = 10/33 = 30.3%), Transitive Blast Radius (TBR = 22/33 = 66.7%), and Test Deficit Factor (TDF).
    - **`06.png`**: Composite Blast Radius Score calculation (CBRS = 73.2 / 100), RED GATE automated block verdict requiring multi-agent adversarial tribunal and double principal engineer sign-off, and failure propagation Mermaid flowchart.

## Additional Reference Screenshots

- `2026-09-26_blast-radius-guard01.png` and `2026-09-26_blast-radius-guard02.png`: Initial headless run attempt (task `4a259689353baa35cef59f5765c01578`, 0.068 bobcoins, 8.3 s) that hit the 3-turn limit before producing the assistant response. Retained for historical tracking.
- `test1.png` and `test2.png`: Runs of the backend test suite (`pytest backend/tests`) in VS Code.
- `test3.png`: Security test suite against the local API (`backend/tests/dast_runner.py`, 25/25 passing).

