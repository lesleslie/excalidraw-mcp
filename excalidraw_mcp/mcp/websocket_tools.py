"""MCP tools for Excalidraw WebSocket monitoring and management."""

from __future__ import annotations

from typing import Any
from fastmcp import FastMCP


def register_websocket_tools(
    server: FastMCP,
    websocket_server: Any,
) -> None:
    """Register WebSocket monitoring tools with MCP server.

    Args:
        server: FastMCP server instance
        websocket_server: ExcalidrawWebSocketServer instance
    """

    @server.tool()
    async def websocket_health_check() -> dict:
        """Check WebSocket server health and status.

        Returns:
            Health status dictionary with server state
        """
        if websocket_server is None or not websocket_server.is_running:
            return {
                "status": "stopped",
                "host": "127.0.0.1",
                "port": 3042,
                "server": "excalidraw"
            }

        return {
            "status": "healthy",
            "host": "127.0.0.1",
            "port": 3042,
            "server": "excalidraw",
            "connections": len(websocket_server.connections),
            "rooms": len(websocket_server.connection_rooms),
        }

    @server.tool()
    async def websocket_get_status() -> dict:
        """Get detailed WebSocket server status.

        Returns:
            Detailed status including connections and rooms
        """
        if websocket_server is None:
            return {"error": "WebSocket server not initialized"}

        return {
            "server": "excalidraw",
            "is_running": websocket_server.is_running,
            "connections": list(websocket_server.connections.keys()),
            "rooms": {
                room: list(connections)
                for room, connections in websocket_server.connection_rooms.items()
            },
        }

    @server.tool()
    async def websocket_list_rooms() -> dict:
        """List all active rooms and their subscribers.

        Returns:
            Dictionary mapping rooms to subscriber counts
        """
        if websocket_server is None:
            return {"error": "WebSocket server not initialized"}

        return {
            "rooms": {
                room: len(connections)
                for room, connections in websocket_server.connection_rooms.items()
            }
        }

    @server.tool()
    async def websocket_broadcast_test_event(channel: str) -> dict:
        """Broadcast a test event to a channel (development only).

        Args:
            channel: Channel to broadcast test event to

        Returns:
            Broadcast result confirmation
        """
        if websocket_server is None:
            return {"error": "WebSocket server not initialized"}

        from mcp_common.websocket import WebSocketProtocol

        test_event = WebSocketProtocol.create_event(
            "test.event",
            {"message": "Test event from Excalidraw WebSocket"},
            room=channel
        )

        await websocket_server.broadcast_to_room(channel, test_event)

        return {
            "status": "broadcast",
            "channel": channel,
            "subscribers": len(websocket_server.connection_rooms.get(channel, set()))
        }

    @server.tool()
    async def websocket_get_metrics() -> dict:
        """Get WebSocket server performance metrics.

        Returns:
            Server metrics including connection stats
        """
        if websocket_server is None:
            return {"error": "WebSocket server not initialized"}

        return {
            "server": "excalidraw",
            "is_running": websocket_server.is_running,
            "active_connections": len(websocket_server.connections),
            "active_rooms": len(websocket_server.connection_rooms),
            "max_connections": websocket_server.max_connections,
            "message_rate_limit": websocket_server.message_rate_limit,
        }
