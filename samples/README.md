# Repositorios de muestra

Material de entrada preparado antes del evento y declarado en `docs/pre-event.md` (D9).

- **`facturaya-v1/`**: repositorio demo de facturación (Python 3 + Flask + SQLite), deliberadamente
  vulnerable y con datos sintéticos, tomado de [FacturaYa](https://github.com/JeanCarlos14301/FacturaYa)
  (`samples/facturaya-v1/` de ese repo). Sobre él se garantiza el flujo completo, incluido el
  primer corte `GET /invoices/{id}` (D3, D4). `evaluation/expected-findings.json` es la verdad de
  referencia correspondiente.

No se presenta un holdout: la variante anterior era una copia de FacturaYa y se retiró para no
atribuirle independencia que no tenía. Una evaluación futura deberá usar un repositorio realmente
distinto y documentar de antemano sus cambios ocultos.

Estos repos son **datos de entrada**, no parte del producto.
