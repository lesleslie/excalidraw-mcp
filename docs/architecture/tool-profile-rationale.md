# excalidraw-mcp Tool Profile Adoption (W4.2)

## Context

excalidraw-mcp is a Tier-A "trivial" repo for the W4 MCP tool profile
adoption wave. The goal is to expose a configurable subset of the
excalidraw MCP server's tool surface to LLM clients based on the
`EXCALIDRAW_TOOL_PROFILE` environment variable, controlling context-window
consumption while preserving the health probe at every tier.

This document records the design decisions and the W4.1 / W2b.3 lessons
that shaped the implementation. It lives under `docs/architecture/`
(not `.claude/decisions/`) so it ships with the repo.

## Tool Surface (Tier-A Trivial — 3-tier Mapping)

excalidraw-mcp exposes 12 MCP tools plus 1 health probe plus 1
`discover_tools` meta-tool (added by the W0 helper):

| Tool name             | Group         | Description                          |
|-----------------------|---------------|--------------------------------------|
| `create_element`      | canvas_tools  | Create a canvas element              |
| `update_element`      | canvas_tools  | Update an existing element           |
| `delete_element`      | canvas_tools  | Delete an element                    |
| `query_elements`      | canvas_tools  | Query elements from the canvas       |
| `batch_create_elements` | canvas_tools | Batch-create elements                |
| `group_elements`      | canvas_tools  | Group multiple elements              |
| `ungroup_elements`    | canvas_tools  | Ungroup a group                      |
| `align_elements`      | canvas_tools  | Align elements to a position         |
| `distribute_elements` | canvas_tools  | Distribute elements evenly           |
| `lock_elements`       | canvas_tools  | Lock elements (prevent modification) |
| `unlock_elements`     | canvas_tools  | Unlock elements                      |
| `get_resource`        | canvas_tools  | Get canvas resources                 |
| `health_check`        | health_tools  | MCP-level health probe (NEW)         |
| `discover_tools`      | W0 helper     | Discover registered tools (meta)     |

The W4 spec mapping for Tier-A trivial is canonical:

```text
MINIMAL  = ["health_tools"]                          (health probe only)
STANDARD = FULL_REGISTRATIONS                        (all 12 + health + discover)
FULL     = ALL_TOOLS                                 (same, via register_all_fn)
```

`MINIMAL` MUST expose the MCP `health_check` tool, NOT just the
HTTP `/health` route. The HTTP route is for orchestrator readiness
probes (Kubernetes, launchd); the MCP tool is for LLM clients. The
W4.1 reviewer explicitly caught an implementer who rationalized
`MINIMAL=empty` because the HTTP route was already there — that
violated the spec.

## Why This Mapping

### MINIMAL=health

LLM clients at MINIMAL profile (control-plane / health-probe
deployments) need exactly one thing: the ability to confirm the
excalidraw-mcp server is alive. The MCP `health_check` tool is the
LLM-protocol equivalent of the HTTP `/health` route; both should be
present at MINIMAL. Exposing the canvas tools at MINIMAL would
defeat the purpose of the profile (context reduction).

### STANDARD/FULL=all

excalidraw-mcp has no concept of "advanced" vs "core" canvas tools.
The canvas operations form a single workflow — element creation,
querying, grouping, locking — and any user invoking one will likely
invoke others in the same session. Tier-A trivial: same set at
STANDARD and FULL.

## Implementation Architecture

### `_GROUP_REGISTRY` — Single Source of Truth

`excalidraw_mcp/tools/profiles.py` declares:

```python
_GROUP_REGISTRY: list[tuple[str, str]] = [
    ("health_tools", "register_health_tool"),
    ("canvas_tools", "register_canvas_tools"),
]
```

Both `_build_registration_map` and `register_all_tool_groups` derive
from this constant — no name-specific conditionals. Adding a new
group requires editing only this constant.

### Production Path Uses Async Helper (W2b.3 Keystone)

`excalidraw_mcp/server.py::create_app(config, server)` is async and
delegates to `apply_excalidraw_tool_profile(mcp, config)` which calls
`_apply_tool_profile` (the async helper from `mcp_common.tools.dispatch`).

The sync `apply_tool_profile` wrapper raises `RuntimeError` when called
from inside a running event loop (e.g. inside pytest-asyncio tests).
The async helper is the ONLY correct production entry point.

The structural test `test_server_awaits_apply_excalidraw_tool_profile`
walks the AST and asserts the production call is wrapped in
`ast.Await(value=ast.Call(...))` — NOT just a call count check that
would pass for a sync-wrapper regression (the W3.2 round-1 fix).

### Caller-Supplied Config Is Preserved (W4.1 Round-1 Fix)

`create_app(config, server)` threads the caller's `Config` instance
through to `_build_registration_map(config)` and
`register_all_tool_groups(server, config)`. Registration callbacks
capture the caller's config via default-argument lambda binding
(mirroring the W3.1 graphics-mcp pattern).

A test (`test_caller_supplied_config_is_preserved`) monkey-patches
`Config.__init__` to track invocations. If registration paths
silently re-construct `Config()` from the environment (the W4.1
round-1 regression), the test fails loud.

### Health Probe Registration Is Split Out

`excalidraw_mcp/tools/__init__.py::register_health_tool(mcp, config)`
registers ONLY:
- The MCP `health_check` tool (returns `status`, `service`,
  `version`, `canvas` state)
- The HTTP `/health` route via `mcp_common.health.register_http_health_route`

`register_canvas_tools(mcp, config)` wraps `MCPToolsManager(mcp)` to
register the 12 canvas tools. Backward compatibility is preserved:
`MCPToolsManager` is still importable from `excalidraw_mcp.mcp_tools`
for any legacy callers.

### `essential_tool_names={"health_check"}`

The W0 helper supports a subset check that asserts the listed tool
names are present after dispatch. `apply_excalidraw_tool_profile` sets
`essential_tool_names={"health_check"}` to enforce the W4 spec
invariant that `health_check` MUST be present at every profile. If a
future refactor accidentally drops the health tool from a profile, the
helper raises `ValueError` with a clear message.

## Files Touched

| File                                       | Change                                            |
|--------------------------------------------|---------------------------------------------------|
| `excalidraw_mcp/tools/__init__.py`         | NEW — `register_health_tool` + `register_canvas_tools` |
| `excalidraw_mcp/tools/profiles.py`         | NEW — `_GROUP_REGISTRY` + profile dispatch        |
| `excalidraw_mcp/server.py`                 | MODIFIED — async `create_app(config, server)` + tool profile integration |
| `tests/unit/test_tool_profile.py`          | NEW — 30 tests covering structural guards, AST keystone checks, and real-path profile tests |
| `docs/architecture/tool-profile-rationale.md` | NEW — this document                            |
| `CLAUDE.md`                                | MODIFIED — "Tool Profile System" subsection       |
| `pyproject.toml`                           | MODIFIED — `mcp-common>=0.18.0`                   |

## Test Summary

30 tests in `tests/unit/test_tool_profile.py` covering:

- Structural guards (files exist, dicts defined, types match)
- AST keystone (production path uses async helper)
- Profile semantics (MINIMAL=health, STANDARD/FULL=all)
- Caller-supplied config preservation (W4.1 round-1 regression)
- Real production-path tests for FULL, STANDARD, and MINIMAL

## References

- W2b.3 spline lesson — production path MUST use async helper
- W3.1 graphics-mcp lesson — 2-arg register fns require lambda binding
- W3.2 langsmith-mcp lesson — AST guard must structurally check `await`
- W4.1 css-mcp lesson — explicit spec mapping, no rationalization
- mcp-common 0.18.0 — `_apply_tool_profile` async helper