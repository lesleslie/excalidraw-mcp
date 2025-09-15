"""Unit tests for the MCP tools module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic import BaseModel

from excalidraw_mcp.mcp_tools import MCPToolsManager


class TestMCPToolsUnit:
    """Test the MCPToolsManager class."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance."""
        return MagicMock()

    @pytest.fixture
    def mcp_tools_manager(self, mock_mcp):
        """Create an MCPToolsManager instance with a mock MCP."""
        with patch('excalidraw_mcp.mcp_tools.ElementFactory') as mock_factory_class, \
             patch('excalidraw_mcp.mcp_tools.http_client'), \
             patch('excalidraw_mcp.mcp_tools.process_manager'):
            
            # Mock the element factory instance
            mock_factory_instance = Mock()
            mock_factory_class.return_value = mock_factory_instance
            
            # Create the manager
            manager = MCPToolsManager(mock_mcp)
            
            # Store mocks for access in tests
            manager._mock_mcp = mock_mcp
            manager._mock_factory = mock_factory_instance
            
            return manager

    def test_initialization_registers_tools(self, mcp_tools_manager, mock_mcp):
        """Test that initialization registers all tools."""
        # Verify that tool registration was called
        mock_mcp.tool.assert_called()
        
        # Check that all expected tools were registered
        registered_tools = []
        for call in mock_mcp.tool.call_args_list:
            if call[0]:  # Positional arguments exist
                registered_tools.append(call[0][0])
        
        expected_tools = [
            "create_element", "update_element", "delete_element", "query_elements",
            "batch_create_elements", "group_elements", "ungroup_elements",
            "align_elements", "distribute_elements", "lock_elements", "unlock_elements",
            "get_resource"
        ]
        
        for tool in expected_tools:
            assert tool in registered_tools, f"Tool {tool} was not registered"

    def test_register_tools_calls_tool_method(self, mcp_tools_manager, mock_mcp):
        """Test that _register_tools calls the tool method correctly."""
        # Verify that tool method was called for each registration
        assert mock_mcp.tool.call_count >= 12  # Minimum expected tools
        
        # This test is sufficient - we verified tools are registered
        pass

    @pytest.mark.asyncio
    async def test_ensure_canvas_available_success(self, mcp_tools_manager):
        """Test that _ensure_canvas_available works when canvas is available."""
        with patch('excalidraw_mcp.mcp_tools.process_manager') as mock_process_manager:
            # Mock process manager to return True (available)
            mock_process_manager.ensure_running = AsyncMock(return_value=True)
            
            # Call the method
            result = await mcp_tools_manager._ensure_canvas_available()
            
            # Verify it returns True
            assert result is True
            # Verify process manager was called
            mock_process_manager.ensure_running.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_canvas_available_failure(self, mcp_tools_manager):
        """Test that _ensure_canvas_available raises exception when canvas is unavailable."""
        with patch('excalidraw_mcp.mcp_tools.process_manager') as mock_process_manager:
            # Mock process manager to return False (unavailable)
            mock_process_manager.ensure_running = AsyncMock(return_value=False)
            
            # Call the method and expect it to raise RuntimeError
            with pytest.raises(RuntimeError, match="Canvas server is not available"):
                await mcp_tools_manager._ensure_canvas_available()
            
            # Verify process manager was called
            mock_process_manager.ensure_running.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_to_canvas_create_operation(self, mcp_tools_manager):
        """Test _sync_to_canvas with create operation."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client, \
             patch.object(mcp_tools_manager, '_ensure_canvas_available', new=AsyncMock()):
            
            # Mock HTTP client to return success
            mock_result = {"success": True, "element": {"id": "test-123"}}
            mock_http_client.post_json = AsyncMock(return_value=mock_result)
            
            # Test data
            test_data = {"type": "rectangle", "x": 100, "y": 200}
            
            # Call the method
            result = await mcp_tools_manager._sync_to_canvas("create", test_data)
            
            # Verify the result
            assert result == mock_result
            # Verify HTTP client was called correctly
            mock_http_client.post_json.assert_called_once_with("/api/elements", test_data)
            # Verify canvas availability was checked
            mcp_tools_manager._ensure_canvas_available.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_to_canvas_update_operation(self, mcp_tools_manager):
        """Test _sync_to_canvas with update operation."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client, \
             patch.object(mcp_tools_manager, '_ensure_canvas_available', new=AsyncMock()):
            
            # Mock HTTP client to return success
            mock_result = {"success": True, "element": {"id": "test-123"}}
            mock_http_client.put_json = AsyncMock(return_value=mock_result)
            
            # Test data
            test_data = {"id": "test-123", "type": "rectangle", "x": 150, "y": 250}
            
            # Call the method
            result = await mcp_tools_manager._sync_to_canvas("update", test_data)
            
            # Verify the result
            assert result == mock_result
            # Verify HTTP client was called correctly
            mock_http_client.put_json.assert_called_once_with("/api/elements/test-123", {"type": "rectangle", "x": 150, "y": 250})
            # Verify canvas availability was checked
            mcp_tools_manager._ensure_canvas_available.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_to_canvas_delete_operation(self, mcp_tools_manager):
        """Test _sync_to_canvas with delete operation."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client, \
             patch.object(mcp_tools_manager, '_ensure_canvas_available', new=AsyncMock()):
            
            # Mock HTTP client to return success
            mock_http_client.delete = AsyncMock(return_value=True)
            
            # Test data
            test_data = {"id": "test-123"}
            
            # Call the method
            result = await mcp_tools_manager._sync_to_canvas("delete", test_data)
            
            # Verify the result
            assert result == {"success": True}
            # Verify HTTP client was called correctly
            mock_http_client.delete.assert_called_once_with("/api/elements/test-123")
            # Verify canvas availability was checked
            mcp_tools_manager._ensure_canvas_available.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_to_canvas_query_operation(self, mcp_tools_manager):
        """Test _sync_to_canvas with query operation."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client, \
             patch.object(mcp_tools_manager, '_ensure_canvas_available', new=AsyncMock()):
            
            # Mock HTTP client to return success
            mock_result = {"elements": [{"id": "test-123"}]}
            mock_http_client.get_json = AsyncMock(return_value=mock_result)
            
            # Test data
            test_data = {}
            
            # Call the method
            result = await mcp_tools_manager._sync_to_canvas("query", test_data)
            
            # Verify the result
            assert result == mock_result
            # Verify HTTP client was called correctly
            mock_http_client.get_json.assert_called_once_with("/api/elements")
            # Verify canvas availability was checked
            mcp_tools_manager._ensure_canvas_available.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_to_canvas_unknown_operation(self, mcp_tools_manager):
        """Test _sync_to_canvas with unknown operation."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client, \
             patch.object(mcp_tools_manager, '_ensure_canvas_available', new=AsyncMock()), \
             patch('excalidraw_mcp.mcp_tools.logger') as mock_logger:
            
            # Test data
            test_data = {"id": "test-123"}
            
            # Call the method with unknown operation
            result = await mcp_tools_manager._sync_to_canvas("unknown", test_data)
            
            # Verify the result is None
            assert result is None
            # Verify error was logged
            mock_logger.error.assert_called_once()
            assert "Unknown sync operation: unknown" in str(mock_logger.error.call_args[0])
            # Verify canvas availability was checked
            mcp_tools_manager._ensure_canvas_available.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_to_canvas_exception_handling(self, mcp_tools_manager):
        """Test _sync_to_canvas handles exceptions correctly."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client, \
             patch.object(mcp_tools_manager, '_ensure_canvas_available', new=AsyncMock()), \
             patch('excalidraw_mcp.mcp_tools.logger') as mock_logger:
            
            # Mock HTTP client to raise an exception
            mock_http_client.post_json = AsyncMock(side_effect=Exception("Network error"))
            
            # Test data
            test_data = {"type": "rectangle", "x": 100, "y": 200}
            
            # Call the method and expect it to raise RuntimeError
            with pytest.raises(RuntimeError, match="Failed to sync create to canvas: Network error"):
                await mcp_tools_manager._sync_to_canvas("create", test_data)
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            # Verify canvas availability was checked
            mcp_tools_manager._ensure_canvas_available.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_element_success(self, mcp_tools_manager):
        """Test create_element method with successful creation."""
        with patch.object(mcp_tools_manager, '_sync_to_canvas', new=AsyncMock()), \
             patch.object(mcp_tools_manager.element_factory, 'create_element') as mock_create_element:
            
            # Mock element factory to return test data
            element_data = {"id": "test-123", "type": "rectangle", "x": 100, "y": 200}
            mock_create_element.return_value = element_data
            
            # Mock sync to return success
            sync_result = {"success": True, "element": element_data}
            mcp_tools_manager._sync_to_canvas.return_value = sync_result
            
            # Create a request model
            class ElementRequest(BaseModel):
                type: str
                x: float
                y: float
            
            request = ElementRequest(type="rectangle", x=100, y=200)
            
            # Call the method
            result = await mcp_tools_manager.create_element(request)
            
            # Verify the result
            assert result["success"] is True
            assert "element" in result
            assert "message" in result
            assert "Created rectangle element successfully" in result["message"]
            
            # Verify element factory was called
            mock_create_element.assert_called_once_with(request.dict())
            # Verify sync was called
            mcp_tools_manager._sync_to_canvas.assert_called_once_with("create", element_data)

    @pytest.mark.asyncio
    async def test_create_element_sync_failure(self, mcp_tools_manager):
        """Test create_element method when sync fails."""
        with patch.object(mcp_tools_manager, '_sync_to_canvas', new=AsyncMock()), \
             patch.object(mcp_tools_manager.element_factory, 'create_element') as mock_create_element:
            
            # Mock element factory to return test data
            element_data = {"id": "test-123", "type": "rectangle", "x": 100, "y": 200}
            mock_create_element.return_value = element_data
            
            # Mock sync to return failure
            sync_result = {"success": False, "error": "Sync failed"}
            mcp_tools_manager._sync_to_canvas.return_value = sync_result
            
            # Create a request model
            class ElementRequest(BaseModel):
                type: str
                x: float
                y: float
            
            request = ElementRequest(type="rectangle", x=100, y=200)
            
            # Call the method
            result = await mcp_tools_manager.create_element(request)
            
            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "element_data" in result
            assert result["element_data"] == element_data
            
            # Verify element factory was called
            mock_create_element.assert_called_once_with(request.dict())
            # Verify sync was called
            mcp_tools_manager._sync_to_canvas.assert_called_once_with("create", element_data)

    @pytest.mark.asyncio
    async def test_create_element_factory_exception(self, mcp_tools_manager):
        """Test create_element method when element factory raises exception."""
        with patch.object(mcp_tools_manager.element_factory, 'create_element') as mock_create_element:
            
            # Mock element factory to raise an exception
            mock_create_element.side_effect = Exception("Factory error")
            
            # Create a request model
            class ElementRequest(BaseModel):
                type: str
                x: float
                y: float
            
            request = ElementRequest(type="rectangle", x=100, y=200)
            
            # Call the method
            result = await mcp_tools_manager.create_element(request)
            
            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Factory error" in result["error"]
            
            # Verify element factory was called
            mock_create_element.assert_called_once_with(request.dict())

    @pytest.mark.asyncio
    async def test_update_element_success(self, mcp_tools_manager):
        """Test update_element method with successful update."""
        with patch.object(mcp_tools_manager, '_sync_to_canvas', new=AsyncMock()), \
             patch.object(mcp_tools_manager.element_factory, 'prepare_update_data') as mock_prepare_update:
            
            # Mock element factory to return test data
            update_data = {"id": "test-123", "x": 150, "y": 250}
            mock_prepare_update.return_value = update_data
            
            # Mock sync to return success
            sync_result = {"success": True}
            mcp_tools_manager._sync_to_canvas.return_value = sync_result
            
            # Create a request model
            class UpdateRequest(BaseModel):
                id: str
                x: float
                y: float
            
            request = UpdateRequest(id="test-123", x=150, y=250)
            
            # Call the method
            result = await mcp_tools_manager.update_element(request)
            
            # Verify the result
            assert result["success"] is True
            assert "element" in result
            assert "message" in result
            assert "Updated element test-123 successfully" in result["message"]
            
            # Verify element factory was called
            mock_prepare_update.assert_called_once_with(request.dict())
            # Verify sync was called
            mcp_tools_manager._sync_to_canvas.assert_called_once_with("update", update_data)

    @pytest.mark.asyncio
    async def test_delete_element_success(self, mcp_tools_manager):
        """Test delete_element method with successful deletion."""
        with patch.object(mcp_tools_manager, '_sync_to_canvas', new=AsyncMock()):
            
            # Mock sync to return success
            sync_result = {"success": True}
            mcp_tools_manager._sync_to_canvas.return_value = sync_result
            
            # Call the method
            result = await mcp_tools_manager.delete_element("test-123")
            
            # Verify the result
            assert result["success"] is True
            assert "message" in result
            assert "Deleted element test-123 successfully" in result["message"]
            
            # Verify sync was called
            mcp_tools_manager._sync_to_canvas.assert_called_once_with("delete", {"id": "test-123"})

    @pytest.mark.asyncio
    async def test_query_elements_success(self, mcp_tools_manager):
        """Test query_elements method with successful query."""
        with patch.object(mcp_tools_manager, '_sync_to_canvas', new=AsyncMock()):
            
            # Mock sync to return success
            mock_elements = [
                {"id": "1", "type": "rectangle"},
                {"id": "2", "type": "ellipse"}
            ]
            sync_result = {"elements": mock_elements}
            mcp_tools_manager._sync_to_canvas.return_value = sync_result
            
            # Create a request model
            class QueryRequest(BaseModel):
                type: str = None
            
            request = QueryRequest(type="rectangle")
            
            # Call the method
            result = await mcp_tools_manager.query_elements(request)
            
            # Verify the result
            assert result["success"] is True
            assert "elements" in result
            assert "count" in result
            assert result["count"] == 2
            assert result["elements"] == mock_elements
            
            # Verify sync was called
            mcp_tools_manager._sync_to_canvas.assert_called_once_with("query", request.dict())

    @pytest.mark.asyncio
    async def test_batch_create_elements_success(self, mcp_tools_manager):
        """Test batch_create_elements method with successful creation."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client:
            
            # Mock HTTP client to return success
            mock_result = {"success": True, "count": 2}
            mock_http_client.post_json = AsyncMock(return_value=mock_result)
            
            # Create a request model
            class ElementData(BaseModel):
                type: str
                x: float
                y: float
            
            class BatchRequest(BaseModel):
                elements: list[ElementData]
            
            elements_data = [
                ElementData(type="rectangle", x=100, y=200),
                ElementData(type="ellipse", x=150, y=250)
            ]
            request = BatchRequest(elements=elements_data)
            
            # Call the method
            result = await mcp_tools_manager.batch_create_elements(request)
            
            # Verify the result
            assert result["success"] is True
            assert "count" in result
            assert result["count"] == 2
            assert "message" in result
            
            # Verify HTTP client was called
            mock_http_client.post_json.assert_called_once()
            # Verify arguments
            call_args = mock_http_client.post_json.call_args
            assert call_args[0][0] == "/api/elements/batch"

    @pytest.mark.asyncio
    async def test_group_elements_success(self, mcp_tools_manager):
        """Test group_elements method with successful grouping."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client:
            
            # Mock HTTP client to return success
            mock_result = {"success": True, "groupId": "group-123"}
            mock_http_client.post_json = AsyncMock(return_value=mock_result)
            
            # Call the method
            result = await mcp_tools_manager.group_elements(["element-1", "element-2"])
            
            # Verify the result
            assert result["success"] is True
            assert "group_id" in result
            assert result["group_id"] == "group-123"
            assert "message" in result
            
            # Verify HTTP client was called
            mock_http_client.post_json.assert_called_once()
            # Verify arguments
            call_args = mock_http_client.post_json.call_args
            assert call_args[0][0] == "/api/elements/group"
            assert call_args[0][1]["elementIds"] == ["element-1", "element-2"]

    @pytest.mark.asyncio
    async def test_ungroup_elements_success(self, mcp_tools_manager):
        """Test ungroup_elements method with successful ungrouping."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client:
            
            # Mock HTTP client to return success
            mock_http_client.delete = AsyncMock(return_value=True)
            
            # Call the method
            result = await mcp_tools_manager.ungroup_elements("group-123")
            
            # Verify the result
            assert result["success"] is True
            assert "message" in result
            
            # Verify HTTP client was called
            mock_http_client.delete.assert_called_once_with("/api/elements/group/group-123")

    @pytest.mark.asyncio
    async def test_align_elements_success(self, mcp_tools_manager):
        """Test align_elements method with successful alignment."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client:
            
            # Mock HTTP client to return success
            mock_result = {"success": True}
            mock_http_client.post_json = AsyncMock(return_value=mock_result)
            
            # Create a request model
            class AlignRequest(BaseModel):
                elementIds: list[str]
                alignment: str
            
            request = AlignRequest(elementIds=["element-1", "element-2"], alignment="center")
            
            # Call the method
            result = await mcp_tools_manager.align_elements(request)
            
            # Verify the result
            assert result["success"] is True
            assert "message" in result
            
            # Verify HTTP client was called
            mock_http_client.post_json.assert_called_once()
            # Verify arguments
            call_args = mock_http_client.post_json.call_args
            assert call_args[0][0] == "/api/elements/align"

    @pytest.mark.asyncio
    async def test_distribute_elements_success(self, mcp_tools_manager):
        """Test distribute_elements method with successful distribution."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client:
            
            # Mock HTTP client to return success
            mock_result = {"success": True}
            mock_http_client.post_json = AsyncMock(return_value=mock_result)
            
            # Create a request model
            class DistributeRequest(BaseModel):
                elementIds: list[str]
                direction: str
            
            request = DistributeRequest(elementIds=["element-1", "element-2"], direction="horizontal")
            
            # Call the method
            result = await mcp_tools_manager.distribute_elements(request)
            
            # Verify the result
            assert result["success"] is True
            assert "message" in result
            
            # Verify HTTP client was called
            mock_http_client.post_json.assert_called_once()
            # Verify arguments
            call_args = mock_http_client.post_json.call_args
            assert call_args[0][0] == "/api/elements/distribute"

    @pytest.mark.asyncio
    async def test_lock_elements_success(self, mcp_tools_manager):
        """Test lock_elements method with successful locking."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client:
            
            # Mock HTTP client to return success
            mock_result = {"success": True}
            mock_http_client.post_json = AsyncMock(return_value=mock_result)
            
            # Call the method
            result = await mcp_tools_manager.lock_elements(["element-1", "element-2"])
            
            # Verify the result
            assert result["success"] is True
            assert "message" in result
            
            # Verify HTTP client was called
            mock_http_client.post_json.assert_called_once()
            # Verify arguments
            call_args = mock_http_client.post_json.call_args
            assert call_args[0][0] == "/api/elements/lock"
            assert call_args[0][1]["locked"] is True

    @pytest.mark.asyncio
    async def test_unlock_elements_success(self, mcp_tools_manager):
        """Test unlock_elements method with successful unlocking."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client:
            
            # Mock HTTP client to return success
            mock_result = {"success": True}
            mock_http_client.post_json = AsyncMock(return_value=mock_result)
            
            # Call the method
            result = await mcp_tools_manager.unlock_elements(["element-1", "element-2"])
            
            # Verify the result
            assert result["success"] is True
            assert "message" in result
            
            # Verify HTTP client was called
            mock_http_client.post_json.assert_called_once()
            # Verify arguments
            call_args = mock_http_client.post_json.call_args
            assert call_args[0][0] == "/api/elements/lock"
            assert call_args[0][1]["locked"] is False

    @pytest.mark.asyncio
    async def test_get_resource_success(self, mcp_tools_manager):
        """Test get_resource method with successful resource retrieval."""
        with patch('excalidraw_mcp.mcp_tools.http_client') as mock_http_client:
            
            # Mock HTTP client to return success
            mock_result = {"scene": "test-scene-data"}
            mock_http_client.get_json = AsyncMock(return_value=mock_result)
            
            # Call the method
            result = await mcp_tools_manager.get_resource("scene")
            
            # Verify the result
            assert result["success"] is True
            assert "resource_type" in result
            assert result["resource_type"] == "scene"
            assert "data" in result
            assert result["data"] == mock_result
            
            # Verify HTTP client was called
            mock_http_client.get_json.assert_called_once_with("/api/scene")

    @pytest.mark.asyncio
    async def test_get_resource_invalid_type(self, mcp_tools_manager):
        """Test get_resource method with invalid resource type."""
        # Call the method with invalid type
        result = await mcp_tools_manager.get_resource("invalid_type")
        
        # Verify the result indicates error
        assert result["success"] is False
        assert "error" in result
        assert "Invalid resource type" in result["error"]