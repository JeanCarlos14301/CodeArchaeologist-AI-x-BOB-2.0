import os

SECRET_KEY = "DEMO_ONLY_NOT_A_REAL_SECRET"
PAYMENT_GATEWAY_KEY = "DEMO_ONLY_NOT_A_REAL_GATEWAY_KEY"
DATABASE = os.environ.get("FACTURAYA_DB", os.path.join(os.path.dirname(__file__), "facturaya.sqlite3"))
