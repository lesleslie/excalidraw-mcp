"""WebSocket client examples for Excalidraw collaboration.

This module demonstrates how to connect to and interact with
the Excalidraw WebSocket server for real-time diagram collaboration.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp_common.websocket.client import WebSocketClient


async def monitor_diagram_collaboration(
    diagram_id: str,
    host: str = "127.0.0.1",
    port: int = 3042,
) -> None:
    """Monitor collaboration events for a specific diagram.

    Args:
        diagram_id: Diagram identifier to monitor
        host: WebSocket server host
        port: WebSocket server port
    """
    client = WebSocketClient(host=host, port=port)

    try:
        await client.connect()

        # Subscribe to diagram updates
        await client.send_request("subscribe", {"channel": f"diagram:{diagram_id}"})

        # Subscribe to cursor updates
        await client.send_request("subscribe", {"channel": f"cursor:{diagram_id}"})

        # Subscribe to presence updates
        await client.send_request("subscribe", {"channel": f"presence:{diagram_id}"})

        # Listen for events
        async for message in client.listen():
            if message.get("type") == "event":
                event = message.get("event", "")
                data = message.get("data", {})

                if event == "diagram.created":
                    print(f"Diagram created: {data.get('diagram_id')}")
                elif event == "diagram.updated":
                    print(f"Diagram updated: {data.get('diagram_id')}")
                elif event == "cursor.moved":
                    print(f"Cursor moved: user={data.get('user_id')} pos={data.get('position')}")
                elif event == "user.joined":
                    print(f"User joined: {data.get('user_info')}")
                elif event == "user.left":
                    print(f"User left: {data.get('user_id')}")

    except KeyboardInterrupt:
        print("\nStopping monitoring...")
    finally:
        await client.disconnect()


async def broadcast_diagram_update(
    diagram_id: str,
    elements: list[dict[str, Any]],
    host: str = "127.0.0.1",
    port: int = 3042,
) -> None:
    """Broadcast a diagram update to all collaborators.

    Args:
        diagram_id: Diagram identifier
        elements: Updated diagram elements
        host: WebSocket server host
        port: WebSocket server port
    """
    client = WebSocketClient(host=host, port=port)

    try:
        await client.connect()

        # Send diagram update event
        await client.send_event("diagram.updated", {
            "diagram_id": diagram_id,
            "elements": elements,
            "timestamp": asyncio.get_event_loop().time(),
        })

        print(f"Broadcast diagram update for {diagram_id}")

    finally:
        await client.disconnect()


async def broadcast_cursor_position(
    diagram_id: str,
    user_id: str,
    position: dict[str, int | float],
    host: str = "127.0.0.1",
    port: int = 3042,
) -> None:
    """Broadcast cursor position to diagram collaborators.

    Args:
        diagram_id: Diagram identifier
        user_id: User identifier
        position: Cursor position {x, y}
        host: WebSocket server host
        port: WebSocket server port
    """
    client = WebSocketClient(host=host, port=port)

    try:
        await client.connect()

        # Subscribe to cursor channel first
        await client.send_request("subscribe", {"channel": f"cursor:{diagram_id}"})

        # Broadcast cursor position
        await client.send_event("cursor.moved", {
            "diagram_id": diagram_id,
            "user_id": user_id,
            "position": position,
        })

        print(f"Broadcast cursor position for user {user_id}")

    finally:
        await client.disconnect()


async def join_collaboration_session(
    diagram_id: str,
    user_id: str,
    user_info: dict[str, Any],
    host: str = "127.0.0.1",
    port: int = 3042,
) -> None:
    """Join a diagram collaboration session.

    Args:
        diagram_id: Diagram identifier
        user_id: User identifier
        user_info: User information {name, color, etc.}
        host: WebSocket server host
        port: WebSocket server port
    """
    client = WebSocketClient(host=host, port=port)

    try:
        await client.connect()

        # Subscribe to presence channel
        await client.send_request("subscribe", {"channel": f"presence:{diagram_id}"})

        # Broadcast user joined event
        await client.send_event("user.joined", {
            "diagram_id": diagram_id,
            "user_id": user_id,
            "user_info": user_info,
        })

        print(f"Joined collaboration session for diagram {diagram_id}")

        # Keep connection alive and listen for events
        async for message in client.listen():
            if message.get("type") == "event":
                print(f"Event: {message.get('event')}")

    except KeyboardInterrupt:
        # Send user left event
        await client.send_event("user.left", {
            "diagram_id": diagram_id,
            "user_id": user_id,
        })
        print("\nLeft collaboration session")
    finally:
        await client.disconnect()


async def main() -> None:
    """Run example WebSocket client interactions."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python websocket_client_examples.py <command> [args...]")
        print("\nCommands:")
        print("  monitor <diagram_id>        - Monitor diagram collaboration")
        print("  update <diagram_id>         - Broadcast diagram update")
        print("  cursor <diagram_id> <user>  - Broadcast cursor position")
        print("  join <diagram_id> <user>    - Join collaboration session")
        return

    command = sys.argv[1]

    if command == "monitor" and len(sys.argv) >= 3:
        diagram_id = sys.argv[2]
        await monitor_diagram_collaboration(diagram_id)

    elif command == "update" and len(sys.argv) >= 3:
        diagram_id = sys.argv[2]
        elements = [{"type": "rectangle", "x": 100, "y": 100}]
        await broadcast_diagram_update(diagram_id, elements)

    elif command == "cursor" and len(sys.argv) >= 4:
        diagram_id = sys.argv[2]
        user_id = sys.argv[3]
        position = {"x": 150, "y": 150}
        await broadcast_cursor_position(diagram_id, user_id, position)

    elif command == "join" and len(sys.argv) >= 4:
        diagram_id = sys.argv[2]
        user_id = sys.argv[3]
        user_info = {"name": f"User {user_id}", "color": "#FF5733"}
        await join_collaboration_session(diagram_id, user_id, user_info)

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
