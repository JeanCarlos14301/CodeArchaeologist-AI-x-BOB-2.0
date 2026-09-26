"""Las pruebas existentes ejercitan los modos example/imported y el motor /api/jobs, apagados por defecto.

Se activan al importar (no solo por fixture) porque algunos módulos de prueba crean `app` al importarse.
"""

import os

os.environ.setdefault("ALLOW_NON_LIVE_MODES", "true")
os.environ.setdefault("ENABLE_JOBS_API", "true")
