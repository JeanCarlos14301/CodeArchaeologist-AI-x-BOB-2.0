# /code-audit

Comando de Bob que lanza la auditoría de evidencia (modo `evidence-auditor`) sobre
el repositorio de entrada y devuelve hallazgos en el esquema v1 de `contracts/`.

Uso previsto: `/code-audit <ruta-del-repo>`

## TODO (F-02 / F-03)
- [ ] Definir argumentos y valores por defecto.
- [ ] Definir cómo se reparte el trabajo por módulo entre subagentes.
- [ ] Definir formato de salida y validación con Pydantic.
