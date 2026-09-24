"""Orquestador determinista del pipeline (D6).

Etapas:
   1. Ingesta e inventario (Python).
   2. evidence-auditor (Bob Ask, solo lectura, delega módulos a subagentes).
   3. Validador de evidencia (Python).
   4. migration-architect (Bob Plan).
   5. Riesgo y esfuerzo PERT (Python).
   6. contract-keeper (Bob Agent, escribe pruebas en sandbox).
   7. Pruebas vs legado (pytest).
   8. strangler-surgeon (Bob Agent, escribe solo en modern/).
   9. Pruebas vs nuevo, máximo 1 reparación.
  10. board-narrator (Bob Ask).
  11. Renderizadores DOCX, HTML, PPTX.

Cada resultado lleva execution_mode: live, imported o example (D8).
"""
