"""External adapters.

- bob_adapter: invokes Bob Shell (`bob run`) through subprocess with an argument list,
  prompt on stdin, timeout and mode; supports live runs and JSON import (D12, D-04).
- telemetry_mcp: external telemetry through FastMCP (D17, not wired into the product).
"""
