"""MCP tool implementations for Excalidraw operations."""

import logging
from typing import Any

from fastmcp import FastMCP
from pydantic import BaseModel

from .element_factory import ElementFactory
from .http_client import http_client
from .process_manager import process_manager

logger = logging.getLogger(__name__)


class MCPToolsManager:
    """Manager for MCP tool implementations."""

    def __init__(self, mcp: FastMCP):
        self.mcp = mcp
        self.element_factory = ElementFactory()
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tools."""
        # Element management tools
        self.mcp.tool("create_element")(self.create_element)
        self.mcp.tool("update_element")(self.update_element)
        self.mcp.tool("delete_element")(self.delete_element)
        self.mcp.tool("query_elements")(self.query_elements)

        # Batch operations
        self.mcp.tool("batch_create_elements")(self.batch_create_elements)

        # Element organization
        self.mcp.tool("group_elements")(self.group_elements)
        self.mcp.tool("ungroup_elements")(self.ungroup_elements)
        self.mcp.tool("align_elements")(self.align_elements)
        self.mcp.tool("distribute_elements")(self.distribute_elements)
        self.mcp.tool("lock_elements")(self.lock_elements)
        self.mcp.tool("unlock_elements")(self.unlock_elements)

        # Resource access
        self.mcp.tool("get_resource")(self.get_resource)

    async def _ensure_canvas_available(self) -> bool:
        """Ensure canvas server is available before operations."""
        if not await process_manager.ensure_running():
            raise RuntimeError("Canvas server is not available")
        return True

    async def _sync_to_canvas(
        self, operation: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Sync operation to canvas server with error handling."""
        try:
            await self._ensure_canvas_available()

            if operation == "create":
                return await http_client.post_json("/api/elements", data)
            elif operation == "update":
                element_id = data.pop("id")
                return await http_client.put_json(f"/api/elements/{element_id}", data)
            elif operation == "delete":
                return {
                    "success": await http_client.delete(f"/api/elements/{data['id']}")
                }
            elif operation == "query":
                return await http_client.get_json("/api/elements")
            else:
                logger.error(f"Unknown sync operation: {operation}")
                return None

        except Exception as e:
            logger.error(f"Canvas sync failed for {operation}: {e}")
            raise RuntimeError(f"Failed to sync {operation} to canvas: {str(e)}")

    # Element Management Tools

    async def create_element(self, request: BaseModel) -> dict[str, Any]:
        """Create a new element on the canvas."""
        try:
            # Create element with factory
            element_data = self.element_factory.create_element(request.dict())

            # Sync to canvas
            result = await self._sync_to_canvas("create", element_data)

            if result and result.get("success"):
                return {
                    "success": True,
                    "element": result.get("element", element_data),
                    "message": f"Created {element_data['type']} element successfully",
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create element on canvas",
                    "element_data": element_data,
                }

        except Exception as e:
            logger.error(f"Element creation failed: {e}")
            return {"success": False, "error": f"Element creation failed: {str(e)}"}

    async def update_element(self, request: BaseModel) -> dict[str, Any]:
        """Update an existing element."""
        try:
            request_data = request.dict()
            element_id = request_data.get("id")

            if not element_id:
                return {"success": False, "error": "Element ID is required for updates"}

            # Prepare update data
            update_data = self.element_factory.prepare_update_data(request_data)

            # Sync to canvas
            result = await self._sync_to_canvas("update", update_data)

            if result and result.get("success"):
                return {
                    "success": True,
                    "element": result.get("element"),
                    "message": f"Updated element {element_id} successfully",
                }
            else:
                return {"success": False, "error": "Failed to update element on canvas"}

        except Exception as e:
            logger.error(f"Element update failed: {e}")
            return {"success": False, "error": f"Element update failed: {str(e)}"}

    async def delete_element(self, element_id: str) -> dict[str, Any]:
        """Delete an element from the canvas."""
        try:
            # Sync to canvas
            result = await self._sync_to_canvas("delete", {"id": element_id})

            if result and result.get("success"):
                return {
                    "success": True,
                    "message": f"Deleted element {element_id} successfully",
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to delete element from canvas",
                }

        except Exception as e:
            logger.error(f"Element deletion failed: {e}")
            return {"success": False, "error": f"Element deletion failed: {str(e)}"}

    async def query_elements(self, request: BaseModel) -> dict[str, Any]:
        """Query elements from the canvas."""
        try:
            # Sync to canvas
            result = await self._sync_to_canvas("query", request.dict())

            if result:
                elements = result.get("elements", [])
                return {
                    "success": True,
                    "elements": elements,
                    "count": len(elements),
                    "message": f"Retrieved {len(elements)} elements",
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to query elements from canvas",
                }

        except Exception as e:
            logger.error(f"Element query failed: {e}")
            return {"success": False, "error": f"Element query failed: {str(e)}"}

    # Batch Operations

    async def batch_create_elements(self, request: BaseModel) -> dict[str, Any]:
        """Create multiple elements in one operation."""
        try:
            request_data = request.dict()
            elements_data = request_data.get("elements", [])

            if not elements_data:
                return {
                    "success": False,
                    "error": "No elements provided for batch creation",
                }

            # Limit batch size
            max_batch_size = 50
            if len(elements_data) > max_batch_size:
                return {
                    "success": False,
                    "error": f"Batch size exceeds maximum limit of {max_batch_size}",
                }

            # Create elements with factory
            created_elements = []
            for element_data in elements_data:
                created_element = self.element_factory.create_element(element_data)
                created_elements.append(created_element)

            # Sync to canvas
            batch_data = {"elements": created_elements}
            result = await http_client.post_json("/api/elements/batch", batch_data)

            if result and result.get("success"):
                return {
                    "success": True,
                    "elements": result.get("elements", created_elements),
                    "count": len(created_elements),
                    "message": f"Created {len(created_elements)} elements successfully",
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create batch elements on canvas",
                    "created_data": created_elements,
                }

        except Exception as e:
            logger.error(f"Batch element creation failed: {e}")
            return {
                "success": False,
                "error": f"Batch element creation failed: {str(e)}",
            }

    # Element Organization Tools

    async def group_elements(self, element_ids: list[str]) -> dict[str, Any]:
        """Group multiple elements together."""
        try:
            if len(element_ids) < 2:
                return {
                    "success": False,
                    "error": "At least 2 elements required for grouping",
                }

            group_data = {"elementIds": element_ids}
            result = await http_client.post_json("/api/elements/group", group_data)

            if result and result.get("success"):
                return {
                    "success": True,
                    "group_id": result.get("groupId"),
                    "message": f"Grouped {len(element_ids)} elements successfully",
                }
            else:
                return {"success": False, "error": "Failed to group elements on canvas"}

        except Exception as e:
            logger.error(f"Element grouping failed: {e}")
            return {"success": False, "error": f"Element grouping failed: {str(e)}"}

    async def ungroup_elements(self, group_id: str) -> dict[str, Any]:
        """Ungroup a group of elements."""
        try:
            result = await http_client.delete(f"/api/elements/group/{group_id}")

            if result:
                return {
                    "success": True,
                    "message": f"Ungrouped elements from group {group_id} successfully",
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to ungroup elements on canvas",
                }

        except Exception as e:
            logger.error(f"Element ungrouping failed: {e}")
            return {"success": False, "error": f"Element ungrouping failed: {str(e)}"}

    async def align_elements(self, request: BaseModel) -> dict[str, Any]:
        """Align elements to a specific position."""
        try:
            request_data = request.dict()
            element_ids = request_data.get("elementIds", [])
            alignment = request_data.get("alignment")

            if not element_ids or not alignment:
                return {
                    "success": False,
                    "error": "Element IDs and alignment are required",
                }

            align_data = {"elementIds": element_ids, "alignment": alignment}
            result = await http_client.post_json("/api/elements/align", align_data)

            if result and result.get("success"):
                return {
                    "success": True,
                    "message": f"Aligned {len(element_ids)} elements to {alignment} successfully",
                }
            else:
                return {"success": False, "error": "Failed to align elements on canvas"}

        except Exception as e:
            logger.error(f"Element alignment failed: {e}")
            return {"success": False, "error": f"Element alignment failed: {str(e)}"}

    async def distribute_elements(self, request: BaseModel) -> dict[str, Any]:
        """Distribute elements evenly."""
        try:
            request_data = request.dict()
            element_ids = request_data.get("elementIds", [])
            direction = request_data.get("direction")

            if not element_ids or not direction:
                return {
                    "success": False,
                    "error": "Element IDs and direction are required",
                }

            distribute_data = {"elementIds": element_ids, "direction": direction}
            result = await http_client.post_json(
                "/api/elements/distribute", distribute_data
            )

            if result and result.get("success"):
                return {
                    "success": True,
                    "message": f"Distributed {len(element_ids)} elements {direction}ly successfully",
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to distribute elements on canvas",
                }

        except Exception as e:
            logger.error(f"Element distribution failed: {e}")
            return {"success": False, "error": f"Element distribution failed: {str(e)}"}

    async def lock_elements(self, element_ids: list[str]) -> dict[str, Any]:
        """Lock elements to prevent modification."""
        try:
            lock_data = {"elementIds": element_ids, "locked": True}
            result = await http_client.post_json("/api/elements/lock", lock_data)

            if result and result.get("success"):
                return {
                    "success": True,
                    "message": f"Locked {len(element_ids)} elements successfully",
                }
            else:
                return {"success": False, "error": "Failed to lock elements on canvas"}

        except Exception as e:
            logger.error(f"Element locking failed: {e}")
            return {"success": False, "error": f"Element locking failed: {str(e)}"}

    async def unlock_elements(self, element_ids: list[str]) -> dict[str, Any]:
        """Unlock elements to allow modification."""
        try:
            unlock_data = {"elementIds": element_ids, "locked": False}
            result = await http_client.post_json("/api/elements/lock", unlock_data)

            if result and result.get("success"):
                return {
                    "success": True,
                    "message": f"Unlocked {len(element_ids)} elements successfully",
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to unlock elements on canvas",
                }

        except Exception as e:
            logger.error(f"Element unlocking failed: {e}")
            return {"success": False, "error": f"Element unlocking failed: {str(e)}"}

    # Resource Access

    async def get_resource(self, resource_type: str) -> dict[str, Any]:
        """Get canvas resources (scene, library, theme, elements)."""
        try:
            valid_resources = ["scene", "library", "theme", "elements"]

            if resource_type not in valid_resources:
                return {
                    "success": False,
                    "error": f"Invalid resource type. Must be one of: {', '.join(valid_resources)}",
                }

            result = await http_client.get_json(f"/api/{resource_type}")

            if result:
                return {
                    "success": True,
                    "resource_type": resource_type,
                    "data": result,
                    "message": f"Retrieved {resource_type} resource successfully",
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to retrieve {resource_type} resource from canvas",
                }

        except Exception as e:
            logger.error(f"Resource retrieval failed: {e}")
            return {"success": False, "error": f"Resource retrieval failed: {str(e)}"}
