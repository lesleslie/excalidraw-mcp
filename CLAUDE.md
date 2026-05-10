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

## Security & Operations

Configuration such as `AUTH_ENABLED`, `JWT_SECRET`, `ALLOWED_ORIGINS`, and server URLs should remain environment-driven. If you add a new setting, update the config surface, docs, and examples together.

Keep deep monitoring or deployment runbooks in repo docs, not in this file.
