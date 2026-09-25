---
name: legacy-flask-patterns
description: >
  Catalog of common architectural anti-patterns, security pitfalls, 
  and obsolete practices in legacy Python 3 + Flask + SQLite applications.
metadata:
  origin: CodeArchaeologist
---

# Legacy Flask & SQLite Anti-Patterns Catalog

A forensic reference of structural, operational, and security anti-patterns frequently found in aging Flask 1.x and SQLite applications.

## When to Use

- When auditing Flask codebases to identify technical debt and structural rot.
- When categorizing findings for the technical dossier.
- When formulating migration strategies to modern frameworks (e.g. FastAPI / modern Python 3.11+).

## Common Anti-Patterns

### 1. Monolithic God-Object `app.py`
- **Pattern**: The entire application (routes, models, database helpers, templates, configuration) is packed into a single 800+ line file.
- **Symptom**: `app = Flask(__name__)` defined globally at line 10, followed by 30+ route functions importing circular dependencies.
- **Consequence**: Inability to write isolated unit tests; high blast radius for any modification.
- **Remediation**: Modularize using Flask Blueprints or refactor into FastAPI routers with an Application Factory pattern.

### 2. Ad-hoc SQLite Connection Lifecycle
- **Pattern**: Opening connections ad-hoc inside view functions without context management or teardown hooks.
  ```python
  # ANTI-PATTERN
  @app.route('/items')
  def get_items():
      conn = sqlite3.connect('app.db')
      cursor = conn.cursor()
      cursor.execute("SELECT * FROM items")
      # Missing conn.close() if an exception is raised!
  ```
- **Consequence**: Connection leaks, database locks (`database is locked` error), thread-safety violations.
- **Remediation**: Use `g.db` with `@app.teardown_appcontext`, connection pooling, or modern ORM/async database drivers.

### 3. Business Logic & Raw SQL Embedded in View Handlers
- **Pattern**: Route functions directly parse HTTP requests, execute raw SQL queries, perform calculations, and format the response all in one place.
- **Symptom**: Functions exceeding 70 lines with nested SQL strings and direct dictionary manipulation.
- **Consequence**: Business logic cannot be tested without simulating the full HTTP stack; code duplication across endpoints.
- **Remediation**: Extract a clean Service/Repository layer. View functions should only parse input, delegate to services, and format output.

### 4. Global Mutable State via Module-Level Variables
- **Pattern**: Using global lists or dictionaries to cache items or track session state across HTTP requests.
  ```python
  # ANTI-PATTERN
  ACTIVE_USERS = {}  # Global dict mutated across concurrent requests
  ```
- **Consequence**: Race conditions under multi-process WSGI servers (Gunicorn, uWSGI), memory leaks, non-deterministic bugs.
- **Remediation**: Externalize shared state to Redis or use database-backed sessions.

### 5. Absence of Application Factory (`create_app`)
- **Pattern**: Hardcoded global `app = Flask(__name__)` instantiated at module load time with configurations read directly from environment or defaults.
- **Consequence**: Tests cannot run with separate in-memory databases or alternate configurations without monkey-patching.
- **Remediation**: Implement `def create_app(config_name=None):` to support multiple application instances.

### 6. Missing Request Validation & Schemas
- **Pattern**: Manual parsing of `request.form['field']` or `request.args.get('id')` with implicit type coercion and missing validation.
  ```python
  # ANTI-PATTERN
  user_id = int(request.args.get('id'))  # Crashes with ValueError if non-numeric
  ```
- **Consequence**: Unhandled 500 errors, vulnerability to edge-case inputs.
- **Remediation**: Adopt Pydantic v2 schemas for strict input parsing and automated error responses.

### 7. Insecure Default Secret Keys
- **Pattern**: `app.secret_key = 'development-key'` or `app.secret_key = 'secret'` hardcoded in source.
- **Consequence**: Anyone can forge signed Flask session cookies to impersonate arbitrary users or administrators.
- **Remediation**: Require `SECRET_KEY` from environment variables, halting startup if absent in production.

## Detection Heuristics

| Pattern | Ripgrep Search Heuristic | File Target |
|---|---|---|
| Ad-hoc connection | `rg 'sqlite3\.connect\('` inside function bodies | `routes/*.py`, `app.py` |
| Monolithic app | `wc -l app.py` (> 400 lines) | `app.py` |
| Missing factory | `rg '^app\s*=\s*Flask\('` | Top-level files |
| Hardcoded secret | `rg -i 'secret_key\s*=\s*["\x27]'` | `app.py`, `config.py` |
| Unsafe query | `rg '\.execute\(f["\x27]|format\('` | All `.py` files |
