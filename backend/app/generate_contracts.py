"""Generador de contratos JSON v1 y fixtures válidos y parciales (D-01).

Genera:
- contracts/schema-v1.json (JSON Schema estándar a partir de Pydantic v2).
- contracts/fixtures/valid-dossier.json (Expediente completo y validado sobre FacturaYa v1).
- contracts/fixtures/partial-dossier.json (Expediente en estado de ejecución parcial).
"""

import json
from pathlib import Path
from backend.app.models import (
    DossierResult,
    SnapshotMetadata,
    Finding,
    EvidenceLocation,
    ArchitectureOption,
    MigrationPhase,
    CharacterizationTestCase,
    CharacterizationTestReport,
    MigrationSummary,
    ValidationReport,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONTRACTS_DIR = BASE_DIR / "contracts"
FIXTURES_DIR = CONTRACTS_DIR / "fixtures"


def generate_schema() -> Path:
    """Genera schema-v1.json desde DossierResult."""
    schema = DossierResult.model_json_schema()
    schema_path = CONTRACTS_DIR / "schema-v1.json"
    schema_path.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Generado: {schema_path}")
    return schema_path


def build_valid_dossier() -> DossierResult:
    """Construye un expediente completo y real para FacturaYa v1."""
    snapshot = SnapshotMetadata(
        sample_id="facturaya-v1",
        repo_name="FacturaYa v1 (Legacy Monolith)",
        snapshot_sha256="d45791058ac483aba258df1e4a2d5b8d53e66bcf891b63363ee1feb33ace479a",
        total_files=10,
        total_loc=1420,
        languages_detected=["Python", "SQL", "HTML"],
        entrypoints=["app.py"],
        timestamp="2026-09-25T10:00:00Z",
        execution_mode="live",
    )

    findings = [
        Finding(
            id="EF-1",
            title="Inyección SQL por concatenación en búsqueda de facturas",
            category="security/sql-injection",
            severity="CRITICAL",
            confidence="HIGH",
            priority="P0",
            expected_detection=True,
            evidence=[
                EvidenceLocation(
                    path="samples/facturaya-v1/app.py",
                    line_start=78,
                    line_end=78,
                    fragment='sql = "SELECT id, number, issue_date, total FROM invoices WHERE owner_id = "',
                    observed_or_inferred="observed",
                )
            ],
            explanation="El parámetro de búsqueda 'q' y el owner_id se concatenan directamente a la consulta SQL sin parametrizar, permitiendo exfiltración de datos no autorizados.",
            verification_method="Inyectar ' OR 1=1 -- en el query parameter de búsqueda; la respuesta devuelve facturas de otros clientes.",
            blast_radius_score=85.0,
            transitive_impacted_symbols=["app.invoices_search", "db.query_db", "billing.get_invoice"],
            status="accepted",
        ),
        Finding(
            id="EF-2",
            title="Función de ruta monolítica con responsabilidades mezcladas",
            category="maintainability/large-function",
            severity="HIGH",
            confidence="HIGH",
            priority="P1",
            expected_detection=True,
            evidence=[
                EvidenceLocation(
                    path="samples/facturaya-v1/app.py",
                    line_start=127,
                    line_end=281,
                    fragment="def invoice_new():",
                    observed_or_inferred="observed",
                )
            ],
            explanation="La función 'invoice_new' tiene 155 líneas y mezcla validación de formulario, reglas de negocio de descuentos, transacciones de BD y renderizado HTML directo.",
            verification_method="Inspección AST y medición de complejidad ciclomática con Radon (CC > 18).",
            blast_radius_score=68.5,
            transitive_impacted_symbols=["app.invoice_new", "billing.calculate_totals", "db.get_db"],
            status="accepted",
        ),
        Finding(
            id="EF-3",
            title="Regla de descuento duplicada con redondeo divergente",
            category="business-rule/duplication",
            severity="HIGH",
            confidence="HIGH",
            priority="P0",
            expected_detection=True,
            evidence=[
                EvidenceLocation(
                    path="samples/facturaya-v1/billing.py",
                    line_start=28,
                    line_end=28,
                    fragment='discount = (subtotal * RATE).quantize',
                    observed_or_inferred="observed",
                ),
                EvidenceLocation(
                    path="samples/facturaya-v1/reports.py",
                    line_start=14,
                    line_end=14,
                    fragment='((Decimal(str(item["line_total"])) * RATE).quantize',
                    observed_or_inferred="observed",
                ),
            ],
            explanation="Facturación redondea el descuento sobre el subtotal global, mientras que el módulo de reportes redondea línea por línea y luego suma, causando discrepancias contables.",
            verification_method="Factura FY-00001 tiene descuento facturado de 7.51 pero en el reporte contable aparece como 7.50.",
            blast_radius_score=54.0,
            transitive_impacted_symbols=["billing.calculate_discount", "reports.generate_summary"],
            status="accepted",
        ),
        Finding(
            id="EF-4",
            title="Claves secretas ficticias escritas en código fuente",
            category="security/hardcoded-secret",
            severity="CRITICAL",
            confidence="HIGH",
            priority="P0",
            expected_detection=True,
            evidence=[
                EvidenceLocation(
                    path="samples/facturaya-v1/config.py",
                    line_start=3,
                    line_end=3,
                    fragment='SECRET_KEY = "DEMO_ONLY_NOT_A_REAL_SECRET"',
                    observed_or_inferred="observed",
                ),
                EvidenceLocation(
                    path="samples/facturaya-v1/config.py",
                    line_start=4,
                    line_end=4,
                    fragment='PAYMENT_GATEWAY_KEY = "DEMO_ONLY_NOT_A_REAL_GATEWAY_KEY"',
                    observed_or_inferred="observed",
                ),
            ],
            explanation="Constantes criptográficas y credenciales de pasarela declaradas en texto plano en el repositorio.",
            verification_method="Inspección estática de config.py y escaneo Bandit.",
            blast_radius_score=40.0,
            transitive_impacted_symbols=["config.SECRET_KEY", "app.app.config"],
            status="accepted",
        ),
        Finding(
            id="EF-5",
            title="Dependencia circular diferida entre módulos de negocio",
            category="architecture/cyclic-dependency",
            severity="MEDIUM",
            confidence="HIGH",
            priority="P1",
            expected_detection=True,
            evidence=[
                EvidenceLocation(
                    path="samples/facturaya-v1/billing.py",
                    line_start=3,
                    line_end=3,
                    fragment="from customers import get_customer",
                    observed_or_inferred="observed",
                ),
                EvidenceLocation(
                    path="samples/facturaya-v1/customers.py",
                    line_start=22,
                    line_end=22,
                    fragment="from billing import count_customer_invoices",
                    observed_or_inferred="observed",
                ),
            ],
            explanation="billing.py importa customers a nivel de módulo, y customers.py importa billing de forma diferida dentro de una función, indicando alto acoplamiento.",
            verification_method="Inspección del grafo de imports y prueba de carga diferida.",
            blast_radius_score=62.0,
            transitive_impacted_symbols=["billing", "customers"],
            status="accepted",
        ),
        Finding(
            id="EF-6",
            title="Acceso a JSON de factura sin autorización por propietario (BOLA/IDOR)",
            category="security/broken-object-authorization",
            severity="CRITICAL",
            confidence="HIGH",
            priority="P0",
            expected_detection=True,
            evidence=[
                EvidenceLocation(
                    path="samples/facturaya-v1/app.py",
                    line_start=93,
                    line_end=107,
                    fragment="def invoice_json(invoice_id):",
                    observed_or_inferred="observed",
                )
            ],
            explanation="El endpoint GET /invoices/<id> comprueba que exista una sesión activa pero no valida que la factura solicitada pertenezca al usuario autenticado.",
            verification_method="Autenticarse como usuario 'bruno' y solicitar la factura 1 de 'ana'; el sistema responde HTTP 200 con datos ajenos.",
            blast_radius_score=72.0,
            transitive_impacted_symbols=["app.invoice_json", "db.get_invoice_by_id"],
            status="accepted",
        ),
        Finding(
            id="EF-7",
            title="Consulta SQL de búsqueda de cliente correctamente parametrizada",
            category="control/parameterized-query",
            severity="INFO",
            confidence="HIGH",
            priority="P2",
            expected_detection=False,
            evidence=[
                EvidenceLocation(
                    path="samples/facturaya-v1/db.py",
                    line_start=33,
                    line_end=33,
                    fragment="SELECT id, owner_id, name, email FROM customers WHERE email = ?",
                    observed_or_inferred="observed",
                )
            ],
            explanation="Control negativo: La consulta utiliza el placeholder '?' de SQLite. No constituye vulnerabilidad y debe mantenerse protegida.",
            verification_method="Prueba de caracterización pasando cargas SQL sintéticas; la consulta retorna cero filas sin error de sintaxis.",
            blast_radius_score=5.0,
            transitive_impacted_symbols=["db.get_customer_by_email"],
            status="accepted",
        ),
    ]

    architecture_options = [
        ArchitectureOption(
            id="OPT-1",
            name="Extracción Progresiva con Strangler Fig (Recomendada)",
            pattern="Strangler Fig",
            pros=[
                "Bajo riesgo operativo: el sistema antiguo y el nuevo conviven simultáneamente.",
                "Primer corte verificable con pruebas de caracterización golden-master.",
                "Despliegue incremental por endpoint sin interrupción del negocio.",
            ],
            cons=[
                "Requiere mantener una capa de enrutamiento fachada durante la transición.",
                "Duplicidad temporal de modelos de datos.",
            ],
            target_stack="FastAPI (Python 3.11) + SQLite/Postgres + Pydantic v2",
            risk_level="LOW",
            estimated_effort_days=18.5,
            recommended=True,
        ),
        ArchitectureOption(
            id="OPT-2",
            name="Extracción por Módulos Hoja (Leaf Services)",
            pattern="Leaf Cut",
            pros=[
                "Desacopla componentes sin dependencias entrantes (ej. reports.py).",
                "Fácil de aislar y testear en contenedores independientes.",
            ],
            cons=[
                "Bajo impacto directo en el valor percibido por el usuario final.",
                "No resuelve las vulnerabilidades críticas de autenticación y BOLA en el núcleo.",
            ],
            target_stack="Microservicios FastAPI independientes",
            risk_level="MEDIUM",
            estimated_effort_days=24.0,
            recommended=False,
        ),
        ArchitectureOption(
            id="OPT-3",
            name="Reescritura Completa desde Cero (Big Bang)",
            pattern="Big Bang Rewrite",
            pros=["Código 100% nuevo sin arrastrar decisiones heredadas."],
            cons=[
                "Riesgo extremo de desviación de cronograma y presupuesto.",
                "Pérdida de reglas de negocio tácitas y casos borde no documentados.",
                "Cero entregas de valor hasta el final del proyecto.",
            ],
            target_stack="FastAPI o NestJS monolítico",
            risk_level="HIGH",
            estimated_effort_days=65.0,
            recommended=False,
        ),
    ]

    pert_plan = [
        MigrationPhase(
            phase_number=1,
            name="Fase 1: Fijación de Contratos y Pruebas de Caracterización",
            description="Crear suite de pruebas golden-master con pytest que fijen el comportamiento observable actual de GET /invoices/{id}.",
            optimistic_days=2.0,
            nominal_days=3.0,
            pessimistic_days=5.0,
            pert_expected_days=3.17,
            pert_variance=0.25,
            assumptions=["Acceso a base de datos de prueba con fixtures conocidos de FacturaYa."],
            prerequisites=["Definición congelada de contratos JSON v1."],
            rollback_strategy="Descartar suite de pruebas sin impacto en producción.",
        ),
        MigrationPhase(
            phase_number=2,
            name="Fase 2: Implementación del Micro-endpoint en FastAPI y Enrutador Fachada",
            description="Construir el nuevo módulo en modern/invoices_api.py con validación Pydantic y fachada que redirige GET /invoices/{id}.",
            optimistic_days=3.0,
            nominal_days=5.0,
            pessimistic_days=8.0,
            pert_expected_days=5.17,
            pert_variance=0.69,
            assumptions=["FastAPI puede compartir el acceso a la base de datos SQLite en modo WAL."],
            prerequisites=["Fase 1 aprobada con 100% de pruebas en verde contra el legado."],
            rollback_strategy="Conmutar la bandera de enrutamiento en la fachada hacia la ruta original de Flask.",
        ),
        MigrationPhase(
            phase_number=3,
            name="Fase 3: Modernización del Núcleo de Facturación y Clientes",
            description="Reescribir app.invoice_new y billing.py eliminando dependencias circulares y parametrizando todas las consultas.",
            optimistic_days=6.0,
            nominal_days=10.0,
            pessimistic_days=16.0,
            pert_expected_days=10.33,
            pert_variance=2.78,
            assumptions=["Las pruebas unitarias y de integración cubren los cálculos de redondeo."],
            prerequisites=["Fase 2 desplegada y estable."],
            rollback_strategy="Mantener el contenedor del backend Flask como respaldo activo.",
        ),
    ]

    characterization_legacy = CharacterizationTestReport(
        total_tests=5,
        passed_count=5,
        failed_count=0,
        target_endpoint="GET /invoices/{id}",
        test_cases=[
            CharacterizationTestCase(
                name="test_invoice_owner_access",
                target_endpoint="GET /invoices/{id}",
                test_type="contract",
                status="PASS",
                duration_ms=12.4,
            ),
            CharacterizationTestCase(
                name="test_invoice_amounts_calculation",
                target_endpoint="GET /invoices/{id}",
                test_type="business_rule",
                status="PASS",
                duration_ms=8.1,
            ),
            CharacterizationTestCase(
                name="test_invoice_unauthenticated_401",
                target_endpoint="GET /invoices/{id}",
                test_type="security",
                status="PASS",
                duration_ms=5.2,
            ),
            CharacterizationTestCase(
                name="test_invoice_not_found_404",
                target_endpoint="GET /invoices/{id}",
                test_type="contract",
                status="PASS",
                duration_ms=6.0,
            ),
            CharacterizationTestCase(
                name="test_known_legacy_bola_behavior",
                target_endpoint="GET /invoices/{id}",
                test_type="security",
                status="PASS",
                duration_ms=9.3,
            ),
        ],
        all_passed=True,
    )

    characterization_modern = CharacterizationTestReport(
        total_tests=5,
        passed_count=5,
        failed_count=0,
        target_endpoint="GET /invoices/{id}",
        test_cases=[
            CharacterizationTestCase(
                name="test_invoice_owner_access",
                target_endpoint="GET /invoices/{id}",
                test_type="contract",
                status="PASS",
                duration_ms=4.2,
            ),
            CharacterizationTestCase(
                name="test_invoice_amounts_calculation",
                target_endpoint="GET /invoices/{id}",
                test_type="business_rule",
                status="PASS",
                duration_ms=3.8,
            ),
            CharacterizationTestCase(
                name="test_invoice_unauthenticated_401",
                target_endpoint="GET /invoices/{id}",
                test_type="security",
                status="PASS",
                duration_ms=2.1,
            ),
            CharacterizationTestCase(
                name="test_invoice_not_found_404",
                target_endpoint="GET /invoices/{id}",
                test_type="contract",
                status="PASS",
                duration_ms=2.5,
            ),
            CharacterizationTestCase(
                name="test_fixed_security_bola_now_returns_404",
                target_endpoint="GET /invoices/{id}",
                test_type="security",
                status="PASS",
                duration_ms=3.0,
            ),
        ],
        all_passed=True,
    )

    diff_sample = """--- a/samples/facturaya-v1/app.py
+++ b/samples/facturaya-v1/modern/facade.py
@@ -93,14 +93,12 @@
-def invoice_json(invoice_id):
-    # Legacy route vulnerable to BOLA
-    inv = get_invoice(invoice_id)
-    return jsonify(inv)
+from modern.invoices_api import get_invoice_modern
+
+@app.route("/invoices/<int:invoice_id>")
+def invoice_json(invoice_id):
+    # Strangler Fig routing: intercepted and forwarded to modern FastAPI handler
+    return get_invoice_modern(invoice_id, current_user=session.get("user_id"))
"""

    migration_summary = MigrationSummary(
        endpoint_migrated="GET /invoices/{id}",
        modern_code_files=["modern/invoices_api.py", "modern/schemas.py"],
        facade_router_file="modern/facade.py",
        legacy_tests_verdict="PASS",
        modern_tests_verdict="PASS",
        repaired_count=0,
        diff_patch=diff_sample,
    )

    validation_report = ValidationReport(
        total_references=8,
        valid_references=8,
        invalid_references=0,
        fidelity_ratio=1.0,
        details=["100% de las citas apuntan a archivos y rangos de líneas válidos en samples/facturaya-v1/."],
    )

    mermaid_er = """erDiagram
    INVOICES {
        int id PK
        int owner_id FK
        string number
        date issue_date
        decimal total
        string status
    }
    CUSTOMERS {
        int id PK
        int owner_id FK
        string name
        string email
    }
    INVOICE_ITEMS {
        int id PK
        int invoice_id FK
        string description
        int quantity
        decimal unit_price
        decimal line_total
    }
    CUSTOMERS ||--o{ INVOICES : places
    INVOICES ||--|{ INVOICE_ITEMS : contains"""

    mermaid_flow = """flowchart TD
    Client["Cliente / Navegador"] --> Facade["Fachada Strangler Fig"]
    Facade -->|GET /invoices/id| Modern["FastAPI (modern/invoices_api.py)"]
    Facade -->|Otras rutas| Legacy["Flask Monolito (app.py)"]
    Modern --> DB[("SQLite Database")]
    Legacy --> DB"""

    return DossierResult(
        schema_version="1.0",
        job_id="job-demo-facturaya-001",
        snapshot=snapshot,
        findings=findings,
        architecture_options=architecture_options,
        selected_first_cut="GET /invoices/{id}",
        pert_plan=pert_plan,
        characterization_tests_legacy=characterization_legacy,
        characterization_tests_modern=characterization_modern,
        migration_summary=migration_summary,
        validation_report=validation_report,
        executive_summary="CodeArchaeologist completó el diagnóstico forense de FacturaYa v1. Se identificaron 6 problemas reales (2 críticos de seguridad: SQLi y BOLA/IDOR, 1 secreto ficticio, 1 cálculo contable divergente y 1 dependencia circular). Se recomienda la modernización progresiva con Strangler Fig iniciando en GET /invoices/{id}, logrando un primer paso probado en verde con cero tiempo de inactividad.",
        mermaid_er_diagram=mermaid_er,
        mermaid_call_flow=mermaid_flow,
        execution_mode="live",
    )


def build_partial_dossier() -> DossierResult:
    """Construye un expediente en estado parcial (ejecución hasta etapa 5)."""
    full = build_valid_dossier()
    return DossierResult(
        schema_version="1.0",
        job_id="job-partial-facturaya-002",
        snapshot=full.snapshot,
        findings=full.findings[:3],
        architecture_options=full.architecture_options,
        selected_first_cut="GET /invoices/{id}",
        pert_plan=full.pert_plan[:1],
        characterization_tests_legacy=None,
        characterization_tests_modern=None,
        migration_summary=None,
        validation_report=ValidationReport(
            total_references=3,
            valid_references=3,
            invalid_references=0,
            fidelity_ratio=1.0,
            details=["Validación parcial de etapas 1 a 5."],
        ),
        executive_summary="Análisis preliminar en progreso. Se han identificado los primeros 3 hallazgos críticos.",
        mermaid_er_diagram=full.mermaid_er_diagram,
        mermaid_call_flow=full.mermaid_call_flow,
        execution_mode="live",
    )


def main():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Generar JSON Schema
    generate_schema()

    # 2. Generar y validar fixture completo
    valid_dossier = build_valid_dossier()
    valid_json = valid_dossier.model_dump_json(indent=2)
    valid_path = FIXTURES_DIR / "valid-dossier.json"
    valid_path.write_text(valid_json, encoding="utf-8")
    # Re-validación estricta
    DossierResult.model_validate_json(valid_path.read_text(encoding="utf-8"))
    print(f"[OK] Generado y validado fixture completo: {valid_path}")

    # 3. Generar y validar fixture parcial
    partial_dossier = build_partial_dossier()
    partial_json = partial_dossier.model_dump_json(indent=2)
    partial_path = FIXTURES_DIR / "partial-dossier.json"
    partial_path.write_text(partial_json, encoding="utf-8")
    DossierResult.model_validate_json(partial_path.read_text(encoding="utf-8"))
    print(f"[OK] Generado y validado fixture parcial: {partial_path}")


if __name__ == "__main__":
    main()
