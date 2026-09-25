# Decisiones

| ID | Decisión |
|----|----------|
| D1 | El valor es expediente validado + primer corte probado, no un informe libre. |
| D2 | Somos la capa de decisión previa; complementamos los paquetes de modernización de IBM, no competimos. |
| D3 | Primer corte = mejor relación valor/riesgo: `GET /invoices/{id}`. |
| D4 | Migración P0 sobre el repo demo; P1 sobre ZIP arbitrarios. |
| D5 | DOCX es P0; PPTX de 6 diapositivas es P1, desde el mismo JSON. |
| D6 | Orquestador determinista en Python; Bob en modos acotados con subagentes. |
| D7 | Ninguna cifra sin medición; riesgo = impacto × incertidumbre con criterios. |
| D8 | Modo de ejecución siempre visible: `live`, `imported`, `example`. |
| D9 | Repos de muestra preparados antes y declarados; producto desde el kickoff. |
| D10 | Solo Python 3 + Flask + SQLite para el MVP P0 inicial; arquitectura ampliada a políglota para P1. |
| D11 | Un contenedor: FastAPI sirve API y build de React. Plan B: túnel. |
| D12 | Si Bob no corre en servidor: modo asistido importando JSON. |
| D13 | Extensibilidad políglota: soporte de migraciones cruzadas (FastAPI → NestJS, Express, Spring Boot) usando matrices de traducción de conceptos y contratos de caracterización. |
| D14 | Shift-Left Risk Gating: simulador de radio de explosión (`blast-radius-simulator`) previo a PR, analizando grafos de llamadas transitivos y mutaciones de BD sin mutar código. |
| D15 | Tribunal adversarial multi-agente: dialéctica formal Arquitecto vs. Escéptico (`code-skeptic`) para desafiar suposiciones, condiciones de carrera y deuda oculta. |
| D16 | Minería forense de git y AST: integración de PyDriller (hotspots de churn vs. bugs) y Tree-sitter/AST para cartografía estructural y diagramas ER en Mermaid. |
| D17 | Inyección de telemetría externa FastMCP: conector a DuckDB, SQLite en modo lectura y GitHub para enriquecer hallazgos estáticos con métricas de tráfico y fallos en producción. |

## Respuestas del kickoff (J-01)
1. **Alcance técnico**: El núcleo arranca con Flask + SQLite a FastAPI, extensible inmediatamente a NestJS y microservicios mediante el catálogo de agentes especializados.
2. **Seguridad de ejecución**: Código analizado es 100% data, nunca instrucciones (Prompt Defense Baseline activo en todos los agentes).
3. **Métricas de riesgo**: Calculadas por código determinista en Python / AST, nunca inventadas por el modelo de lenguaje.
