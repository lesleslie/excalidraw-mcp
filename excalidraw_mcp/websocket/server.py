"""WebSocket server for Excalidraw diagram collaboration.

Broadcasts real-time events for:
- Diagram creation and updates
- Cursor movement
- User presence
- Collaborative editing
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from mcp_common.websocket import (
    MessageType,
    WebSocketMessage,
    WebSocketProtocol,
    WebSocketServer,
)
from mcp_common.websocket.protocol import EventTypes

# Import authentication
from excalidraw_mcp.websocket.auth import get_authenticator

logger = logging.getLogger(__name__)


class ExcalidrawWebSocketServer(WebSocketServer):
    """WebSocket server for Excalidraw diagram collaboration.

    Broadcasts real-time events for:
    - Diagram creation events
    - Cursor position updates
    - User presence notifications
    - Collaborative editing state

    Channels:
    - diagram:{diagram_id} - Diagram-specific updates
    - cursor:{diagram_id} - Cursor position updates
    - presence:{diagram_id} - User presence events
    - global - System-wide events

    Attributes:
        diagram_manager: Diagram manager instance
        host: Server host address
        port: Server port number (default: 3042)
    """

    def __init__(
        self,
        diagram_manager: Any,
        host: str = "127.0.0.1",
        port: int = 3042,
        max_connections: int = 100,
        message_rate_limit: int = 60,
        require_auth: bool = False,
    ):
        """Initialize Excalidraw WebSocket server.

        Args:
            diagram_manager: DiagramManager instance
            host: Server host address
            port: Server port number
            max_connections: Maximum concurrent connections
            message_rate_limit: Messages per second per connection
            require_auth: Require JWT authentication for connections
        """
        authenticator = get_authenticator()

        super().__init__(
            host=host,
            port=port,
            max_connections=max_connections,
            message_rate_limit=message_rate_limit,
            authenticator=authenticator,
            require_auth=require_auth,
        )

        self.diagram_manager = diagram_manager
        logger.info(f"ExcalidrawWebSocketServer initialized: {host}:{port}")

    async def on_connect(self, websocket: Any, connection_id: str) -> None:
        """Handle new WebSocket connection.

        Args:
            websocket: WebSocket connection object
            connection_id: Unique connection identifier
        """
        user = getattr(websocket, "user", None)
        user_id = user.get("user_id") if user else "anonymous"

        logger.info(f"Client connected: {connection_id} (user: {user_id})")

        # Send welcome message
        welcome = WebSocketProtocol.create_event(
            EventTypes.SESSION_CREATED,
            {
                "connection_id": connection_id,
                "server": "excalidraw",
                "message": "Connected to Excalidraw collaboration",
                "authenticated": user is not None,
            },
        )
        await websocket.send(WebSocketProtocol.encode(welcome))

    async def on_disconnect(self, websocket: Any, connection_id: str) -> None:
        """Handle WebSocket disconnection.

        Args:
            websocket: WebSocket connection object
            connection_id: Unique connection identifier
        """
        logger.info(f"Client disconnected: {connection_id}")
        await self.leave_all_rooms(connection_id)

    async def on_message(self, websocket: Any, message: WebSocketMessage) -> None:
        """Handle incoming WebSocket message.

        Args:
            websocket: WebSocket connection object
            message: Decoded message
        """
        if message.type == MessageType.REQUEST:
            await self._handle_request(websocket, message)
        elif message.type == MessageType.EVENT:
            await self._handle_event(websocket, message)
        else:
            logger.warning(f"Unhandled message type: {message.type}")

    async def _handle_request(
        self, websocket: Any, message: WebSocketMessage
    ) -> None:
        """Handle request message (expects response).

        Args:
            websocket: WebSocket connection object
            message: Request message
        """
        # Get authenticated user from connection
        user = getattr(websocket, "user", None)

        if message.event == "subscribe":
            channel = message.data.get("channel")

            # Check authorization for this channel
            if user and not self._can_subscribe_to_channel(user, channel):
                error = WebSocketProtocol.create_error(
                    error_code="FORBIDDEN",
                    error_message=f"Not authorized to subscribe to {channel}",
                    correlation_id=message.correlation_id,
                )
                await websocket.send(WebSocketProtocol.encode(error))
                return

            if channel:
                connection_id = getattr(websocket, "id", str(uuid.uuid4()))
                await self.join_room(channel, connection_id)

                response = WebSocketProtocol.create_response(
                    message,
                    {"status": "subscribed", "channel": channel}
                )
                await websocket.send(WebSocketProtocol.encode(response))

        elif message.event == "unsubscribe":
            channel = message.data.get("channel")
            if channel:
                connection_id = getattr(websocket, "id", str(uuid.uuid4()))
                await self.leave_room(channel, connection_id)

                response = WebSocketProtocol.create_response(
                    message,
                    {"status": "unsubscribed", "channel": channel}
                )
                await websocket.send(WebSocketProtocol.encode(response))

        elif message.event == "get_diagram_status":
            diagram_id = message.data.get("diagram_id")
            if diagram_id and self.diagram_manager:
                status = await self._get_diagram_status(diagram_id)
                response = WebSocketProtocol.create_response(message, status)
                await websocket.send(WebSocketProtocol.encode(response))

        else:
            error = WebSocketProtocol.create_error(
                error_code="UNKNOWN_REQUEST",
                error_message=f"Unknown request event: {message.event}",
                correlation_id=message.correlation_id,
            )
            await websocket.send(WebSocketProtocol.encode(error))

    async def _handle_event(self, websocket: Any, message: WebSocketMessage) -> None:
        """Handle event message (no response expected).

        Args:
            websocket: WebSocket connection object
            message: Event message
        """
        logger.debug(f"Received client event: {message.event}")

    def _can_subscribe_to_channel(self, user: dict[str, Any], channel: str) -> bool:
        """Check if user can subscribe to channel.

        Args:
            user: User payload from JWT
            channel: Channel name

        Returns:
            True if authorized, False otherwise
        """
        permissions = user.get("permissions", [])

        # Admin can subscribe to any channel
        if "excalidraw:admin" in permissions:
            return True

        # Check channel-specific permissions
        if channel.startswith("diagram:"):
            return "excalidraw:read" in permissions

        if channel.startswith("cursor:"):
            return "excalidraw:read" in permissions

        if channel.startswith("presence:"):
            return "excalidraw:read" in permissions

        # Default: deny
        return False

    async def _get_diagram_status(self, diagram_id: str) -> dict[str, Any]:
        """Get diagram status from diagram manager.

        Args:
            diagram_id: Diagram identifier

        Returns:
            Diagram status dictionary
        """
        try:
            if hasattr(self.diagram_manager, "get_diagram"):
                diagram = await self.diagram_manager.get_diagram(diagram_id)
                return {
                    "diagram_id": diagram_id,
                    "status": "found",
                    "diagram": diagram
                }
            else:
                return {"diagram_id": diagram_id, "status": "not_found"}
        except Exception as e:
            logger.error(f"Error getting diagram status: {e}")
            return {"diagram_id": diagram_id, "status": "error", "error": str(e)}

    async def leave_all_rooms(self, connection_id: str) -> None:
        """Remove connection from all rooms.

        Args:
            connection_id: Connection identifier
        """
        # Remove connection from all rooms
        rooms_to_leave = []
        for room_id, connections in self.connection_rooms.items():
            if connection_id in connections:
                rooms_to_leave.append(room_id)

        for room_id in rooms_to_leave:
            await self.leave_room(room_id, connection_id)

    # Broadcast methods for diagram events

    async def broadcast_diagram_created(
        self, diagram_id: str, metadata: dict[str, Any]
    ) -> None:
        """Broadcast diagram created event.

        Args:
            diagram_id: Diagram identifier
            metadata: Diagram metadata (title, elements, etc.)
        """
        event = WebSocketProtocol.create_event(
            EventTypes.DIAGRAM_CREATED,
            {
                "diagram_id": diagram_id,
                "timestamp": self._get_timestamp(),
                **metadata
            },
            room=f"diagram:{diagram_id}"
        )
        await self.broadcast_to_room(f"diagram:{diagram_id}", event)

    async def broadcast_diagram_updated(
        self, diagram_id: str, metadata: dict[str, Any]
    ) -> None:
        """Broadcast diagram updated event.

        Args:
            diagram_id: Diagram identifier
            metadata: Update metadata
        """
        event = WebSocketProtocol.create_event(
            EventTypes.DIAGRAM_UPDATED,
            {
                "diagram_id": diagram_id,
                "timestamp": self._get_timestamp(),
                **metadata
            },
            room=f"diagram:{diagram_id}"
        )
        await self.broadcast_to_room(f"diagram:{diagram_id}", event)

    async def broadcast_cursor_moved(
        self, diagram_id: str, user_id: str, position: dict[str, Any]
    ) -> None:
        """Broadcast cursor moved event.

        Args:
            diagram_id: Diagram identifier
            user_id: User identifier
            position: Cursor position {x, y}
        """
        event = WebSocketProtocol.create_event(
            EventTypes.CURSOR_MOVED,
            {
                "diagram_id": diagram_id,
                "user_id": user_id,
                "position": position,
                "timestamp": self._get_timestamp(),
            },
            room=f"cursor:{diagram_id}"
        )
        await self.broadcast_to_room(f"cursor:{diagram_id}", event)

    async def broadcast_user_joined(
        self, diagram_id: str, user_id: str, user_info: dict[str, Any]
    ) -> None:
        """Broadcast user joined event.

        Args:
            diagram_id: Diagram identifier
            user_id: User identifier
            user_info: User information {name, color, etc.}
        """
        event = WebSocketProtocol.create_event(
            EventTypes.USER_JOINED,
            {
                "diagram_id": diagram_id,
                "user_id": user_id,
                "user_info": user_info,
                "timestamp": self._get_timestamp(),
            },
            room=f"presence:{diagram_id}"
        )
        await self.broadcast_to_room(f"presence:{diagram_id}", event)

    async def broadcast_user_left(
        self, diagram_id: str, user_id: str
    ) -> None:
        """Broadcast user left event.

        Args:
            diagram_id: Diagram identifier
            user_id: User identifier
        """
        event = WebSocketProtocol.create_event(
            EventTypes.USER_LEFT,
            {
                "diagram_id": diagram_id,
                "user_id": user_id,
                "timestamp": self._get_timestamp(),
            },
            room=f"presence:{diagram_id}"
        )
        await self.broadcast_to_room(f"presence:{diagram_id}", event)

    def _get_timestamp(self) -> str:
        """Get current ISO timestamp.

        Returns:
            ISO 8601 formatted timestamp
        """
        from datetime import datetime, UTC
        return datetime.now(UTC).isoformat()
