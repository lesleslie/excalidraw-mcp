# Repository Guidelines

## Project Structure & Module Organization

Excalidraw MCP couples a Python FastMCP backend with a TypeScript canvas stack. Core FastMCP logic, CLI entry points, and process supervision live in `excalidraw_mcp/`. The realtime canvas service and shared TS utilities are in `src/`, while the React surface that renders Excalidraw sits under `frontend/src/`. Python automated tests reside in `tests/` (unit, integration, e2e, performance, security folders); TypeScript and UI tests live in `test/`. Generated builds are shipped in `dist/`, and example agent payloads live in `examples/` and `example.mcp.json`.

## Build, Test, and Development Commands

- `uv sync && npm install` install Python and Node dependencies.
- `uv run python excalidraw_mcp/server.py` launches the MCP server and supervises the canvas service.
- `npm run dev` runs TypeScript watch mode plus Vite for iterative UI work; `npm run build` compiles frontend + server assets.
- `npm run canvas` starts only the built canvas server; `npm run production` rebuilds and boots both services.
- `uv run pytest` executes the Python suite (coverage reports emitted to `htmlcov/` and `coverage.xml`).

## Coding Style & Naming Conventions

Python code targets 3.13+, uses 4-space indentation, exhaustive type hints, `import typing as t`, f-strings, and `pathlib`. Run `uv run ruff check --fix` before committing; keep modules small and single-purpose per `RULES.md`. TypeScript follows strict `tsconfig` settings with 2-space indentation, snake-case filenames for back-end modules (e.g., `storage/index.ts`) and PascalCase for React components. Prefer interfaces over type aliases, const assertions for invariants, and Zod schemas for runtime validation.

## Testing Guidelines

Pytest is configured in `pyproject.toml` with `--cov-fail-under=85`; keep new Python tests in `tests/test_*.py` and mark them (`@pytest.mark.integration`, etc.) so CI filtering works. Jest enforces 70% global coverage (`jest.config.cjs`); add `.test.ts` files under `test/` and import stubs from `test/setup.ts`. Use `npm run test:coverage` for TS coverage and `npm run type-check` before submitting runtime changes.

## Commit & Pull Request Guidelines

Follow the conventional `type(scope): detail` summary seen in recent history (`test(test): ...`, `docs(config): ...`). Keep messages imperative and limit to ~72 characters; expand context in the body if needed. Pull requests should describe intent, link to issues, list the commands executed (e.g., `uv run pytest`, `npm run test:coverage`), and add screenshots or screen captures when UI behaviour changes. Reference any new environment variables or migrations explicitly.

## Security & Configuration Tips

Canvas security settings are environment-driven (`AUTH_ENABLED`, `JWT_SECRET`, `ALLOWED_ORIGINS`, rate-limit knobs). Provide sane defaults for development but never commit real secrets. Update `src/config.ts` when adding new env toggles, and document them in `README.md` and `.env.example`. Ensure CORS and JWT settings of the canvas match the MCP server host you deploy.
