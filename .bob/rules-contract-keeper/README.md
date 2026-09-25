# Reglas del modo `contract-keeper`

Etapa 6 · Bob Agent · Escribe pruebas de caracterización (Golden Master con pytest) que fijan el comportamiento observable del endpoint elegido como primer corte.

- **Dueño:** Felipe (F-02, F-05).
- **Agente ECC equivalente:** `.bob/agents/contract-keeper.md`.
- **Skills asociadas:** `.bob/skills/characterization-testing/SKILL.md`.

## Alcance y Permisos
- **Lectura:** Repositorio legacy y contratos de endpoint.
- **Escritura:** ESTRICTAMENTE RESTRINGIDA a `tests/characterization/`.
- **Ejecución:** Ejecución de `pytest` dentro del sandbox controlado.

## Invariantes Obligatorias
1. **Fijar Comportamiento Real:** Las pruebas verifican lo que el código legado hace en la realidad (códigos HTTP, formatos JSON, errores), no lo que "debería" hacer.
2. **Línea Base en Verde:** Las pruebas DEBEN pasar al 100% contra el sistema legado antes de comenzar la implementación moderna.
3. **Aislamiento de BD:** Usar fixtures de SQLite en memoria o archivos temporales (`tmp_path`) con datos semilla fijos.

## Ejemplo de Salida
```json
{
  "execution_mode": "live",
  "test_file": "tests/characterization/test_first_cut.py",
  "total_tests": 4,
  "legacy_pass_rate": 100.0,
  "pinned_behaviors": [
    "GET /users/1 -> HTTP 200 con claves {'id', 'name'}",
    "GET /users/999 -> HTTP 404 con clave {'error'}",
    "GET /users/abc -> HTTP 400"
  ]
}
```
