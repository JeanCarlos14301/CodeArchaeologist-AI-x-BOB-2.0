# Sample repositories

Input material prepared before the event and declared in `docs/pre-event.md` (D9).

- **`facturaya-v1/`**: a deliberately vulnerable billing demo (Python 3 + Flask + SQLite) with synthetic data,
  taken from [FacturaYa](https://github.com/JeanCarlos14301/FacturaYa) (`samples/facturaya-v1/` in that
  repository). The complete workflow is supported for this sample, including the first `GET /invoices/{id}`
  cut (D3, D4). `evaluation/expected-findings.json` is its corresponding ground truth.

There is no holdout sample. The earlier variant was a copy of FacturaYa and was removed rather than being
misrepresented as independent. A future evaluation must use a genuinely different repository and document
its hidden changes in advance.

These repositories are **input data**, not product code.
