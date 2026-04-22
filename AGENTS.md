# AGENTS Guide - DATOS_CONSIGNACION

This guide is for coding agents operating in this repository.
Follow this file first, then repository-local conventions in nearby code.

## 1) Project shape

- App architecture is monolithic: `src/app.py` contains routing, UI, DB logic, and utility helpers.
- Runtime wrapper is `run.py` (used for packaged execution path handling).
- Tests live in `tests/` and use pytest.
- Local SQLite data is in `data/datos_consignacion.db`.
- Build artifacts in `build/` and `dist/` are generated; do not edit them manually.
- PyInstaller specs: `MiAppStreamlit.spec` and `run.spec`.

## 2) Setup commands

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Notes:
- `requirements.txt` is UTF-16 LE encoded; preserve encoding when editing.
- Python target is 3.10+.

## 3) Build / run / test / lint commands

Run app in dev mode:

```bash
streamlit run src/app.py
```

Run app via wrapper (packaging path validation):

```bash
python run.py
```

Build distributable:

```bash
pyinstaller MiAppStreamlit.spec
```

Run all tests:

```bash
pytest
```

Run a single test file (important):

```bash
pytest tests/test_generate_html.py
```

Run a single test function (important):

```bash
pytest tests/test_generate_html.py::test_generate_html_rotates_messages
```

Run by keyword:

```bash
pytest -k "sanitize and not live"
```

Fail-fast run used by maintainers:

```bash
pytest --maxfail=1 --disable-warnings
```

Live scraping check (network dependent, not standard unit suite):

```bash
python tests/test_scrape_live.py
```

Lint/format status in this repo:
- No configured `ruff`, `black`, `flake8`, `mypy`, or `pyproject.toml` was found.
- Do not add new lint tooling/config unless explicitly asked.
- Optional quick syntax check:

```bash
python -m compileall src tests
```

## 4) Testing conventions to follow

- Unit tests often mock heavy deps before `import src.app`.
- Common pattern: patch `sys.modules` for `streamlit`, `requests`, `bs4`, and sometimes `pandas`.
- Prefer in-memory SQLite (`sqlite3.connect(":memory:")`) for deterministic DB tests.
- Patch `get_connection()` in tests instead of touching real DB files.
- Mock network calls for scraping tests; never require internet for core unit tests.
- Validate both function return values and DB side effects.
- Name tests as `tests/test_<feature>.py` and `test_<behavior>()`.

## 5) Code style: imports and structure

- Use PEP 8 basics: 4 spaces, clear spacing, readable line length.
- Import order: standard library, third-party, local modules.
- Prefer explicit imports; avoid wildcard imports.
- Keep Streamlit UI code inside `render_*` helpers.
- Keep business logic/helpers separate from widget declaration blocks where possible.
- Reuse existing helper names/patterns before creating new abstractions.

## 6) Code style: naming, types, docs

- `snake_case` for functions/variables, `CapWords` for classes, `UPPER_SNAKE_CASE` for constants.
- Continue existing function naming style (`render_*`, `fetch_*`, `add_*`, `update_*`, `delete_*`).
- Add type hints for new or modified helper functions when practical.
- Prefer modern built-in generics (`list[str]`, `dict[str, Any]`, `tuple[...]`).
- Add concise docstrings for reusable business helpers.
- Add comments only for non-obvious logic; avoid restating code.

## 7) Error handling and resilience

- Prefer specific exception types over broad `except Exception`.
- For UI actions, present failures via `st.error(...)` with actionable text.
- For helper/data functions, return clear status values or raise consistently.
- Keep DB writes transactional: commit on success, rollback on failure-sensitive paths.
- Never silently swallow exceptions.
- Validate/normalize user-derived inputs before persistence.

## 8) Database and security rules

- Always use parameterized SQL (`?` placeholders), never SQL string interpolation.
- Keep role checks intact (`admin` vs `user`) for privileged/destructive operations.
- Preserve existing normalization behavior for phones and URLs.
- Do not commit secrets, credentials, or production personal data.
- Store secrets in `.streamlit/secrets.toml` or environment variables.

## 9) UI and Streamlit behavior

- Keep explicit empty/loading/error states (`st.info`, `st.warning`, `st.error`).
- Preserve established sidebar/nav patterns and existing page gating by role.
- Keep CSS/style changes coherent with current visual system unless redesign is requested.
- Avoid introducing heavy frontend frameworks; this app is Streamlit-first.

## 10) Agent workflow expectations

- Make minimal, scoped changes that match local code patterns.
- Do not refactor unrelated areas while implementing a focused request.
- Update or add tests when behavior changes.
- Prefer deterministic tests and avoid new external dependencies unless requested.
- If required tooling is missing, choose safest defaults and document assumptions.

## 11) Cursor and Copilot instruction files

Checked in this repository:
- `.cursor/rules/` -> not present.
- `.cursorrules` -> not present.
- `.github/copilot-instructions.md` -> not present.

If any of these files are added later, treat them as higher-priority agent instructions and update this AGENTS guide.
