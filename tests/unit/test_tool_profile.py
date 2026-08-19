"""Tests for excalidraw-mcp's ToolProfile adoption (W4.2).

Pins the W4 Tier-A trivial mapping for excalidraw-mcp:
- MINIMAL  = ["health_tools"] (health probe only)
- STANDARD = FULL_REGISTRATIONS (all 12 canvas tools + health_check)
- FULL     = ALL_TOOLS (same as STANDARD via register_all_fn)

And verifies the W2b.3 keystone: the production path uses the async
``_apply_tool_profile`` helper (NOT the sync ``apply_tool_profile``
wrapper, which raises ``RuntimeError`` when called from inside a
running event loop).

See ``docs/architecture/tool-profile-rationale.md`` for the rationale.
"""

from __future__ import annotations

import ast
import inspect
import os
import pathlib

import pytest

from excalidraw_mcp.config import Config
from excalidraw_mcp.server import create_app
from excalidraw_mcp.tools.profiles import (
    _GROUP_REGISTRY,
    FULL_REGISTRATIONS,
    MINIMAL_REGISTRATIONS,
    PROFILE_REGISTRATIONS,
    _build_registration_map,
    apply_excalidraw_tool_profile,
    register_all_tool_groups,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVER_PY = REPO_ROOT / "excalidraw_mcp" / "server.py"
PROFILES_PY = REPO_ROOT / "excalidraw_mcp" / "tools" / "profiles.py"
TOOLS_INIT_PY = REPO_ROOT / "excalidraw_mcp" / "tools" / "__init__.py"
PYPROJECT_TOML = REPO_ROOT / "pyproject.toml"


# ---------------------------------------------------------------------------
# Structural / AST guards
# ---------------------------------------------------------------------------


def test_profiles_py_exists() -> None:
    """excalidraw_mcp/tools/profiles.py must exist."""
    assert PROFILES_PY.exists(), f"Missing {PROFILES_PY}"


def test_tools_init_exists() -> None:
    """excalidraw_mcp/tools/__init__.py must exist."""
    assert TOOLS_INIT_PY.exists(), f"Missing {TOOLS_INIT_PY}"


def test_profiles_py_defines_profile_registrations() -> None:
    """PROFILE_REGISTRATIONS dict must be defined with all 3 tiers."""
    assert isinstance(PROFILE_REGISTRATIONS, dict)
    assert set(PROFILE_REGISTRATIONS.keys()) == {"minimal", "standard", "full"}


def test_profiles_py_defines_group_registry() -> None:
    """_GROUP_REGISTRY must contain health_tools + canvas_tools."""
    assert isinstance(_GROUP_REGISTRY, list)
    keys = [key for key, _ in _GROUP_REGISTRY]
    assert "health_tools" in keys, "_GROUP_REGISTRY must include health_tools"
    assert "canvas_tools" in keys, "_GROUP_REGISTRY must include canvas_tools"


def test_profiles_py_defines_build_registration_map() -> None:
    """_build_registration_map fn must be defined."""
    assert callable(_build_registration_map)


def test_profiles_py_defines_register_all_tool_groups() -> None:
    """register_all_tool_groups fn must be defined."""
    assert callable(register_all_tool_groups)


def test_profiles_py_defines_apply_excalidraw_tool_profile() -> None:
    """async apply_excalidraw_tool_profile fn must be defined."""
    assert callable(apply_excalidraw_tool_profile)
    assert inspect.iscoroutinefunction(apply_excalidraw_tool_profile)


def test_profiles_py_references_excalidraw_tool_profile_env_var() -> None:
    """EXCALIDRAW_TOOL_PROFILE env var must be referenced."""
    source = PROFILES_PY.read_text()
    assert "EXCALIDRAW_TOOL_PROFILE" in source


def test_server_uses_async_create_app() -> None:
    """server.py must expose async create_app."""
    source = SERVER_PY.read_text()
    tree = ast.parse(source)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "create_app":
            found = True
            break
    assert found, "Expected `async def create_app(...)` in server.py"


def test_server_awaits_apply_excalidraw_tool_profile() -> None:
    """W2b.3 keystone: production path MUST await apply_excalidraw_tool_profile.

    Structural AST check for ``ast.Await(value=ast.Call(
    func=ast.Name(id="apply_excalidraw_tool_profile")))`` — NOT just call
    count, which would pass for a sync-wrapper regression (the W3.2
    round-1 fix).
    """
    source = SERVER_PY.read_text()
    tree = ast.parse(source)
    found = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Await):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if not (
            isinstance(node.value.func, ast.Name)
            and node.value.func.id == "apply_excalidraw_tool_profile"
        ):
            continue
        found = True
        break
    assert found, (
        "`await apply_excalidraw_tool_profile(...)` not found in server.py. "
        "Production path MUST use the async helper, not the sync wrapper."
    )


def test_server_does_not_use_sync_wrapper() -> None:
    """server.py must NOT call sync ``apply_tool_profile``."""
    source = SERVER_PY.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "apply_tool_profile":
            raise AssertionError(
                "server.py calls bare `apply_tool_profile(...)` (sync wrapper). "
                "Use the async helper: `await apply_excalidraw_tool_profile(app)`."
            )


def test_profiles_uses_async_helper_not_sync_wrapper() -> None:
    """profiles.py must use _apply_tool_profile (async), not apply_tool_profile (sync)."""
    source = PROFILES_PY.read_text()
    assert "_apply_tool_profile" in source, (
        "profiles.py must call _apply_tool_profile (async helper)"
    )
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "apply_tool_profile":
            raise AssertionError(
                "profiles.py calls sync `apply_tool_profile(...)`; "
                "must use async `_apply_tool_profile(...)`"
            )


def test_pyproject_bumps_mcp_common_to_0_18() -> None:
    """pyproject.toml must pin mcp-common>=0.18.0."""
    pyproject = PYPROJECT_TOML.read_text()
    assert "mcp-common>=0.18.0" in pyproject, (
        "pyproject.toml must bump mcp-common to >=0.18.0"
    )


def test_decision_doc_exists_at_tracked_path() -> None:
    """docs/architecture/tool-profile-rationale.md must exist."""
    doc = REPO_ROOT / "docs" / "architecture" / "tool-profile-rationale.md"
    assert doc.exists(), f"Missing rationale doc at {doc}"


def test_tools_init_exposes_register_health_tool() -> None:
    """excalidraw_mcp/tools/__init__.py must expose a register_health_tool callable.

    The W4 spec requires MINIMAL=health, which requires ``health_check``
    to be registerable independently from the canvas tools. If this
    function is missing, MINIMAL cannot expose the health probe.
    """
    import importlib

    tools_module = importlib.import_module("excalidraw_mcp.tools")
    assert hasattr(tools_module, "register_health_tool"), (
        "excalidraw_mcp.tools must expose register_health_tool — "
        "required for MINIMAL=health mapping"
    )
    assert callable(tools_module.register_health_tool)


def test_tools_init_exposes_register_canvas_tools() -> None:
    """excalidraw_mcp/tools/__init__.py must expose a register_canvas_tools callable."""
    import importlib

    tools_module = importlib.import_module("excalidraw_mcp.tools")
    assert hasattr(tools_module, "register_canvas_tools"), (
        "excalidraw_mcp.tools must expose register_canvas_tools — "
        "required for STANDARD/FULL=all mapping"
    )
    assert callable(tools_module.register_canvas_tools)


# ---------------------------------------------------------------------------
# Profile semantics — runtime data structures, NOT source-text greps
# ---------------------------------------------------------------------------


def test_minimal_registrations_contain_health_tools() -> None:
    """MINIMAL profile must include ``health_tools`` (canonical W4.1 mapping)."""
    assert "health_tools" in MINIMAL_REGISTRATIONS, (
        f"MINIMAL must include 'health_tools' (W4.1 canonical: MINIMAL=health); "
        f"got {MINIMAL_REGISTRATIONS}"
    )


def test_profile_registrations_subset_of_map() -> None:
    """Every key in PROFILE_REGISTRATIONS must resolve via registration_map.

    The subset check is non-vacuous: MINIMAL has ``health_tools`` which
    MUST be in the registration map, and FULL_REGISTRATIONS (STANDARD's
    value) MUST be a subset of registration_map keys.
    """
    config = Config()
    mapping = _build_registration_map(config)
    map_keys = set(mapping.keys())

    # MINIMAL keys must be in the map
    minimal_keys = {k for k in MINIMAL_REGISTRATIONS if isinstance(k, str)}
    assert minimal_keys <= map_keys, (
        f"MINIMAL keys {minimal_keys - map_keys} not in registration_map"
    )

    # STANDARD value (FULL_REGISTRATIONS) keys must be in the map
    standard_keys = {k for k in FULL_REGISTRATIONS if isinstance(k, str)}
    assert standard_keys <= map_keys, (
        f"STANDARD/FULL keys {standard_keys - map_keys} not in registration_map"
    )

    # All registry keys must be in the map (proves _GROUP_REGISTRY is the SSOT)
    registry_keys = {key for key, _ in _GROUP_REGISTRY}
    assert registry_keys == map_keys, (
        f"registration_map keys {map_keys} != _GROUP_REGISTRY keys {registry_keys}"
    )


def test_essential_tool_names_subset_check_enforced() -> None:
    """essential_tool_names={"health_check"} must actually be enforced.

    Runtime check: profiles.py calls ``_apply_tool_profile`` with
    ``essential_tool_names={"health_check"}``. After dispatch at MINIMAL,
    the registered tool set must contain ``health_check`` (enforced by
    the W0 helper's subset check; raises ValueError on failure).
    """
    import inspect

    from excalidraw_mcp.tools import profiles as _profiles

    source = inspect.getsource(_profiles.apply_excalidraw_tool_profile)
    assert 'essential_tool_names={"health_check"}' in source, (
        "apply_excalidraw_tool_profile must pass essential_tool_names={'health_check'} "
        "to enforce the W4 canonical MINIMAL=health invariant"
    )


def test_full_registers_all_groups() -> None:
    """FULL/STANDARD profile registers every group + discover_tools."""
    config = Config()
    mapping = _build_registration_map(config)
    assert "health_tools" in mapping
    assert "canvas_tools" in mapping
    assert len(mapping) == len(_GROUP_REGISTRY)


def test_minimal_subset_is_non_empty() -> None:
    """MINIMAL_REGISTRATIONS must not be empty (the W4.1 reviewer finding)."""
    assert MINIMAL_REGISTRATIONS, (
        "MINIMAL_REGISTRATIONS must NOT be empty — W4.1 canonical mapping "
        "is MINIMAL=health. If you want MINIMAL=empty, change the W4 spec, "
        "not the implementation."
    )


def test_invalid_profile_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid EXCALIDRAW_TOOL_PROFILE values raise InvalidProfileError at sync validation."""
    from mcp_common.tools.dispatch import InvalidProfileError, apply_tool_profile

    monkeypatch.setenv("EXCALIDRAW_TOOL_PROFILE", "bogus")
    with pytest.raises(InvalidProfileError):
        apply_tool_profile(
            None,  # server=None: validation-only path
            profile_env_var="EXCALIDRAW_TOOL_PROFILE",
            registrations=PROFILE_REGISTRATIONS,
            registration_map={},
            register_all_fn=lambda server: None,
            mandatory_groups=set(),
            essential_tool_names={"health_check"},
        )


# ---------------------------------------------------------------------------
# W4.1 round-1: caller-supplied config must be preserved through registration
# ---------------------------------------------------------------------------


def test_caller_supplied_config_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    """The config object passed to ``create_app`` is the same one used at registration.

    This catches the W4.1 round-1 regression where registration paths
    silently re-loaded settings from the environment, discarding any
    test-injected overrides.

    Strategy: monkey-patch ``Config.__init__`` to RAISE if called during
    registration. If registration paths bypass the caller's config and
    call ``Config()`` themselves, the test fails with the raised
    error. This is a true negative-test for the W4.1 regression.
    """
    from fastmcp import FastMCP

    monkeypatch.delenv("EXCALIDRAW_TOOL_PROFILE", raising=False)

    # Track whether Config() was instantiated
    init_calls: list[str] = []

    original_init = Config.__init__

    def tracking_init(*args, **kwargs):
        init_calls.append("init_called")
        return original_init(*args, **kwargs)

    monkeypatch.setattr(Config, "__init__", tracking_init)

    config = Config()  # First instantiation - this is OK (the caller)

    # Reset the call counter - we only care about registration-time calls.
    init_calls.clear()

    # Build the registration map. If this calls Config() internally,
    # init_calls will contain an entry. The W4.1 round-1 bug was that
    # registration paths called Config() and discarded caller config.
    mapping = _build_registration_map(config)

    # Run the actual registration (FULL/STANDARD profile behavior)
    server = FastMCP(name="test-server")
    for _key, fn in mapping.items():
        fn(server)

    assert init_calls == [], (
        f"_build_registration_map called Config.__init__ {len(init_calls)} time(s) — "
        f"registration paths re-loaded config from the environment, "
        f"discarding the caller-supplied config object. "
        f"This is the W4.1 round-1 regression."
    )


def test_register_all_tool_groups_does_not_reload_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """register_all_tool_groups must not re-load config from the environment."""
    config = Config()

    init_calls: list[str] = []
    original_init = Config.__init__

    def tracking_init(*args, **kwargs):
        init_calls.append("init_called")
        return original_init(*args, **kwargs)

    monkeypatch.setattr(Config, "__init__", tracking_init)

    from fastmcp import FastMCP

    server = FastMCP(name="test-server")
    register_all_tool_groups(server, config)

    assert init_calls == [], (
        f"register_all_tool_groups called Config.__init__ {len(init_calls)} time(s) — "
        f"W4.1 round-1 regression: registration path discarded caller-supplied config."
    )


def test_full_registrations_match_group_registry() -> None:
    """FULL_REGISTRATIONS must be derived from _GROUP_REGISTRY (SSOT)."""
    expected = [key for key, _ in _GROUP_REGISTRY]
    assert expected == FULL_REGISTRATIONS, (
        f"FULL_REGISTRATIONS={FULL_REGISTRATIONS} drifted from _GROUP_REGISTRY={expected}"
    )


def test_env_var_default_is_full(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sanity: an unset EXCALIDRAW_TOOL_PROFILE env var falls through to FULL."""
    monkeypatch.delenv("EXCALIDRAW_TOOL_PROFILE", raising=False)
    assert os.getenv("EXCALIDRAW_TOOL_PROFILE") is None


def test_full_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default (no env var) → FULL = all 12 tools + discover_tools."""
    monkeypatch.delenv("EXCALIDRAW_TOOL_PROFILE", raising=False)
    from mcp_common.tools.dispatch import _resolve_profile

    profile = _resolve_profile("EXCALIDRAW_TOOL_PROFILE", yaml_loader=None)
    assert profile.value == "full", f"Expected default FULL, got {profile.value}"


# ---------------------------------------------------------------------------
# W2b.3 keystone: real production-path tests (no mocks)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_app_full_profile_real_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2b.3 keystone test — real ``await create_app(config, server)`` end-to-end.

    NO mocks of the dispatch helper. Uses standard ``monkeypatch`` fixture
    (not manual MonkeyPatch lifecycle). Asserts STRICT EQUALITY on tool
    names so unreported extra tools fail loud (W2b.1 lesson).
    """
    from fastmcp import FastMCP

    monkeypatch.delenv("EXCALIDRAW_TOOL_PROFILE", raising=False)

    # Use a fresh server instance to avoid tool registration collisions
    # across tests (the module-level `mcp` is shared global state).
    fresh_server = FastMCP(name="excalidraw-mcp-test")
    config = Config()

    mcp_returned = await create_app(config, fresh_server)
    assert mcp_returned is fresh_server

    tools = await fresh_server.list_tools()
    tool_names = {t.name for t in tools}

    # FULL profile: all 12 canvas tools + health_check + discover_tools
    expected = {
        "create_element",
        "update_element",
        "delete_element",
        "query_elements",
        "batch_create_elements",
        "group_elements",
        "ungroup_elements",
        "align_elements",
        "distribute_elements",
        "lock_elements",
        "unlock_elements",
        "get_resource",
        "health_check",
        "discover_tools",
    }
    assert tool_names == expected, (
        f"FULL profile tool set mismatch.\n"
        f"  Expected: {sorted(expected)}\n"
        f"  Got:      {sorted(tool_names)}\n"
        f"  Missing:  {sorted(expected - tool_names)}\n"
        f"  Extra:    {sorted(tool_names - expected)}"
    )


@pytest.mark.asyncio
async def test_create_app_minimal_profile_real_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2b.3 keystone test — real MINIMAL ``await create_app(config, server)``.

    MINIMAL must expose ``health_check`` (canonical W4.1 mapping) plus
    ``discover_tools``. Strict equality (no extra tools allowed).
    """
    from fastmcp import FastMCP

    monkeypatch.setenv("EXCALIDRAW_TOOL_PROFILE", "minimal")

    fresh_server = FastMCP(name="excalidraw-mcp-test")
    config = Config()

    mcp_returned = await create_app(config, fresh_server)
    assert mcp_returned is fresh_server

    tools = await fresh_server.list_tools()
    tool_names = {t.name for t in tools}

    expected = {"health_check", "discover_tools"}
    assert tool_names == expected, (
        f"MINIMAL profile tool set mismatch.\n"
        f"  Expected: {sorted(expected)}\n"
        f"  Got:      {sorted(tool_names)}\n"
        f"  Missing:  {sorted(expected - tool_names)}\n"
        f"  Extra:    {sorted(tool_names - expected)}"
    )

    # Critical: health_check MUST be present at MINIMAL (W4 spec)
    assert "health_check" in tool_names, (
        f"health_check MISSING at MINIMAL profile — W4 canonical MINIMAL=health "
        f"violated. Got: {tool_names}"
    )


@pytest.mark.asyncio
async def test_create_app_standard_profile_real_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """STANDARD profile should match FULL (Tier-A trivial: same mapping)."""
    from fastmcp import FastMCP

    monkeypatch.setenv("EXCALIDRAW_TOOL_PROFILE", "standard")

    fresh_server = FastMCP(name="excalidraw-mcp-test")
    config = Config()

    mcp_returned = await create_app(config, fresh_server)
    assert mcp_returned is fresh_server

    tools = await fresh_server.list_tools()
    tool_names = {t.name for t in tools}

    expected = {
        "create_element",
        "update_element",
        "delete_element",
        "query_elements",
        "batch_create_elements",
        "group_elements",
        "ungroup_elements",
        "align_elements",
        "distribute_elements",
        "lock_elements",
        "unlock_elements",
        "get_resource",
        "health_check",
        "discover_tools",
    }
    assert tool_names == expected, (
        f"STANDARD profile tool set mismatch.\n"
        f"  Expected: {sorted(expected)}\n"
        f"  Got:      {sorted(tool_names)}\n"
        f"  Missing:  {sorted(expected - tool_names)}\n"
        f"  Extra:    {sorted(tool_names - expected)}"
    )


@pytest.mark.asyncio
async def test_create_app_real_path_with_caller_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end create_app test that exercises the production path.

    Verifies the caller-supplied config is preserved through the async
    production path (W4.1 round-1 fix).
    """
    from fastmcp import FastMCP

    monkeypatch.delenv("EXCALIDRAW_TOOL_PROFILE", raising=False)

    fresh_server = FastMCP(name="excalidraw-mcp-test")

    # Track Config.__init__ to ensure caller-supplied config is preserved
    init_calls: list[str] = []
    original_init = Config.__init__

    def tracking_init(*args, **kwargs):
        init_calls.append("init_called")
        return original_init(*args, **kwargs)

    monkeypatch.setattr(Config, "__init__", tracking_init)

    config = Config()
    init_calls.clear()  # Reset after initial instantiation

    mcp_returned = await create_app(config, fresh_server)
    assert mcp_returned is fresh_server

    # Verify registration did NOT re-construct Config
    assert init_calls == [], (
        f"create_app called Config.__init__ {len(init_calls)} time(s) "
        f"after initial config was supplied — caller config was discarded."
    )
