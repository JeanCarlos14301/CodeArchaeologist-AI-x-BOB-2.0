# Repositorios de muestra

Material de entrada preparado antes del evento y declarado en `docs/pre-event.md` (D9).

- **`facturaya-v1/`**: repositorio demo de facturación (Python 3 + Flask + SQLite), deliberadamente
  vulnerable y con datos sintéticos, tomado de [FacturaYa](https://github.com/JeanCarlos14301/FacturaYa)
  (`samples/facturaya-v1/` de ese repo). Sobre él se garantiza el flujo completo, incluido el
  primer corte `GET /invoices/{id}` (D3, D4). `evaluation/expected-findings.json` es la verdad de
  referencia correspondiente.
- **`variant-holdout/`**: variante que no se usa al ajustar los modos de Bob; sirve para
  comprobar que el pipeline generaliza (F-08).

Estos repos son **datos de entrada**, no parte del producto.
