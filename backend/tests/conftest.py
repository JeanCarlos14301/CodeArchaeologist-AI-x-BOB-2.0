"""The tests exercise the example/imported modes, which are off by default in production.

They are enabled at import time (not only through a fixture) because some test modules create `app` on import.
"""

import os

os.environ.setdefault("ALLOW_NON_LIVE_MODES", "true")
