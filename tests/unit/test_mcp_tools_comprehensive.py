"""Comprehensive tests for MCPToolsManager with mocked dependencies."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from excalidraw_mcp.mcp_tools import MCPToolsManager
from excalidraw_mcp.element_factory import ElementFactory


@pytest.fixture
def mock_mcp():
    """Create a mock FastMCP instance."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    return mcp


@pytest.fixture
def mock_process_manager():
    """Create a mock process manager."""
    with patch("excalidraw_mcp.mcp_tools.process_manager") as mock:
        mock.ensure_running = AsyncMock(return_value=True)
        yield mock


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    with patch("excalidraw_mcp.mcp_tools.http_client") as mock:
        mock.post_json = AsyncMock(return_value={"success": True, "element": {}})
        mock.put_json = AsyncMock(return_value={"success": True, "element": {}})
        mock.delete = AsyncMock(return_value=True)
        mock.get_json = AsyncMock(return_value={"elements": []})
        yield mock


@pytest.fixture
def manager(mock_mcp):
    """Create MCPToolsManager instance."""
    return MCPToolsManager(mock_mcp)


class TestMCPToolsManagerInitialization:
    """Test MCPToolsManager initialization."""

    def test_manager_initialization(self, mock_mcp):
        """Test that manager initializes correctly."""
        manager = MCPToolsManager(mock_mcp)

        assert manager.mcp == mock_mcp
        assert isinstance(manager.element_factory, ElementFactory)

    def test_manager_registers_tools(self, mock_mcp):
        """Test that manager registers all tools."""
        manager = MCPToolsManager(mock_mcp)

        # Check that mcp.tool was called for each expected tool
        expected_tools = [
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
        ]

        assert mock_mcp.tool.call_count == len(expected_tools)


class TestRequestToDict:
    """Test _request_to_dict method."""

    def test_request_to_dict_with_pydantic_model(self, manager):
        """Test conversion from Pydantic model."""
        # Create a mock Pydantic model
        request = MagicMock()
        request.model_dump = MagicMock(return_value={"type": "rectangle", "x": 10})

        result = manager._request_to_dict(request)

        assert result == {"type": "rectangle", "x": 10}
        request.model_dump.assert_called_once()

    def test_request_to_dict_with_dict(self, manager):
        """Test that dict is returned as-is."""
        request = {"type": "rectangle", "x": 10}

        result = manager._request_to_dict(request)

        assert result == {"type": "rectangle", "x": 10}

    def test_request_to_dict_with_legacy_dict_method(self, manager):
        """Test conversion from legacy dict method."""
        request = MagicMock()
        del request.model_dump  # Remove model_dump
        request.dict = MagicMock(return_value={"type": "rectangle"})

        result = manager._request_to_dict(request)

        assert result == {"type": "rectangle"}
        request.dict.assert_called_once()


class TestEnsureCanvasAvailable:
    """Test _ensure_canvas_available method."""

    @pytest.mark.asyncio
    async def test_ensure_canvas_available_success(self, manager, mock_process_manager):
        """Test successful canvas availability check."""
        result = await manager._ensure_canvas_available()

        assert result is True
        mock_process_manager.ensure_running.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_canvas_available_failure(self, manager, mock_process_manager):
        """Test canvas availability failure."""
        mock_process_manager.ensure_running = AsyncMock(return_value=False)

        with pytest.raises(RuntimeError, match="Canvas server is not available"):
            await manager._ensure_canvas_available()


class TestSyncToCanvas:
    """Test _sync_to_canvas method."""

    @pytest.mark.asyncio
    async def test_sync_create_operation(self, manager, mock_process_manager, mock_http_client):
        """Test sync for create operation."""
        data = {"type": "rectangle", "x": 10}

        result = await manager._sync_to_canvas("create", data)

        assert result is not None
        mock_http_client.post_json.assert_called_once_with("/api/elements", data)

    @pytest.mark.asyncio
    async def test_sync_update_operation(self, manager, mock_http_client):
        """Test sync for update operation."""
        data = {"id": "elem123", "x": 20}

        result = await manager._sync_to_canvas("update", data)

        assert result is not None
        # ID should be popped from data
        mock_http_client.put_json.assert_called_once_with("/api/elements/elem123", {"x": 20})

    @pytest.mark.asyncio
    async def test_sync_delete_operation(self, manager, mock_http_client):
        """Test sync for delete operation."""
        data = {"id": "elem123"}

        result = await manager._sync_to_canvas("delete", data)

        assert result == {"success": True}
        mock_http_client.delete.assert_called_once_with("/api/elements/elem123")

    @pytest.mark.asyncio
    async def test_sync_query_operation(self, manager, mock_http_client):
        """Test sync for query operation."""
        data = {"type": "rectangle"}

        result = await manager._sync_to_canvas("query", data)

        assert result is not None
        mock_http_client.get_json.assert_called_once_with("/api/elements")

    @pytest.mark.asyncio
    async def test_sync_unknown_operation(self, manager):
        """Test sync with unknown operation."""
        result = await manager._sync_to_canvas("unknown", {})

        assert result is None

    @pytest.mark.asyncio
    async def test_sync_handles_exceptions(self, manager, mock_process_manager):
        """Test that sync handles exceptions gracefully."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            mock_http_client.post_json = AsyncMock(side_effect=Exception("Connection error"))

            with pytest.raises(RuntimeError, match="Failed to sync create"):
                await manager._sync_to_canvas("create", {})


class TestCreateElement:
    """Test create_element tool."""

    @pytest.mark.asyncio
    async def test_create_element_success(self, manager, mock_http_client):
        """Test successful element creation."""
        request = {"type": "rectangle", "x": 10, "y": 20}

        result = await manager.create_element(request)

        assert result["success"] is True
        assert "element" in result
        assert "Created" in result["message"]

    @pytest.mark.asyncio
    async def test_create_element_with_pydantic_request(self, manager, mock_http_client):
        """Test element creation with Pydantic request."""
        request = MagicMock()
        request.model_dump = MagicMock(return_value={"type": "rectangle", "x": 10})

        result = await manager.create_element(request)

        assert result["success"] is True
        request.model_dump.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_element_canvas_failure(self, manager, mock_http_client):
        """Test element creation when canvas fails."""
        mock_http_client.post_json = AsyncMock(return_value={"success": False})

        request = {"type": "rectangle"}

        result = await manager.create_element(request)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_element_exception(self, manager, mock_http_client):
        """Test element creation handles exceptions."""
        mock_http_client.post_json = AsyncMock(side_effect=Exception("Error"))

        request = {"type": "rectangle"}

        result = await manager.create_element(request)

        assert result["success"] is False
        assert "error" in result


class TestUpdateElement:
    """Test update_element tool."""

    @pytest.mark.asyncio
    async def test_update_element_success(self, manager, mock_http_client):
        """Test successful element update."""
        request = {"id": "elem123", "x": 50, "y": 60}

        result = await manager.update_element(request)

        assert result["success"] is True
        assert "Updated" in result["message"]

    @pytest.mark.asyncio
    async def test_update_element_missing_id(self, manager):
        """Test update with missing ID."""
        request = {"x": 50, "y": 60}

        result = await manager.update_element(request)

        assert result["success"] is False
        assert "Element ID is required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_element_canvas_failure(self, manager, mock_http_client):
        """Test update when canvas fails."""
        mock_http_client.put_json = AsyncMock(return_value={"success": False})

        request = {"id": "elem123", "x": 50}

        result = await manager.update_element(request)

        assert result["success"] is False


class TestDeleteElement:
    """Test delete_element tool."""

    @pytest.mark.asyncio
    async def test_delete_element_success(self, manager, mock_http_client):
        """Test successful element deletion."""
        result = await manager.delete_element("elem123")

        assert result["success"] is True
        assert "Deleted" in result["message"]
        mock_http_client.delete.assert_called_once_with("/api/elements/elem123")

    @pytest.mark.asyncio
    async def test_delete_element_failure(self, manager, mock_http_client):
        """Test deletion when canvas fails."""
        mock_http_client.delete = AsyncMock(return_value=False)

        result = await manager.delete_element("elem123")

        assert result["success"] is False


class TestQueryElements:
    """Test query_elements tool."""

    @pytest.mark.asyncio
    async def test_query_elements_success(self, manager, mock_http_client):
        """Test successful element query."""
        mock_http_client.get_json = AsyncMock(
            return_value={"elements": [{"id": "elem1"}, {"id": "elem2"}]}
        )

        request = {"type": "rectangle"}

        result = await manager.query_elements(request)

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["elements"]) == 2

    @pytest.mark.asyncio
    async def test_query_elements_empty(self, manager, mock_http_client):
        """Test query with no results."""
        mock_http_client.get_json = AsyncMock(return_value={"elements": []})

        request = {}

        result = await manager.query_elements(request)

        assert result["success"] is True
        assert result["count"] == 0
        assert result["elements"] == []


class TestBatchCreateElements:
    """Test batch_create_elements tool."""

    @pytest.mark.asyncio
    async def test_batch_create_success(self, manager, mock_http_client):
        """Test successful batch creation."""
        request = {
            "elements": [
                {"type": "rectangle", "x": 0, "y": 0},
                {"type": "ellipse", "x": 100, "y": 0},
            ]
        }

        result = await manager.batch_create_elements(request)

        assert result["success"] is True
        assert result["count"] == 2
        assert "Created 2 elements" in result["message"]

    @pytest.mark.asyncio
    async def test_batch_create_no_elements(self, manager):
        """Test batch creation with no elements."""
        request = {"elements": []}

        result = await manager.batch_create_elements(request)

        assert result["success"] is False
        assert "No elements provided" in result["error"]

    @pytest.mark.asyncio
    async def test_batch_create_exceeds_limit(self, manager):
        """Test batch creation exceeds size limit."""
        request = {
            "elements": [
                {"type": "rectangle", "x": i, "y": 0}
                for i in range(51)  # Exceeds max_batch_size of 50
            ]
        }

        result = await manager.batch_create_elements(request)

        assert result["success"] is False
        assert "exceeds maximum limit" in result["error"]

    @pytest.mark.asyncio
    async def test_batch_create_canvas_failure(self, manager, mock_http_client):
        """Test batch creation when canvas fails."""
        mock_http_client.post_json = AsyncMock(return_value={"success": False})

        request = {"elements": [{"type": "rectangle"}]}

        result = await manager.batch_create_elements(request)

        assert result["success"] is False


class TestGroupElements:
    """Test group_elements tool."""

    @pytest.mark.asyncio
    async def test_group_elements_success(self, manager, mock_http_client):
        """Test successful element grouping."""
        mock_http_client.post_json = AsyncMock(
            return_value={"success": True, "groupId": "group123"}
        )

        element_ids = ["elem1", "elem2", "elem3"]

        result = await manager.group_elements(element_ids)

        assert result["success"] is True
        assert result["group_id"] == "group123"
        assert "Grouped 3 elements" in result["message"]

    @pytest.mark.asyncio
    async def test_group_elements_insufficient_count(self, manager):
        """Test grouping with insufficient elements."""
        result = await manager.group_elements(["elem1"])

        assert result["success"] is False
        assert "At least 2 elements required" in result["error"]

    @pytest.mark.asyncio
    async def test_group_elements_canvas_failure(self, manager, mock_http_client):
        """Test grouping when canvas fails."""
        mock_http_client.post_json = AsyncMock(return_value={"success": False})

        result = await manager.group_elements(["elem1", "elem2"])

        assert result["success"] is False


class TestUngroupElements:
    """Test ungroup_elements tool."""

    @pytest.mark.asyncio
    async def test_ungroup_elements_success(self, manager, mock_http_client):
        """Test successful element ungrouping."""
        mock_http_client.delete = AsyncMock(return_value=True)

        result = await manager.ungroup_elements("group123")

        assert result["success"] is True
        assert "Ungrouped" in result["message"]
        mock_http_client.delete.assert_called_once_with("/api/elements/group/group123")

    @pytest.mark.asyncio
    async def test_ungroup_elements_failure(self, manager, mock_http_client):
        """Test ungrouping when canvas fails."""
        mock_http_client.delete = AsyncMock(return_value=False)

        result = await manager.ungroup_elements("group123")

        assert result["success"] is False


class TestAlignElements:
    """Test align_elements tool."""

    @pytest.mark.asyncio
    async def test_align_elements_success(self, manager, mock_http_client):
        """Test successful element alignment."""
        request = {
            "elementIds": ["elem1", "elem2"],
            "alignment": "left",
        }

        result = await manager.align_elements(request)

        assert result["success"] is True
        assert "Aligned 2 elements" in result["message"]

    @pytest.mark.asyncio
    async def test_align_elements_missing_params(self, manager):
        """Test alignment with missing parameters."""
        request = {"elementIds": ["elem1"]}  # Missing alignment

        result = await manager.align_elements(request)

        assert result["success"] is False
        assert "Element IDs and alignment are required" in result["error"]

    @pytest.mark.asyncio
    async def test_align_elements_canvas_failure(self, manager, mock_http_client):
        """Test alignment when canvas fails."""
        mock_http_client.post_json = AsyncMock(return_value={"success": False})

        request = {"elementIds": ["elem1"], "alignment": "left"}

        result = await manager.align_elements(request)

        assert result["success"] is False


class TestDistributeElements:
    """Test distribute_elements tool."""

    @pytest.mark.asyncio
    async def test_distribute_elements_success(self, manager, mock_http_client):
        """Test successful element distribution."""
        request = {
            "elementIds": ["elem1", "elem2", "elem3"],
            "direction": "horizontal",
        }

        result = await manager.distribute_elements(request)

        assert result["success"] is True
        assert "Distributed 3 elements" in result["message"]

    @pytest.mark.asyncio
    async def test_distribute_elements_missing_params(self, manager):
        """Test distribution with missing parameters."""
        request = {"elementIds": ["elem1"]}  # Missing direction

        result = await manager.distribute_elements(request)

        assert result["success"] is False
        assert "Element IDs and direction are required" in result["error"]

    @pytest.mark.asyncio
    async def test_distribute_elements_canvas_failure(self, manager, mock_http_client):
        """Test distribution when canvas fails."""
        mock_http_client.post_json = AsyncMock(return_value={"success": False})

        request = {"elementIds": ["elem1"], "direction": "vertical"}

        result = await manager.distribute_elements(request)

        assert result["success"] is False


class TestLockUnlockElements:
    """Test lock_elements and unlock_elements tools."""

    @pytest.mark.asyncio
    async def test_lock_elements_success(self, manager, mock_http_client):
        """Test successful element locking."""
        element_ids = ["elem1", "elem2"]

        result = await manager.lock_elements(element_ids)

        assert result["success"] is True
        assert "Locked 2 elements" in result["message"]
        mock_http_client.post_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_unlock_elements_success(self, manager, mock_http_client):
        """Test successful element unlocking."""
        element_ids = ["elem1", "elem2"]

        result = await manager.unlock_elements(element_ids)

        assert result["success"] is True
        assert "Unlocked 2 elements" in result["message"]
        mock_http_client.post_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_lock_elements_failure(self, manager, mock_http_client):
        """Test locking when canvas fails."""
        mock_http_client.post_json = AsyncMock(return_value={"success": False})

        result = await manager.lock_elements(["elem1"])

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_unlock_elements_failure(self, manager, mock_http_client):
        """Test unlocking when canvas fails."""
        mock_http_client.post_json = AsyncMock(return_value={"success": False})

        result = await manager.unlock_elements(["elem1"])

        assert result["success"] is False


class TestGetResource:
    """Test get_resource tool."""

    @pytest.mark.asyncio
    async def test_get_scene_resource(self, manager, mock_http_client):
        """Test getting scene resource."""
        mock_http_client.get_json = AsyncMock(return_value={"elements": []})

        result = await manager.get_resource("scene")

        assert result["success"] is True
        assert result["resource_type"] == "scene"
        mock_http_client.get_json.assert_called_once_with("/api/scene")

    @pytest.mark.asyncio
    async def test_get_library_resource(self, manager, mock_http_client):
        """Test getting library resource."""
        mock_http_client.get_json = AsyncMock(return_value={"library": []})

        result = await manager.get_resource("library")

        assert result["success"] is True
        assert result["resource_type"] == "library"

    @pytest.mark.asyncio
    async def test_get_theme_resource(self, manager, mock_http_client):
        """Test getting theme resource."""
        mock_http_client.get_json = AsyncMock(return_value={"theme": "light"})

        result = await manager.get_resource("theme")

        assert result["success"] is True
        assert result["resource_type"] == "theme"

    @pytest.mark.asyncio
    async def test_get_elements_resource(self, manager, mock_http_client):
        """Test getting elements resource."""
        mock_http_client.get_json = AsyncMock(return_value={"elements": []})

        result = await manager.get_resource("elements")

        assert result["success"] is True
        assert result["resource_type"] == "elements"

    @pytest.mark.asyncio
    async def test_get_invalid_resource(self, manager):
        """Test getting invalid resource type."""
        result = await manager.get_resource("invalid")

        assert result["success"] is False
        assert "Invalid resource type" in result["error"]

    @pytest.mark.asyncio
    async def test_get_resource_canvas_failure(self, manager, mock_http_client):
        """Test resource retrieval when canvas fails."""
        mock_http_client.get_json = AsyncMock(return_value=None)

        result = await manager.get_resource("scene")

        assert result["success"] is False


class TestElementFactoryIntegration:
    """Test integration with ElementFactory."""

    @pytest.mark.asyncio
    async def test_create_element_uses_factory(self, manager, mock_http_client):
        """Test that create_element uses element factory."""
        request = {"type": "rectangle", "x": 10, "y": 20}

        await manager.create_element(request)

        # Check that HTTP client was called with factory-processed data
        call_args = mock_http_client.post_json.call_args
        assert call_args is not None

        # The element should have factory-added fields
        sent_data = call_args[0][1]  # Second positional argument
        assert "id" in sent_data  # Factory adds ID
        assert "createdAt" in sent_data  # Factory adds timestamp
        assert "updatedAt" in sent_data  # Factory adds timestamp

    @pytest.mark.asyncio
    async def test_batch_create_uses_factory(self, manager, mock_http_client):
        """Test that batch_create uses element factory."""
        request = {
            "elements": [
                {"type": "rectangle", "x": 0, "y": 0},
                {"type": "ellipse", "x": 100, "y": 0},
            ]
        }

        await manager.batch_create_elements(request)

        # Check that elements have factory-added fields
        call_args = mock_http_client.post_json.call_args
        sent_data = call_args[0][1]

        for element in sent_data["elements"]:
            assert "id" in element
            assert "createdAt" in element

    @pytest.mark.asyncio
    async def test_update_element_uses_factory(self, manager, mock_http_client):
        """Test that update_element uses element factory."""
        request = {"id": "elem123", "x": 50, "y": 60}

        await manager.update_element(request)

        # Check that factory prepared the update data
        call_args = mock_http_client.put_json.call_args
        sent_data = call_args[0][1]  # Second positional argument (after URL)

        assert "updatedAt" in sent_data  # Factory adds update timestamp
        assert sent_data["x"] == 50.0  # Factory converts to float
