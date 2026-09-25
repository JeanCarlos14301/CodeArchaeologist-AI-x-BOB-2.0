# Repositorios de muestra

Material de entrada preparado antes del evento y declarado en `docs/pre-event.md` (D9).

- **`facturaya-v1/`**: repositorio demo de facturación (Python 3 + Flask + SQLite), deliberadamente
  vulnerable y con datos sintéticos, tomado de [FacturaYa](https://github.com/JeanCarlos14301/FacturaYa)
  (`samples/facturaya-v1/` de ese repo). Sobre él se garantiza el flujo completo, incluido el
  primer corte `GET /invoices/{id}` (D3, D4). `evaluation/expected-findings.json` es la verdad de
  referencia correspondiente.
- **`variant-holdout/`** (opcional, no bloqueante): variante que no se usa al ajustar los modos de
  Bob; serviría para comprobar que el pipeline generaliza (F-08). No tenemos ese repo todavía y no
  hace falta para el MVP: `facturaya-v1` es suficiente para el expediente, el memo y el primer
  corte migrado. Si aparece tiempo sobre el final, se puede improvisar tomando un endpoint distinto
  de `facturaya-v1` como si fuera el "holdout"; si no aparece, F-08 se completa solo con la prueba
  sobre `facturaya-v1`.

Estos repos son **datos de entrada**, no parte del producto.
