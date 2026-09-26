"""Las pruebas ejercitan los modos example/imported, apagados por defecto en producción.

Se activan al importar (no solo por fixture) porque algunos módulos de prueba crean `app` al importarse.
"""

import os

os.environ.setdefault("ALLOW_NON_LIVE_MODES", "true")
