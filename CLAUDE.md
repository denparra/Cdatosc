# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app (dev mode)
streamlit run src/app.py

# Run the app via wrapper (validates packaged entrypoint paths)
python run.py

# Run all tests
pytest

# Run a single test file
pytest tests/test_generate_html.py

# Run with fail-fast
pytest --maxfail=1 --disable-warnings

# Build distributable
pyinstaller MiAppStreamlit.spec
```

## Architecture

`src/app.py` is the **entire application** — a single-file Streamlit monolith acting as router, controller, and UI. There are no separate modules.

**Execution flow on every page load:**
1. CSS injection and global config at module top-level (runs on every rerender)
2. `create_tables()` initializes the SQLite schema if missing
3. `st.session_state['user']` check — forces Login view if unauthenticated
4. `st.sidebar` radio → `page` variable → `if/elif` block dispatches to `render_*()` functions

**Navigation is gated by role**: `admin` users see all pages (Sanitizar, Gestión de Usuarios, Lista Negra); `user` role sees only the operational pages.

**Database**: Single SQLite file at `data/datos_consignacion.db`. All queries use parameterized statements. Key tables: `links_contactos` (master groupers/campaigns), `contactos` (prospects+vehicles), `mensajes` (WhatsApp templates), `clientes_interesados` (CRM leads), `contactos_restringidos` (blocklist), `export_logs` (audit). Default credentials: `admin/admin` and `test/test`.

**Key utility functions in `app.py`:**
- `get_connection()` — returns SQLite connection; mockable in tests
- `resource_path(relative_path)` — resolves paths for both dev (`os.path.abspath(".")`) and PyInstaller bundles (`sys._MEIPASS`)
- `normalize_phone(value)` — strips non-digits, trims to last 9 digits (Chilean format)
- `sanitize_vehicle_link(url)` — strips query strings and fragments from Chileautos URLs

## Testing Patterns

Tests mock Streamlit and external dependencies at import time using a shared `import_app()` helper. Every test file follows this pattern:

```python
def import_app():
    with patch.dict(sys.modules, {
        "streamlit": MagicMock(),
        "streamlit.components": MagicMock(),
        "streamlit.components.v1": MagicMock(),
        "requests": MagicMock(),
        "bs4": MagicMock(),
        "pandas": MagicMock(),
    }):
        sys.path.insert(0, ROOT)
        import src.app
        importlib.reload(src.app)
        sys.path.remove(ROOT)
        return src.app
```

Database isolation uses in-memory SQLite + `patch.object(app, "get_connection", return_value=conn)`. Never use the real `data/datos_consignacion.db` in tests.

## Conventions

- UI sections go in `render_*()` functions (e.g., `render_interested_clients_page()`)
- Commit prefixes: `feat:`, `fix:`, `chore:` (Conventional Commits)
- Secrets/credentials go in `.streamlit/secrets.toml`, never in `src/app.py`
- `build/` and `dist/` are PyInstaller artifacts — never edit manually
