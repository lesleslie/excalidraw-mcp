"""Additional tests to cover missing lines in mcp_tools.py"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic import BaseModel

from excalidraw_mcp.mcp_tools import MCPToolsManager


class TestMCPToolsCoverage:
    """Additional tests to cover missing lines in mcp_tools.py"""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance."""
        return MagicMock()

    @pytest.fixture
    def mcp_tools_manager(self, mock_mcp):
        """Create an MCPToolsManager instance with a mock MCP."""
        with (
            patch("excalidraw_mcp.mcp_tools.ElementFactory") as mock_factory_class,
            patch("excalidraw_mcp.mcp_tools.http_client"),
            patch("excalidraw_mcp.mcp_tools.process_manager"),
        ):
            # Mock the element factory instance
            mock_factory_instance = Mock()
            mock_factory_class.return_value = mock_factory_instance

            # Create the manager
            manager = MCPToolsManager(mock_mcp)

            # Store mocks for access in tests
            manager._mock_mcp = mock_mcp
            manager._mock_factory = mock_factory_instance

            return manager

    @pytest.mark.asyncio
    async def test_update_element_failure(self, mcp_tools_manager):
        """Test update_element method when sync fails."""
        with (
            patch.object(mcp_tools_manager, "_sync_to_canvas") as mock_sync,
            patch.object(
                mcp_tools_manager.element_factory, "prepare_update_data"
            ) as mock_prepare_update,
        ):
            # Mock element factory to return test data
            update_data = {"id": "test-123", "x": 150, "y": 250}
            mock_prepare_update.return_value = update_data

            # Mock sync to return failure
            sync_result = {"success": False, "error": "Sync failed"}
            mock_sync.return_value = sync_result

            # Create a request model
            class UpdateRequest(BaseModel):
                id: str
                x: float
                y: float

            request = UpdateRequest(id="test-123", x=150, y=250)

            # Call the method
            result = await mcp_tools_manager.update_element(request)

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Failed to update element on canvas" in result["error"]

            # Verify element factory was called
            mock_prepare_update.assert_called_once_with(request.dict())
            # Verify sync was called
            mock_sync.assert_called_once_with("update", update_data)

    @pytest.mark.asyncio
    async def test_update_element_exception(self, mcp_tools_manager):
        """Test update_element method when exception occurs."""
        with patch.object(
            mcp_tools_manager.element_factory, "prepare_update_data"
        ) as mock_prepare_update:
            # Mock element factory to raise an exception
            mock_prepare_update.side_effect = Exception("Factory error")

            # Create a request model
            class UpdateRequest(BaseModel):
                id: str
                x: float
                y: float

            request = UpdateRequest(id="test-123", x=150, y=250)

            # Call the method
            result = await mcp_tools_manager.update_element(request)

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Factory error" in result["error"]

            # Verify element factory was called
            mock_prepare_update.assert_called_once_with(request.dict())

    @pytest.mark.asyncio
    async def test_delete_element_failure(self, mcp_tools_manager):
        """Test delete_element method when sync fails."""
        with patch.object(mcp_tools_manager, "_sync_to_canvas") as mock_sync:
            # Mock sync to return failure
            sync_result = {"success": False, "error": "Sync failed"}
            mock_sync.return_value = sync_result

            # Call the method
            result = await mcp_tools_manager.delete_element("test-123")

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Failed to delete element from canvas" in result["error"]

            # Verify sync was called
            mock_sync.assert_called_once_with("delete", {"id": "test-123"})

    @pytest.mark.asyncio
    async def test_delete_element_exception(self, mcp_tools_manager):
        """Test delete_element method when exception occurs."""
        with patch.object(mcp_tools_manager, "_sync_to_canvas") as mock_sync:
            # Mock sync to raise an exception
            mock_sync.side_effect = Exception("Sync error")

            # Call the method
            result = await mcp_tools_manager.delete_element("test-123")

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Sync error" in result["error"]

            # Verify sync was called
            mock_sync.assert_called_once_with("delete", {"id": "test-123"})

    @pytest.mark.asyncio
    async def test_query_elements_failure(self, mcp_tools_manager):
        """Test query_elements method when sync fails."""
        with patch.object(mcp_tools_manager, "_sync_to_canvas") as mock_sync:
            # Mock sync to return failure
            sync_result = None
            mock_sync.return_value = sync_result

            # Create a request model
            class QueryRequest(BaseModel):
                type: str = None

            request = QueryRequest(type="rectangle")

            # Call the method
            result = await mcp_tools_manager.query_elements(request)

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Failed to query elements from canvas" in result["error"]

            # Verify sync was called
            mock_sync.assert_called_once_with("query", request.dict())

    @pytest.mark.asyncio
    async def test_query_elements_exception(self, mcp_tools_manager):
        """Test query_elements method when exception occurs."""
        with patch.object(mcp_tools_manager, "_sync_to_canvas") as mock_sync:
            # Mock sync to raise an exception
            mock_sync.side_effect = Exception("Sync error")

            # Create a request model
            class QueryRequest(BaseModel):
                type: str = None

            request = QueryRequest(type="rectangle")

            # Call the method
            result = await mcp_tools_manager.query_elements(request)

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Sync error" in result["error"]

            # Verify sync was called
            mock_sync.assert_called_once_with("query", request.dict())

    @pytest.mark.asyncio
    async def test_batch_create_elements_no_elements(self, mcp_tools_manager):
        """Test batch_create_elements method with no elements."""

        # Create a request model with no elements
        class ElementData(BaseModel):
            type: str
            x: float
            y: float

        class BatchRequest(BaseModel):
            elements: list[ElementData] = []

        request = BatchRequest(elements=[])

        # Call the method
        result = await mcp_tools_manager.batch_create_elements(request)

        # Verify the result indicates failure
        assert result["success"] is False
        assert "error" in result
        assert "No elements provided for batch creation" in result["error"]

    @pytest.mark.asyncio
    async def test_batch_create_elements_too_many_elements(self, mcp_tools_manager):
        """Test batch_create_elements method with too many elements."""

        # Create a request model with too many elements
        class ElementData(BaseModel):
            type: str
            x: float
            y: float

        class BatchRequest(BaseModel):
            elements: list[ElementData]

        # Create more than 50 elements
        elements_data = [
            ElementData(type="rectangle", x=float(i), y=float(i)) for i in range(51)
        ]
        request = BatchRequest(elements=elements_data)

        # Call the method
        result = await mcp_tools_manager.batch_create_elements(request)

        # Verify the result indicates failure
        assert result["success"] is False
        assert "error" in result
        assert "Batch size exceeds maximum limit" in result["error"]

    @pytest.mark.asyncio
    async def test_batch_create_elements_sync_failure(self, mcp_tools_manager):
        """Test batch_create_elements method when sync fails."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to return failure
            mock_http_client.post_json = AsyncMock(return_value=None)

            # Create a request model
            class ElementData(BaseModel):
                type: str
                x: float
                y: float

            class BatchRequest(BaseModel):
                elements: list[ElementData]

            elements_data = [
                ElementData(type="rectangle", x=100, y=200),
                ElementData(type="ellipse", x=150, y=250),
            ]
            request = BatchRequest(elements=elements_data)

            # Mock element factory
            with patch.object(
                mcp_tools_manager.element_factory, "create_element"
            ) as mock_create_element:
                mock_create_element.side_effect = lambda x: x  # Just return the input

                # Call the method
                result = await mcp_tools_manager.batch_create_elements(request)

                # Verify the result indicates failure
                assert result["success"] is False
                assert "error" in result
                assert "Failed to create batch elements on canvas" in result["error"]

                # Verify HTTP client was called
                mock_http_client.post_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_create_elements_exception(self, mcp_tools_manager):
        """Test batch_create_elements method when exception occurs."""

        # Create a request model
        class ElementData(BaseModel):
            type: str
            x: float
            y: float

        class BatchRequest(BaseModel):
            elements: list[ElementData]

        elements_data = [
            ElementData(type="rectangle", x=100, y=200),
            ElementData(type="ellipse", x=150, y=250),
        ]
        request = BatchRequest(elements=elements_data)

        # Mock element factory to raise an exception
        with patch.object(
            mcp_tools_manager.element_factory, "create_element"
        ) as mock_create_element:
            mock_create_element.side_effect = Exception("Factory error")

            # Call the method
            result = await mcp_tools_manager.batch_create_elements(request)

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Factory error" in result["error"]

    @pytest.mark.asyncio
    async def test_group_elements_too_few_elements(self, mcp_tools_manager):
        """Test group_elements method with too few elements."""
        # Call the method with only one element
        result = await mcp_tools_manager.group_elements(["element-1"])

        # Verify the result indicates failure
        assert result["success"] is False
        assert "error" in result
        assert "At least 2 elements required for grouping" in result["error"]

    @pytest.mark.asyncio
    async def test_group_elements_sync_failure(self, mcp_tools_manager):
        """Test group_elements method when sync fails."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to return failure
            mock_http_client.post_json = AsyncMock(return_value=None)

            # Call the method
            result = await mcp_tools_manager.group_elements(["element-1", "element-2"])

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Failed to group elements on canvas" in result["error"]

            # Verify HTTP client was called
            mock_http_client.post_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_group_elements_exception(self, mcp_tools_manager):
        """Test group_elements method when exception occurs."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to raise an exception
            mock_http_client.post_json = AsyncMock(
                side_effect=Exception("Network error")
            )

            # Call the method
            result = await mcp_tools_manager.group_elements(["element-1", "element-2"])

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_ungroup_elements_sync_failure(self, mcp_tools_manager):
        """Test ungroup_elements method when sync fails."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to return failure
            mock_http_client.delete = AsyncMock(return_value=False)

            # Call the method
            result = await mcp_tools_manager.ungroup_elements("group-123")

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Failed to ungroup elements on canvas" in result["error"]

            # Verify HTTP client was called
            mock_http_client.delete.assert_called_once_with(
                "/api/elements/group/group-123"
            )

    @pytest.mark.asyncio
    async def test_ungroup_elements_exception(self, mcp_tools_manager):
        """Test ungroup_elements method when exception occurs."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to raise an exception
            mock_http_client.delete = AsyncMock(side_effect=Exception("Network error"))

            # Call the method
            result = await mcp_tools_manager.ungroup_elements("group-123")

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_align_elements_missing_data(self, mcp_tools_manager):
        """Test align_elements method with missing data."""

        # Create a request model with missing data
        class AlignRequest(BaseModel):
            elementIds: list[str] = []
            alignment: str = ""

        request = AlignRequest(elementIds=[], alignment="")

        # Call the method
        result = await mcp_tools_manager.align_elements(request)

        # Verify the result indicates failure
        assert result["success"] is False
        assert "error" in result
        assert "Element IDs and alignment are required" in result["error"]

    @pytest.mark.asyncio
    async def test_align_elements_sync_failure(self, mcp_tools_manager):
        """Test align_elements method when sync fails."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to return failure
            mock_http_client.post_json = AsyncMock(return_value=None)

            # Create a request model
            class AlignRequest(BaseModel):
                elementIds: list[str]
                alignment: str

            request = AlignRequest(
                elementIds=["element-1", "element-2"], alignment="center"
            )

            # Call the method
            result = await mcp_tools_manager.align_elements(request)

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Failed to align elements on canvas" in result["error"]

            # Verify HTTP client was called
            mock_http_client.post_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_align_elements_exception(self, mcp_tools_manager):
        """Test align_elements method when exception occurs."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to raise an exception
            mock_http_client.post_json = AsyncMock(
                side_effect=Exception("Network error")
            )

            # Create a request model
            class AlignRequest(BaseModel):
                elementIds: list[str]
                alignment: str

            request = AlignRequest(
                elementIds=["element-1", "element-2"], alignment="center"
            )

            # Call the method
            result = await mcp_tools_manager.align_elements(request)

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_distribute_elements_missing_data(self, mcp_tools_manager):
        """Test distribute_elements method with missing data."""

        # Create a request model with missing data
        class DistributeRequest(BaseModel):
            elementIds: list[str] = []
            direction: str = ""

        request = DistributeRequest(elementIds=[], direction="")

        # Call the method
        result = await mcp_tools_manager.distribute_elements(request)

        # Verify the result indicates failure
        assert result["success"] is False
        assert "error" in result
        assert "Element IDs and direction are required" in result["error"]

    @pytest.mark.asyncio
    async def test_distribute_elements_sync_failure(self, mcp_tools_manager):
        """Test distribute_elements method when sync fails."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to return failure
            mock_http_client.post_json = AsyncMock(return_value=None)

            # Create a request model
            class DistributeRequest(BaseModel):
                elementIds: list[str]
                direction: str

            request = DistributeRequest(
                elementIds=["element-1", "element-2"], direction="horizontal"
            )

            # Call the method
            result = await mcp_tools_manager.distribute_elements(request)

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Failed to distribute elements on canvas" in result["error"]

            # Verify HTTP client was called
            mock_http_client.post_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_distribute_elements_exception(self, mcp_tools_manager):
        """Test distribute_elements method when exception occurs."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to raise an exception
            mock_http_client.post_json = AsyncMock(
                side_effect=Exception("Network error")
            )

            # Create a request model
            class DistributeRequest(BaseModel):
                elementIds: list[str]
                direction: str

            request = DistributeRequest(
                elementIds=["element-1", "element-2"], direction="horizontal"
            )

            # Call the method
            result = await mcp_tools_manager.distribute_elements(request)

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_lock_elements_sync_failure(self, mcp_tools_manager):
        """Test lock_elements method when sync fails."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to return failure
            mock_http_client.post_json = AsyncMock(return_value=None)

            # Call the method
            result = await mcp_tools_manager.lock_elements(["element-1", "element-2"])

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Failed to lock elements on canvas" in result["error"]

            # Verify HTTP client was called
            mock_http_client.post_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_lock_elements_exception(self, mcp_tools_manager):
        """Test lock_elements method when exception occurs."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to raise an exception
            mock_http_client.post_json = AsyncMock(
                side_effect=Exception("Network error")
            )

            # Call the method
            result = await mcp_tools_manager.lock_elements(["element-1", "element-2"])

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_unlock_elements_sync_failure(self, mcp_tools_manager):
        """Test unlock_elements method when sync fails."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to return failure
            mock_http_client.post_json = AsyncMock(return_value=None)

            # Call the method
            result = await mcp_tools_manager.unlock_elements(["element-1", "element-2"])

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Failed to unlock elements on canvas" in result["error"]

            # Verify HTTP client was called
            mock_http_client.post_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_unlock_elements_exception(self, mcp_tools_manager):
        """Test unlock_elements method when exception occurs."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to raise an exception
            mock_http_client.post_json = AsyncMock(
                side_effect=Exception("Network error")
            )

            # Call the method
            result = await mcp_tools_manager.unlock_elements(["element-1", "element-2"])

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_get_resource_invalid_type(self, mcp_tools_manager):
        """Test get_resource method with invalid resource type."""
        # Call the method with invalid type
        result = await mcp_tools_manager.get_resource("invalid_type")

        # Verify the result indicates error
        assert result["success"] is False
        assert "error" in result
        assert "Invalid resource type" in result["error"]

    @pytest.mark.asyncio
    async def test_get_resource_sync_failure(self, mcp_tools_manager):
        """Test get_resource method when sync fails."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to return failure
            mock_http_client.get_json = AsyncMock(return_value=None)

            # Call the method
            result = await mcp_tools_manager.get_resource("scene")

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Failed to retrieve scene resource from canvas" in result["error"]

            # Verify HTTP client was called
            mock_http_client.get_json.assert_called_once_with("/api/scene")

    @pytest.mark.asyncio
    async def test_get_resource_exception(self, mcp_tools_manager):
        """Test get_resource method when exception occurs."""
        with patch("excalidraw_mcp.mcp_tools.http_client") as mock_http_client:
            # Mock HTTP client to raise an exception
            mock_http_client.get_json = AsyncMock(
                side_effect=Exception("Network error")
            )

            # Call the method
            result = await mcp_tools_manager.get_resource("scene")

            # Verify the result indicates failure
            assert result["success"] is False
            assert "error" in result
            assert "Network error" in result["error"]
