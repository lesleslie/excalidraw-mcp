"""Tests for Excalidraw WebSocket server.

This module tests the WebSocket server implementation for Excalidraw diagram collaboration,
including:
- Server initialization and configuration
- Broadcasting diagram events (created, updated)
- Cursor position broadcasting
- User presence events (joined, left)
- Connection management
- Channel subscription/unsubscription
- Message handling and routing
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from excalidraw_mcp.websocket import ExcalidrawWebSocketServer


def test_server_initialization():
    """Test server initialization with default parameters."""
    diagram_manager = MagicMock()
    server = ExcalidrawWebSocketServer(
        diagram_manager=diagram_manager,
        host="127.0.0.1",
        port=3042,
    )

    assert server.host == "127.0.0.1"
    assert server.port == 3042
    assert server.max_connections == 100
    assert server.diagram_manager is not None


def test_server_initialization_custom_params():
    """Test server initialization with custom parameters."""
    diagram_manager = MagicMock()
    server = ExcalidrawWebSocketServer(
        diagram_manager=diagram_manager,
        host="0.0.0.0",
        port=8080,
        max_connections=200,
        message_rate_limit=120,
    )

    assert server.host == "0.0.0.0"
    assert server.port == 8080
    assert server.max_connections == 200
    assert server.message_rate_limit == 120


@pytest.mark.asyncio
async def test_broadcast_diagram_created():
    """Test diagram created broadcast."""
    diagram_manager = MagicMock()
    server = ExcalidrawWebSocketServer(
        diagram_manager=diagram_manager,
        host="127.0.0.1",
        port=3042,
    )

    # Add mock client to diagram room
    mock_client = AsyncMock()
    server.connections["test_conn"] = mock_client
    server.connection_rooms["diagram:test123"] = {"test_conn"}

    # Broadcast diagram created event
    await server.broadcast_diagram_created("test123", {"title": "Test Diagram"})

    # Verify message was sent
    assert mock_client.send.called


@pytest.mark.asyncio
async def test_broadcast_diagram_updated():
    """Test diagram updated broadcast."""
    diagram_manager = MagicMock()
    server = ExcalidrawWebSocketServer(
        diagram_manager=diagram_manager,
        host="127.0.0.1",
        port=3042,
    )

    # Add mock client to diagram room
    mock_client = AsyncMock()
    server.connections["test_conn"] = mock_client
    server.connection_rooms["diagram:test456"] = {"test_conn"}

    # Broadcast diagram updated event
    await server.broadcast_diagram_updated("test456", {"version": "2.0"})

    # Verify message was sent
    assert mock_client.send.called


@pytest.mark.asyncio
async def test_broadcast_cursor_moved():
    """Test cursor moved broadcast."""
    diagram_manager = MagicMock()
    server = ExcalidrawWebSocketServer(
        diagram_manager=diagram_manager,
        host="127.0.0.1",
        port=3042,
    )

    # Add mock client to cursor room
    mock_client = AsyncMock()
    server.connections["test_conn"] = mock_client
    server.connection_rooms["cursor:diag789"] = {"test_conn"}

    # Broadcast cursor moved event
    await server.broadcast_cursor_moved(
        "diag789",
        "user123",
        {"x": 150, "y": 200}
    )

    # Verify message was sent
    assert mock_client.send.called


@pytest.mark.asyncio
async def test_broadcast_user_joined():
    """Test user joined broadcast."""
    diagram_manager = MagicMock()
    server = ExcalidrawWebSocketServer(
        diagram_manager=diagram_manager,
        host="127.0.0.1",
        port=3042,
    )

    # Add mock client to presence room
    mock_client = AsyncMock()
    server.connections["test_conn"] = mock_client
    server.connection_rooms["presence:diag999"] = {"test_conn"}

    # Broadcast user joined event
    await server.broadcast_user_joined(
        "diag999",
        "user456",
        {"name": "Test User", "color": "#FF5733"}
    )

    # Verify message was sent
    assert mock_client.send.called


@pytest.mark.asyncio
async def test_broadcast_user_left():
    """Test user left broadcast."""
    diagram_manager = MagicMock()
    server = ExcalidrawWebSocketServer(
        diagram_manager=diagram_manager,
        host="127.0.0.1",
        port=3042,
    )

    # Add mock client to presence room
    mock_client = AsyncMock()
    server.connections["test_conn"] = mock_client
    server.connection_rooms["presence:diag999"] = {"test_conn"}

    # Broadcast user left event
    await server.broadcast_user_left("diag999", "user456")

    # Verify message was sent
    assert mock_client.send.called


@pytest.mark.asyncio
async def test_on_connect_sends_welcome():
    """Test that on_connect sends welcome message."""
    diagram_manager = MagicMock()
    server = ExcalidrawWebSocketServer(
        diagram_manager=diagram_manager,
        host="127.0.0.1",
        port=3042,
    )

    # Mock websocket
    mock_websocket = AsyncMock()
    connection_id = "test_conn_123"

    # Call on_connect
    await server.on_connect(mock_websocket, connection_id)

    # Verify welcome message was sent
    assert mock_websocket.send.called


@pytest.mark.asyncio
async def test_on_disconnect_leaves_rooms():
    """Test that on_disconnect leaves all rooms."""
    diagram_manager = MagicMock()
    server = ExcalidrawWebSocketServer(
        diagram_manager=diagram_manager,
        host="127.0.0.1",
        port=3042,
    )

    # Mock websocket and set up rooms
    mock_websocket = AsyncMock()
    connection_id = "test_conn_123"
    server.connection_rooms["room1"] = {connection_id}
    server.connection_rooms["room2"] = {connection_id}

    # Call on_disconnect
    await server.on_disconnect(mock_websocket, connection_id)

    # Verify connection was removed from all rooms
    assert connection_id not in server.connection_rooms.get("room1", set())
    assert connection_id not in server.connection_rooms.get("room2", set())


@pytest.mark.asyncio
async def test_get_diagram_status():
    """Test getting diagram status."""
    diagram_manager = AsyncMock()
    diagram_manager.get_diagram = AsyncMock(return_value={"id": "test123", "title": "Test"})

    server = ExcalidrawWebSocketServer(
        diagram_manager=diagram_manager,
        host="127.0.0.1",
        port=3042,
    )

    # Get diagram status
    status = await server._get_diagram_status("test123")

    # Verify status
    assert status["diagram_id"] == "test123"
    assert status["status"] == "found"
    assert "diagram" in status


@pytest.mark.asyncio
async def test_get_diagram_status_not_found():
    """Test getting status when diagram manager has no get_diagram method."""
    # Create a mock object without the get_diagram method
    class SimpleManager:
        pass

    diagram_manager = SimpleManager()

    server = ExcalidrawWebSocketServer(
        diagram_manager=diagram_manager,
        host="127.0.0.1",
        port=3042,
    )

    # Get diagram status
    status = await server._get_diagram_status("missing")

    # Verify status
    assert status["diagram_id"] == "missing"
    assert status["status"] == "not_found"


def test_get_timestamp():
    """Test timestamp generation."""
    diagram_manager = MagicMock()
    server = ExcalidrawWebSocketServer(
        diagram_manager=diagram_manager,
        host="127.0.0.1",
        port=3042,
    )

    # Get timestamp
    timestamp = server._get_timestamp()

    # Verify it's a valid ISO timestamp
    assert isinstance(timestamp, str)
    assert "T" in timestamp or ":" in timestamp
