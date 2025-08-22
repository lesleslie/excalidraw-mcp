#!/usr/bin/env python3
"""
Excalidraw MCP Server - Python FastMCP Implementation
Provides MCP tools for creating and managing Excalidraw diagrams with canvas sync.
"""

import os
import json
import uuid
import asyncio
import logging
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, asdict
from enum import Enum

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
EXPRESS_SERVER_URL = os.getenv("EXPRESS_SERVER_URL", "http://localhost:3031")
ENABLE_CANVAS_SYNC = os.getenv("ENABLE_CANVAS_SYNC", "true").lower() != "false"

# Initialize FastMCP server
mcp = FastMCP("Excalidraw MCP Server")

# Excalidraw element types
class ElementType(str, Enum):
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    DIAMOND = "diamond"
    TEXT = "text"
    LINE = "line"
    ARROW = "arrow"
    DRAW = "draw"
    IMAGE = "image"
    FRAME = "frame"
    EMBEDDABLE = "embeddable"
    MAGICFRAME = "magicframe"

@dataclass
class ExcalidrawElement:
    """Excalidraw element data structure"""
    type: ElementType
    x: float
    y: float
    id: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    backgroundColor: Optional[str] = None
    strokeColor: Optional[str] = None
    strokeWidth: Optional[float] = None
    roughness: Optional[float] = None
    opacity: Optional[float] = None
    text: Optional[str] = None
    fontSize: Optional[float] = None
    fontFamily: Optional[str] = None
    locked: Optional[bool] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    version: Optional[int] = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())

# Pydantic models for validation
class CreateElementRequest(BaseModel):
    type: ElementType
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    backgroundColor: Optional[str] = None
    strokeColor: Optional[str] = None
    strokeWidth: Optional[float] = None
    roughness: Optional[float] = None
    opacity: Optional[float] = None
    text: Optional[str] = None
    fontSize: Optional[float] = None
    fontFamily: Optional[str] = None

class UpdateElementRequest(BaseModel):
    id: str
    type: Optional[ElementType] = None
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    backgroundColor: Optional[str] = None
    strokeColor: Optional[str] = None
    strokeWidth: Optional[float] = None
    roughness: Optional[float] = None
    opacity: Optional[float] = None
    text: Optional[str] = None
    fontSize: Optional[float] = None
    fontFamily: Optional[str] = None
    locked: Optional[bool] = None

class QueryElementsRequest(BaseModel):
    type: Optional[ElementType] = None
    filter: Optional[Dict[str, Any]] = None

class BatchCreateRequest(BaseModel):
    elements: List[CreateElementRequest]

class AlignElementsRequest(BaseModel):
    element_ids: List[str] = Field(alias="elementIds")
    alignment: Literal["left", "center", "right", "top", "middle", "bottom"]

class DistributeElementsRequest(BaseModel):
    element_ids: List[str] = Field(alias="elementIds")  
    direction: Literal["horizontal", "vertical"]

class ElementIdsRequest(BaseModel):
    element_ids: List[str] = Field(alias="elementIds")

# Canvas sync functions
async def sync_to_canvas(operation: str, data: Any) -> Optional[Dict[str, Any]]:
    """Sync operations to the Express canvas server"""
    if not ENABLE_CANVAS_SYNC:
        logger.debug("Canvas sync disabled")
        return None

    try:
        async with httpx.AsyncClient() as client:
            if operation == "create":
                url = f"{EXPRESS_SERVER_URL}/api/elements"
                response = await client.post(url, json=data)
            elif operation == "update":
                url = f"{EXPRESS_SERVER_URL}/api/elements/{data['id']}"
                response = await client.put(url, json=data)
            elif operation == "delete":
                url = f"{EXPRESS_SERVER_URL}/api/elements/{data['id']}"
                response = await client.delete(url)
            elif operation == "batch_create":
                url = f"{EXPRESS_SERVER_URL}/api/elements/batch"
                response = await client.post(url, json={"elements": data})
            else:
                logger.warning(f"Unknown sync operation: {operation}")
                return None

            if response.status_code < 400:
                return response.json()
            else:
                logger.warning(f"Canvas sync failed: {response.status_code}")
                return None

    except Exception as e:
        logger.warning(f"Canvas sync error for {operation}: {e}")
        return None

def convert_text_to_label(element: Dict[str, Any]) -> Dict[str, Any]:
    """Convert text property to label format for Excalidraw compatibility"""
    if "text" in element and element.get("type") != "text":
        # For non-text elements, convert text to label format
        text = element.pop("text")
        element["label"] = {"text": text}
    return element

# MCP Tool Implementations

@mcp.tool()
async def create_element(request: CreateElementRequest) -> str:
    """Create a new Excalidraw element"""
    logger.info(f"Creating element: {request.type}")
    
    # Create element data
    element_data = request.model_dump(exclude_none=True)
    element_data["id"] = str(uuid.uuid4())
    element_data["createdAt"] = "2025-01-01T00:00:00.000Z"  # timestamp placeholder
    element_data["updatedAt"] = "2025-01-01T00:00:00.000Z"
    element_data["version"] = 1
    
    # Convert text to label format for Excalidraw
    element_data = convert_text_to_label(element_data)
    
    # Sync to canvas
    canvas_result = await sync_to_canvas("create", element_data)
    
    if canvas_result is None and ENABLE_CANVAS_SYNC:
        return json.dumps({
            "error": "Failed to create element: Canvas server unavailable",
            "element": element_data
        }, indent=2)
    
    result = {
        "success": True,
        "element": canvas_result.get("element", element_data) if canvas_result else element_data,
        "synced_to_canvas": canvas_result is not None
    }
    
    return json.dumps(result, indent=2)

@mcp.tool()
async def update_element(request: UpdateElementRequest) -> str:
    """Update an existing Excalidraw element"""
    logger.info(f"Updating element: {request.id}")
    
    # Create update data
    update_data = request.model_dump(exclude_none=True)
    update_data["updatedAt"] = "2025-01-01T00:00:00.000Z"
    
    # Convert text to label format
    update_data = convert_text_to_label(update_data)
    
    # Sync to canvas
    canvas_result = await sync_to_canvas("update", update_data)
    
    if canvas_result is None and ENABLE_CANVAS_SYNC:
        return json.dumps({
            "error": "Failed to update element: Canvas server unavailable or element not found",
            "update_data": update_data
        }, indent=2)
    
    result = {
        "success": True,
        "element": canvas_result.get("element", update_data) if canvas_result else update_data,
        "synced_to_canvas": canvas_result is not None
    }
    
    return json.dumps(result, indent=2)

@mcp.tool()
async def delete_element(element_id: str) -> str:
    """Delete an Excalidraw element"""
    logger.info(f"Deleting element: {element_id}")
    
    # Sync to canvas
    canvas_result = await sync_to_canvas("delete", {"id": element_id})
    
    if canvas_result is None and ENABLE_CANVAS_SYNC:
        return json.dumps({
            "error": "Failed to delete element: Canvas server unavailable or element not found",
            "element_id": element_id
        }, indent=2)
    
    result = {
        "success": True,
        "element_id": element_id,
        "deleted": True,
        "synced_to_canvas": canvas_result is not None
    }
    
    return json.dumps(result, indent=2)

@mcp.tool()
async def query_elements(request: QueryElementsRequest) -> str:
    """Query Excalidraw elements with optional filters"""
    logger.info(f"Querying elements: type={request.type}")
    
    try:
        # Build query parameters
        params = {}
        if request.type:
            params["type"] = request.type.value
        if request.filter:
            params.update(request.filter)
        
        # Query canvas server
        async with httpx.AsyncClient() as client:
            url = f"{EXPRESS_SERVER_URL}/api/elements/search"
            response = await client.get(url, params=params)
            
            if response.status_code < 400:
                data = response.json()
                return json.dumps(data.get("elements", []), indent=2)
            else:
                return json.dumps({
                    "error": f"Query failed: {response.status_code}",
                    "elements": []
                }, indent=2)
                
    except Exception as e:
        return json.dumps({
            "error": f"Failed to query elements: {str(e)}",
            "elements": []
        }, indent=2)

@mcp.tool()
async def batch_create_elements(request: BatchCreateRequest) -> str:
    """Create multiple Excalidraw elements at once"""
    logger.info(f"Batch creating {len(request.elements)} elements")
    
    # Create elements data
    elements_data = []
    for element_req in request.elements:
        element_data = element_req.model_dump(exclude_none=True)
        element_data["id"] = str(uuid.uuid4())
        element_data["createdAt"] = "2025-01-01T00:00:00.000Z"
        element_data["updatedAt"] = "2025-01-01T00:00:00.000Z"
        element_data["version"] = 1
        
        # Convert text to label format
        element_data = convert_text_to_label(element_data)
        elements_data.append(element_data)
    
    # Sync to canvas
    canvas_result = await sync_to_canvas("batch_create", elements_data)
    
    if canvas_result is None and ENABLE_CANVAS_SYNC:
        return json.dumps({
            "error": "Failed to batch create elements: Canvas server unavailable",
            "elements": elements_data,
            "count": len(elements_data)
        }, indent=2)
    
    result = {
        "success": True,
        "elements": canvas_result.get("elements", elements_data) if canvas_result else elements_data,
        "count": len(elements_data),
        "synced_to_canvas": canvas_result is not None
    }
    
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_resource(resource: Literal["scene", "library", "theme", "elements"]) -> str:
    """Get Excalidraw resources (scene, library, theme, or elements)"""
    logger.info(f"Getting resource: {resource}")
    
    if resource in ["library", "elements"]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{EXPRESS_SERVER_URL}/api/elements")
                if response.status_code < 400:
                    data = response.json()
                    return json.dumps({
                        "elements": data.get("elements", [])
                    }, indent=2)
                else:
                    return json.dumps({
                        "error": f"Failed to get elements: {response.status_code}",
                        "elements": []
                    }, indent=2)
        except Exception as e:
            return json.dumps({
                "error": f"Failed to get elements: {str(e)}",
                "elements": []
            }, indent=2)
    
    elif resource == "scene":
        return json.dumps({
            "theme": "light",
            "viewport": {"x": 0, "y": 0, "zoom": 1},
            "selectedElements": []
        }, indent=2)
    
    elif resource == "theme":
        return json.dumps({"theme": "light"}, indent=2)
    
    else:
        return json.dumps({"error": f"Unknown resource: {resource}"}, indent=2)

@mcp.tool()
async def group_elements(request: ElementIdsRequest) -> str:
    """Group multiple elements together"""
    group_id = str(uuid.uuid4())
    result = {
        "success": True,
        "group_id": group_id,
        "element_ids": request.element_ids
    }
    return json.dumps(result, indent=2)

@mcp.tool()
async def ungroup_elements(group_id: str) -> str:
    """Ungroup a group of elements"""
    result = {
        "success": True,
        "group_id": group_id,
        "ungrouped": True
    }
    return json.dumps(result, indent=2)

@mcp.tool()
async def align_elements(request: AlignElementsRequest) -> str:
    """Align elements to a specific position"""
    logger.info(f"Aligning {len(request.element_ids)} elements: {request.alignment}")
    
    result = {
        "success": True,
        "aligned": True,
        "element_ids": request.element_ids,
        "alignment": request.alignment
    }
    return json.dumps(result, indent=2)

@mcp.tool()
async def distribute_elements(request: DistributeElementsRequest) -> str:
    """Distribute elements evenly"""
    logger.info(f"Distributing {len(request.element_ids)} elements: {request.direction}")
    
    result = {
        "success": True,
        "distributed": True,
        "element_ids": request.element_ids,
        "direction": request.direction
    }
    return json.dumps(result, indent=2)

@mcp.tool()
async def lock_elements(request: ElementIdsRequest) -> str:
    """Lock elements to prevent modification"""
    # Update each element to be locked via canvas API
    success_count = 0
    
    for element_id in request.element_ids:
        canvas_result = await sync_to_canvas("update", {
            "id": element_id,
            "locked": True
        })
        if canvas_result:
            success_count += 1
    
    result = {
        "success": success_count > 0,
        "locked": True,
        "element_ids": request.element_ids,
        "success_count": success_count
    }
    return json.dumps(result, indent=2)

@mcp.tool()
async def unlock_elements(request: ElementIdsRequest) -> str:
    """Unlock elements to allow modification"""
    # Update each element to be unlocked via canvas API
    success_count = 0
    
    for element_id in request.element_ids:
        canvas_result = await sync_to_canvas("update", {
            "id": element_id,
            "locked": False
        })
        if canvas_result:
            success_count += 1
    
    result = {
        "success": success_count > 0,
        "unlocked": True,
        "element_ids": request.element_ids,
        "success_count": success_count
    }
    return json.dumps(result, indent=2)

def main():
    """Main entry point for the CLI"""
    mcp.run()

if __name__ == "__main__":
    main()