# Repository Guidelines
## Project Structure & Module Organization
- `src/app.py` is the Streamlit entrypoint; keep new UI sections encapsulated in helper functions to avoid tightly coupled callbacks.
- `tests/` contains pytest modules that mirror link sanitizing, contact search, and HTML generation; expand alongside new functionality.
- `data/` stores sample spreadsheets and cached exports for local experimentation; treat it as read-only fixtures unless a test requires dedicated input.
- `docs/` collects reference notes and screenshots; update it with architecture diagrams when workflows change.
- `build/` and `dist/` hold PyInstaller artifacts generated from `MiAppStreamlit.spec` or `run.spec`; never hand-edit bundled files.

## Build, Test, and Development Commands
- `python -m venv .venv && .\.venv\Scripts\activate` prepares a fresh virtual environment.
- `pip install -r requirements.txt` installs Streamlit, Playwright, and supporting utilities.
- `streamlit run src/app.py` launches the app locally; use `python run.py` when validating the packaged entrypoint.
- `pytest` exercises the regression suite; narrow scope with `pytest tests/test_generate_html.py` during focused work.
- `pyinstaller MiAppStreamlit.spec` produces the distributable in `dist/`; rerun after shipping new resources.

## Coding Style & Naming Conventions
- Follow PEP 8: 4-space indentation, `snake_case` for functions, `CapWords` for classes, and `UPPER_SNAKE` for shared constants.
- Keep Streamlit component rendering in helper functions such as `render_*` blocks to simplify reuse and testing.
- Prefer type hints for new helpers and document non-obvious business rules with concise comments near the logic.

## Testing Guidelines
- Extend the pytest suite whenever you add or alter business logic; mirror source modules in `tests/` with `test_<module>.py` files.
- Mock external services and file I/O so tests remain deterministic across environments.
- Run `pytest --maxfail=1 --disable-warnings` before pushing; maintain coverage for critical generators (`generate_html`, `sanitize_links`) by exercising new branches.

## Commit & Pull Request Guidelines
- Use concise, descriptive commit subjects; prefer Conventional Commit prefixes (`feat:`, `fix:`, `chore:`) observed in history.
- Ensure every PR summary explains the user-facing effect, lists affected pathways, and links the tracked issue.
- Attach before/after screenshots or terminal snippets for UI or packaging changes, and include the latest `pytest` output in the PR checklist.

## Security & Data Handling
- Keep `data/` free of production records; scrub personal identifiers before committing.
- Store secrets in local `.streamlit/secrets.toml` or environment variables; never hard-code tokens inside `src/app.py`.
