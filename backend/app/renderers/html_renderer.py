"""Renderizador de Reporte HTML Autónomo e Interactivo (D-08).

Genera un archivo HTML autocontenido con:
- Paleta ejecutiva moderna (inspirada en IBM Carbon Design y modo oscuro refinado).
- Tarjetas de resumen de métricas clave (Fidelidad 100%, Hallazgos, PERT, Radio de Explosión).
- Visor de evidencia con fragmentos de código, números de línea y badges de severidad.
- Diagramas Mermaid embebidos (ER y flujo de llamadas).
- Tabla de opciones de arquitectura y plan PERT.
"""

from pathlib import Path
from jinja2 import Template
from backend.app.models import DossierResult


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LegacyLens — {{ dossier.snapshot.repo_name }}</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --critical: #ef4444;
      --high: #f97316;
      --medium: #eab308;
      --low: #3b82f6;
      --success: #10b981;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 2rem 1rem;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 1.5rem;
      margin-bottom: 2rem;
      flex-wrap: wrap;
      gap: 1rem;
    }
    .logo-group h1 { font-size: 1.8rem; font-weight: 800; color: #60a5fa; }
    .logo-group p { color: var(--text-muted); font-size: 0.95rem; }
    .badge {
      display: inline-block;
      padding: 0.25rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .badge-live { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #059669; }
    .badge-example { background: rgba(147, 51, 234, 0.2); color: #c084fc; border: 1px solid #7c3aed; }
    .badge-imported { background: rgba(6, 182, 212, 0.2); color: #22d3ee; border: 1px solid #0891b2; }
    
    .badge-CRITICAL { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626; }
    .badge-HIGH { background: rgba(249, 115, 22, 0.2); color: #fb923c; border: 1px solid #ea580c; }
    .badge-MEDIUM { background: rgba(234, 179, 8, 0.2); color: #facc15; border: 1px solid #ca8a04; }
    .badge-LOW { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid #2563eb; }
    .badge-INFO { background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid #64748b; }

    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1.25rem;
      margin-bottom: 2.5rem;
    }
    .metric-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 0.75rem;
      padding: 1.25rem;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .metric-title { font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-bottom: 0.5rem; }
    .metric-value { font-size: 2rem; font-weight: 800; color: #ffffff; }
    .metric-sub { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem; }

    section { margin-bottom: 3rem; }
    h2 { font-size: 1.4rem; font-weight: 700; margin-bottom: 1.25rem; color: #93c5fd; border-left: 4px solid var(--primary); padding-left: 0.75rem; }

    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 0.75rem;
      padding: 1.5rem;
      margin-bottom: 1.25rem;
    }
    .finding-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.75rem;
      gap: 1rem;
    }
    .finding-title { font-size: 1.1rem; font-weight: 700; color: #ffffff; }
    .finding-desc { color: #cbd5e1; font-size: 0.95rem; margin-bottom: 1rem; }
    
    .code-box {
      background: #090d16;
      border: 1px solid #1e293b;
      border-radius: 0.5rem;
      padding: 0.85rem;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.85rem;
      color: #38bdf8;
      overflow-x: auto;
      margin-bottom: 0.75rem;
    }
    .code-meta { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.35rem; display: flex; justify-content: space-between; }

    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 1rem;
      font-size: 0.9rem;
    }
    th, td {
      padding: 0.75rem 1rem;
      text-align: left;
      border-bottom: 1px solid var(--card-border);
    }
    th {
      background: rgba(30, 41, 59, 0.8);
      color: #93c5fd;
      font-weight: 600;
    }
    tr:hover { background: rgba(51, 65, 85, 0.3); }

    .mermaid-box {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 0.75rem;
      padding: 1.5rem;
      overflow-x: auto;
      text-align: center;
      margin-bottom: 1.5rem;
    }

    footer {
      border-top: 1px solid var(--card-border);
      padding-top: 1.5rem;
      text-align: center;
      color: var(--text-muted);
      font-size: 0.85rem;
    }
  </style>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({ startOnLoad: true, theme: 'dark' });
  </script>
</head>
<body>
  <div class="container">
    <header>
      <div class="logo-group">
        <h1>LegacyLens × IBM Bob 2.0</h1>
        <p>Expediente de Diagnóstico y Migración — <strong>{{ dossier.snapshot.repo_name }}</strong></p>
      </div>
      <div>
        <span class="badge badge-{{ dossier.execution_mode }}">{{ dossier.execution_mode }} mode</span>
        <span style="font-size: 0.85rem; color: var(--text-muted); margin-left: 0.5rem;">Job ID: {{ dossier.job_id }}</span>
      </div>
    </header>

    <!-- METRICS -->
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-title">Fidelidad de Evidencia</div>
        <div class="metric-value" style="color: #34d399;">{{ (dossier.validation_report.fidelity_ratio * 100)|round(1) }}%</div>
        <div class="metric-sub">{{ dossier.validation_report.valid_references }} / {{ dossier.validation_report.total_references }} referencias verificadas en código</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Hallazgos Detectados</div>
        <div class="metric-value">{{ dossier.findings|length }}</div>
        <div class="metric-sub">
          {% set critical_count = dossier.findings|selectattr('severity', 'equalto', 'CRITICAL')|list|length %}
          {{ critical_count }} críticos · {{ dossier.findings|length - critical_count }} alta/media
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Esfuerzo Total PERT</div>
        {% set total_pert = dossier.pert_plan|map(attribute='pert_expected_days')|sum %}
        <div class="metric-value" style="color: #60a5fa;">{{ total_pert|round(1) }} d</div>
        <div class="metric-sub">Estimación estadística en 4 fases</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Primer Corte Probado</div>
        <div class="metric-value" style="font-size: 1.25rem; padding-top: 0.5rem; color: #f59e0b;">{{ dossier.selected_first_cut }}</div>
        <div class="metric-sub">Strangler Fig + Pruebas PASS</div>
      </div>
    </div>

    <!-- SECCIÓN 1: HALLAZGOS Y EVIDENCIA FÍSICA -->
    <section>
      <h2>Hallazgos Forenses con Evidencia Física en Código</h2>
      {% for f in dossier.findings %}
      <div class="card">
        <div class="finding-header">
          <div>
            <span class="badge badge-{{ f.severity }}">{{ f.severity }}</span>
            <span style="font-size: 0.85rem; color: var(--text-muted); margin-left: 0.5rem;">{{ f.id }} · {{ f.category }}</span>
            <div class="finding-title" style="margin-top: 0.35rem;">{{ f.title }}</div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 0.8rem; color: var(--text-muted);">Blast Radius CBRS</div>
            <div style="font-size: 1.1rem; font-weight: 800; color: #f87171;">{{ f.blast_radius_score|round(1) }} / 100</div>
          </div>
        </div>
        <p class="finding-desc">{{ f.explanation }}</p>

        {% for ev in f.evidence %}
        <div class="code-meta">
          <span>📄 <strong>{{ ev.path }}</strong>: Líneas {{ ev.line_start }}–{{ ev.line_end }}</span>
          <span>Observado directamente en fuente</span>
        </div>
        <pre class="code-box"><code>{{ ev.fragment }}</code></pre>
        {% endfor %}

        <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.5rem;">
          <strong>Método de verificación:</strong> {{ f.verification_method }}
        </div>
      </div>
      {% endfor %}
    </section>

    <!-- SECCIÓN 2: DIAGRAMAS MERMAID -->
    {% if dossier.mermaid_er_diagram %}
    <section>
      <h2>Diagrama Entidad-Relación Observable</h2>
      <div class="mermaid-box">
        <pre class="mermaid">
{{ dossier.mermaid_er_diagram }}
        </pre>
      </div>
    </section>
    {% endif %}

    <!-- SECCIÓN 3: OPCIONES ARQUITECTÓNICAS -->
    <section>
      <h2>Opciones Arquitectónicas Comparadas</h2>
      <div class="card" style="padding: 0; overflow-x: auto;">
        <table>
          <thead>
            <tr>
              <th>Opción</th>
              <th>Patrón</th>
              <th>Riesgo</th>
              <th>Esfuerzo</th>
              <th>Ventajas</th>
            </tr>
          </thead>
          <tbody>
            {% for opt in dossier.architecture_options %}
            <tr>
              <td>
                <strong>{{ opt.name }}</strong>
                {% if opt.recommended %}<br><span class="badge" style="background: #10b981; color: white;">Recomendada</span>{% endif %}
              </td>
              <td>{{ opt.pattern }}</td>
              <td><span class="badge badge-{{ opt.risk_level }}">{{ opt.risk_level }}</span></td>
              <td>{{ opt.estimated_effort_days }} días</td>
              <td>
                <ul style="padding-left: 1rem;">
                  {% for pro in opt.pros[:2] %}
                  <li>{{ pro }}</li>
                  {% endfor %}
                </ul>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </section>

    <!-- SECCIÓN 4: PLAN PERT -->
    <section>
      <h2>Plan de Fases de Migración (PERT)</h2>
      <div class="card" style="padding: 0; overflow-x: auto;">
        <table>
          <thead>
            <tr>
              <th>Fase</th>
              <th>Alcance y Entregables</th>
              <th>O / M / P</th>
              <th>Esperado (E)</th>
              <th>Estrategia de Rollback</th>
            </tr>
          </thead>
          <tbody>
            {% for ph in dossier.pert_plan %}
            <tr>
              <td><strong>Fase {{ ph.phase_number }}</strong></td>
              <td>
                <strong>{{ ph.name }}</strong>
                <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem;">{{ ph.description }}</p>
              </td>
              <td>{{ ph.optimistic_days }} / {{ ph.nominal_days }} / {{ ph.pessimistic_days }} d</td>
              <td><strong>{{ ph.pert_expected_days }} días</strong></td>
              <td><small>{{ ph.rollback_strategy }}</small></td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </section>

    <footer>
      <p>Generado deterministamente por <strong>LegacyLens</strong> × <strong>IBM Bob Shell 2.0</strong> · Hackathon IBM Bob 2.0</p>
      <p style="margin-top: 0.25rem;">SHA256: <code>{{ dossier.snapshot.snapshot_sha256 }}</code></p>
    </footer>
  </div>
</body>
</html>
"""


def render_dossier_to_html(dossier: DossierResult, output_path: Path | str) -> Path:
    """Renderiza el expediente a un archivo HTML autónomo."""
    template = Template(HTML_TEMPLATE)
    html_content = template.render(dossier=dossier)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html_content, encoding="utf-8")
    return out_file
