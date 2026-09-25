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

## Primera medición (informal, H7 aprox., job `02833a24a7a7`)

Primera corrida `live` real de `evidence-auditor` sobre `facturaya-v1` (Jean, 25/09/2026 15:22,
120 s, 1.14 bobcoins), comparada a mano contra `expected-findings.json`:

| Referencia | Esperado | Resultado |
|---|---|---|
| EF-1 SQL inyectado | detectar | ✅ detectado y validado (`F-1`) |
| EF-2 función `invoice_new` extensa | detectar | ✅ detectado y validado (`F-10`) |
| EF-3 descuento duplicado | detectar | ⚠️ Bob lo reportó (`F-5`), pero el validador **rechazó** la mitad de la evidencia (el fragmento citado en `reports.py` no calzó con el rango) — el hallazgo no llegó al expediente final |
| EF-4 secretos hardcodeados | detectar | ✅ detectado y validado (`F-2`) |
| EF-5 dependencia circular | detectar | ✅ detectado y validado (`F-9`) |
| EF-6 IDOR en JSON de factura | detectar | ✅ detectado y validado (`F-3`) |
| EF-7 consulta parametrizada (control negativo) | NO detectar | ✅ no se reportó ningún falso positivo aquí |

**Recall sobre hallazgos validados: 5/6 (83%).** El único miss (EF-3) no es que Bob no lo haya visto
— lo vio y lo redactó — sino que su propia cita de evidencia no coincidió lo bastante con el código
como para pasar el validador de la etapa 3. Es el comportamiento correcto del validador (D7): mejor
perder un hallazgo real que dejar pasar uno con evidencia que no se sostiene.

Bob reportó además 7 hallazgos fuera de esta lista de 7 (condición de carrera en numeración de
facturas, N+1 en el reporte mensual, hashing débil en `seed.py`, IDOR en el conteo de facturas por
cliente, dinero como `TEXT` en SQLite, ausencia de pruebas, `login_required` inconsistente); todos
con cita de archivo/línea verificada por el validador. No están en `expected-findings.json` porque
esa lista es un mínimo curado, no exhaustivo — no se cuentan como falsos positivos sin revisión
manual, pero valdría la pena que alguien del equipo los revise para decidir si se agregan a la
verdad de referencia.

## TODO
- [ ] Automatizar esta comparación (script que lea un `dossier.json` + `expected-findings.json` y
  calcule precisión/recall por rango de líneas, no a mano) — F-07.
- [ ] Revisar por qué el segundo fragmento de `F-5` no calzó en `reports.py` (¿tolerancia de línea,
  o el snippet de Bob no es literal?) y decidir si vale la pena ajustar `LINE_TOLERANCE` o pedirle
  a Bob una sola línea representativa por evidencia en vez de fragmentos con `...`.
