# Evaluación

- `expected-findings.json` es la **verdad de referencia** de hallazgos para `samples/facturaya-v1`,
  tomada de [FacturaYa](https://github.com/JeanCarlos14301/FacturaYa) (`evaluation/expected-findings.json`
  de ese repo), con las rutas de evidencia reescritas relativas a la raíz de la muestra (`app.py`,
  no `samples/facturaya-v1/app.py`) para que coincidan con lo que cita `evidence-auditor`.
- Incluye 7 hallazgos: 6 con `expected_detection: true` y uno (`EF-7`) con `false`, para poder medir
  también falsos positivos, no solo recall.
- **NUNCA se pasa a Bob** ni se incluye en ningún prompt o contexto de modo. `evidence_audit.py`
  ya excluye la carpeta `evaluation/` y `expected-findings*.json` al copiar el workspace del sandbox.
- Se usa solo para medir la precisión y el recall de `evidence-auditor` (F-07).

## TODO
- [ ] Tabla de precisión y recall (F-07): comparar los hallazgos aceptados de un dossier real
  contra `expected-findings.json` por `category`/rango de líneas y calcular precisión y recall.
