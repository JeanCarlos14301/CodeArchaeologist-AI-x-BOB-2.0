"""Adaptadores externos.

- bob_adapter: invoca Bob Shell (`bob run`) por subprocess con lista de argumentos,
  prompt por stdin, timeout y modo; soporta ejecución live e importación de JSON (D12, D-04).
- telemetry_mcp: telemetría externa vía FastMCP (D17).
"""
