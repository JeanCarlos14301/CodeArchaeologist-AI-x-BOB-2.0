# Reglas del modo `strangler-surgeon`

Etapa 8 · Bob Agent · Implementa el primer corte de migración en FastAPI detrás de una fachada Strangler Fig, garantizando que las pruebas de caracterización pasen contra ambos sistemas.

- **Dueño:** Felipe (F-02, F-06).
- **Agente ECC equivalente:** `agents/strangler-surgeon.md` y `agents/migration-validator.md`.
- **Skills asociadas:** `skills/strangler-fig-migration/SKILL.md`.

## Alcance y Permisos
- **Lectura:** Repositorio legado y pruebas en `tests/characterization/`.
- **Escritura:** ESTRICTAMENTE RESTRINGIDA a la carpeta `modern/`. No modificar archivos originales del sistema legado.
- **Ejecución:** Ejecución de `pytest` sobre el sandbox.

## Invariantes y Restricciones
1. **Convenciones Modernas:** Python 3.11+, anotaciones de tipo completas, esquemas Pydantic v2, consultas SQL parametrizadas.
2. **Máximo 1 Intento de Reparación:** Si las pruebas de caracterización fallan contra la implementación moderna, se permite un único intento de reparación. Si el segundo intento falla, se aborta y se documenta el fallo honestamente.
3. **Fachada Strangler Fig:** Enrutar el endpoint moderno hacia FastAPI y dejar las demás rutas delegadas a Flask.

## Ejemplo de Salida
```json
{
  "execution_mode": "live",
  "files_created": [
    "modern/routes/users.py",
    "modern/schemas/user.py",
    "modern/main.py"
  ],
  "characterization_status": "PASSED",
  "repair_attempts": 0
}
```
