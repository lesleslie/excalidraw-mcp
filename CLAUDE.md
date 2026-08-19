# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

For a shorter, tool-neutral bootstrap document, start with `AGENTS.md`.

## Project Overview

`excalidraw-mcp` is a dual-language MCP server for manipulating a live Excalidraw canvas.

Core parts:

- `excalidraw_mcp/`: Python FastMCP server and canvas-process supervision
- `src/`: TypeScript canvas server, HTTP API, and WebSocket coordination
- `frontend/src/`: React Excalidraw client

The Python server owns the MCP protocol surface and supervises the TypeScript canvas service.

## Key Constraints

- The Python and TypeScript halves must stay in sync on payload shape and element semantics.
- The canvas server is process-managed by the MCP server unless the task explicitly targets standalone canvas work.
- Element storage is in-memory; do not assume persistence unless you are adding it intentionally.
- Environment-driven security settings must remain configuration, not code constants.

## Development Commands

### Setup

```bash
uv sync
npm install
npm run build
```

### Main Workflows

```bash
uv run python excalidraw_mcp/server.py
npm run dev
npm run canvas
npm run production
npm run type-check
uv run pytest
```

### Useful Validation

```bash
npm run build:frontend
npm run build:server
npm run test:coverage
uv run ruff check --fix
```

## Quality Workflow

Use Crackerjack-aligned Python quality checks for the repo's CI path, and pair them with the TypeScript build, type-check, and test flow whenever a change crosses stacks.

## Architecture Notes

The runtime path is:

- MCP tool call in Python
- HTTP call to the TypeScript canvas API
- WebSocket broadcast to connected clients
- canvas update in the React frontend

Keep responsibilities split this way:

- Python: MCP interface, validation, process lifecycle, recovery behavior
- TypeScript server: element state, HTTP API, WebSocket fanout
- React: rendering and client synchronization

If a change crosses layers, update the shared types and confirm the request and response contracts still match.

## MCP Tool Guidance

The tool surface centers on:

- element CRUD
- batch creation
- grouping, alignment, distribution, and locking
- scene or resource inspection

When adding or modifying tools:

- validate coordinates, element identifiers, and enum-like options strictly
- preserve fast failure with actionable errors
- avoid burying canvas-server assumptions inside MCP tool code
- keep transport and schema changes explicit across Python and TypeScript

## Testing Focus

- Python changes: `uv run pytest`
- TypeScript or frontend changes: `npm run type-check` and relevant JS/TS tests
- cross-layer changes: validate both the Python MCP side and the canvas API path
- process-management changes: verify startup, health checks, and shutdown behavior explicitly

## Tool Profile System

excalidraw-mcp adopts the `mcp-common` ToolProfile dispatch (W4.2 — Tier-A trivial). The Python MCP server exposes a configurable subset of tools based on the `EXCALIDRAW_TOOL_PROFILE` environment variable, controlling context consumption while preserving the health probe at every tier.

### Profile Mapping (Tier-A Trivial — 3-tier)

| Profile  | Tools exposed                                                                              | Use case                                       |
|----------|--------------------------------------------------------------------------------------------|------------------------------------------------|
| MINIMAL  | `health_check`, `discover_tools`                                                          | Control-plane / health-probe deployments       |
| STANDARD | All 12 canvas tools + `health_check` + `discover_tools`                                    | Typical LLM client deployments                 |
| FULL     | All 12 canvas tools + `health_check` + `discover_tools` (default — matches STANDARD)        | Default behavior, no profile gating            |

### Implementation Files

- `excalidraw_mcp/tools/__init__.py` — `register_health_tool(mcp, config)` (MCP `health_check` + HTTP `/health` route) and `register_canvas_tools(mcp, config)` (12 canvas tools via `MCPToolsManager`).
- `excalidraw_mcp/tools/profiles.py` — `_GROUP_REGISTRY` (SSOT for group keys), `PROFILE_REGISTRATIONS`, `apply_excalidraw_tool_profile(server, config)` async entry point.
- `excalidraw_mcp/server.py::create_app(config, server)` — async production path that calls `apply_excalidraw_tool_profile`. The caller-supplied `config` is threaded through (NOT re-loaded from env).

### W4.1 Lessons Applied

- **MINIMAL includes the health tool** (NOT just the HTTP `/health` route) — `essential_tool_names={"health_check"}` enforces this at every profile.
- **Caller-supplied config is preserved** — `create_app(config, server)` threads the config object through to every registration callback. Tests use monkey-patched `Config.__init__` tracking to catch silent re-loads.
- **Production path uses `_apply_tool_profile` (async), NOT `apply_tool_profile` (sync)** — the sync wrapper raises `RuntimeError` inside an event loop.

### Tests

`tests/unit/test_tool_profile.py` (31 tests) covers structural guards, AST keystone checks, profile semantics, and real production-path tests. See `docs/architecture/tool-profile-rationale.md` for the full rationale.

## Security & Operations

Configuration such as `AUTH_ENABLED`, `JWT_SECRET`, `ALLOWED_ORIGINS`, and server URLs should remain environment-driven. If you add a new setting, update the config surface, docs, and examples together.

Keep deep monitoring or deployment runbooks in repo docs, not in this file.
