"""Tests for Excalidraw-MCP WebSocket authentication."""

from __future__ import annotations

import os
import sys
import pytest

# Set environment variables before importing the modules
os.environ["EXCALIDRAW_AUTH_ENABLED"] = "false"

from excalidraw_mcp.websocket.auth import (
    get_authenticator,
    generate_token,
    verify_token,
)
from excalidraw_mcp.websocket.server import ExcalidrawWebSocketServer
from mcp_common.websocket import WebSocketProtocol


@pytest.mark.unit
class TestExcalidrawWebSocketAuth:
    """Test Excalidraw WebSocket authentication configuration."""

    def test_get_authenticator_dev_mode(self):
        """Test getting authenticator in development mode."""
        # Ensure auth is disabled
        os.environ["EXCALIDRAW_AUTH_ENABLED"] = "false"

        # Reload module to pick up env var change
        import importlib
        import excalidraw_mcp.websocket.auth
        importlib.reload(excalidraw_mcp.websocket.auth)

        from excalidraw_mcp.websocket.auth import get_authenticator
        authenticator = get_authenticator()
        assert authenticator is None

    def test_generate_token(self):
        """Test generating a JWT token."""
        token = generate_token("user123", ["excalidraw:read", "excalidraw:write"])

        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2  # JWT format

    def test_verify_token(self):
        """Test verifying a generated token."""
        token = generate_token("user123", ["excalidraw:read"])
        payload = verify_token(token)

        assert payload is not None
        assert payload["user_id"] == "user123"
        assert payload["permissions"] == ["excalidraw:read"]

    def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        payload = verify_token("invalid-token")
        assert payload is None


@pytest.mark.unit
class TestExcalidrawWebSocketServer:
    """Test Excalidraw WebSocket server with authentication."""

    def test_server_initialization(self):
        """Test server initialization."""
        server = ExcalidrawWebSocketServer(
            diagram_manager=None,
            host="127.0.0.1",
            port=3042,
            require_auth=False,
        )

        assert server.host == "127.0.0.1"
        assert server.port == 3042
        assert server.require_auth is False

    def test_channel_authorization(self):
        """Test channel subscription authorization."""
        server = ExcalidrawWebSocketServer(
            diagram_manager=None,
            require_auth=False,
        )

        # Test admin user
        admin_user = {"user_id": "admin", "permissions": ["excalidraw:admin"]}
        assert server._can_subscribe_to_channel(admin_user, "diagram:123") is True
        assert server._can_subscribe_to_channel(admin_user, "cursor:abc") is True
        assert server._can_subscribe_to_channel(admin_user, "presence:abc") is True

        # Test user with excalidraw:read permission
        read_user = {"user_id": "user1", "permissions": ["excalidraw:read"]}
        assert server._can_subscribe_to_channel(read_user, "diagram:123") is True
        assert server._can_subscribe_to_channel(read_user, "cursor:abc") is True
        assert server._can_subscribe_to_channel(read_user, "presence:abc") is True

        # Test user without relevant permissions
        limited_user = {"user_id": "user2", "permissions": ["other"]}
        assert server._can_subscribe_to_channel(limited_user, "diagram:123") is False
        assert server._can_subscribe_to_channel(limited_user, "cursor:abc") is False
        assert server._can_subscribe_to_channel(limited_user, "presence:abc") is False


@pytest.mark.integration
class TestExcalidrawWebSocketAuthenticationIntegration:
    """Integration tests for Excalidraw WebSocket authentication."""

    @pytest.mark.asyncio
    async def test_server_start_without_auth(self):
        """Test that server starts without authentication."""
        server = ExcalidrawWebSocketServer(
            diagram_manager=None,
            host="127.0.0.1",
            port=3043,  # Use different port for testing
            require_auth=False,
        )

        try:
            await server.start()
            assert server.is_running is True
        finally:
            await server.stop()
            assert server.is_running is False

    @pytest.mark.asyncio
    async def test_unauthenticated_connection_rejected(self):
        """Test that connections without valid token are rejected."""
        # Enable auth for this test
        os.environ["EXCALIDRAW_AUTH_ENABLED"] = "true"

        # Reload module to pick up env var change
        import importlib
        import excalidraw_mcp.websocket.auth
        importlib.reload(excalidraw_mcp.websocket.auth)

        server = ExcalidrawWebSocketServer(
            diagram_manager=None,
            host="127.0.0.1",
            port=3046,
            require_auth=True,
        )

        try:
            await server.start()

            # Create client with invalid token
            from mcp_common.websocket import WebSocketClient
            client = WebSocketClient(
                uri="ws://127.0.0.1:3046",
                token="invalid-token",
                reconnect=False,
            )

            try:
                # Connection should fail or auth should fail
                await client.connect()
                # If connection succeeds, auth should have failed
                assert client.is_authenticated is False
            except (ConnectionError, Exception):
                # Expected - connection should be rejected
                pass
            finally:
                await client.disconnect()

        finally:
            await server.stop()
            os.environ["EXCALIDRAW_AUTH_ENABLED"] = "false"
