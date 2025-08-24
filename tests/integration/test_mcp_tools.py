"""Integration tests for MCP tools."""

import pytest
from unittest.mock import AsyncMock, patch
from excalidraw_mcp.mcp_tools import create_element, update_element, delete_element, query_elements


class TestMCPToolsIntegration:
    """Integration tests for MCP tool implementations."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_element_integration(self, mock_http_client, sample_element_data):
        """Test element creation through MCP tool."""
        # Mock successful HTTP response
        mock_http_client.post_json.return_value = {
            "id": "created-element-123",
            "success": True
        }
        
        with patch('excalidraw_mcp.mcp_tools.get_canvas_client', return_value=mock_http_client):
            result = await create_element(sample_element_data)
        
        # Verify client was called with correct data
        mock_http_client.post_json.assert_called_once()
        call_args = mock_http_client.post_json.call_args
        
        # Check endpoint
        assert call_args[0][0] == "/api/elements"
        
        # Check element data was properly formatted
        sent_data = call_args[1]["json"]
        assert sent_data["type"] == "rectangle"
        assert sent_data["x"] == 100.0
        assert sent_data["y"] == 200.0
        assert "id" in sent_data
        assert "createdAt" in sent_data
        
        # Check return value
        assert result["id"] == "created-element-123"
        assert result["success"] is True
    
    @pytest.mark.integration  
    @pytest.mark.asyncio
    async def test_update_element_integration(self, mock_http_client):
        """Test element update through MCP tool."""
        update_data = {
            "id": "test-element-123",
            "x": 150,
            "y": 250,
            "strokeColor": "#ff0000"
        }
        
        mock_http_client.put_json.return_value = {"success": True}
        
        with patch('excalidraw_mcp.mcp_tools.get_canvas_client', return_value=mock_http_client):
            result = await update_element(update_data)
        
        # Verify client was called correctly
        mock_http_client.put_json.assert_called_once()
        call_args = mock_http_client.put_json.call_args
        
        # Check endpoint includes element ID
        assert call_args[0][0] == "/api/elements/test-element-123"
        
        # Check update data
        sent_data = call_args[1]["json"]
        assert sent_data["x"] == 150.0
        assert sent_data["y"] == 250.0
        assert sent_data["strokeColor"] == "#ff0000"
        assert "updatedAt" in sent_data
        
        assert result["success"] is True
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_element_integration(self, mock_http_client):
        """Test element deletion through MCP tool."""
        element_id = "test-element-123"
        
        mock_http_client.delete.return_value = True
        
        with patch('excalidraw_mcp.mcp_tools.get_canvas_client', return_value=mock_http_client):
            result = await delete_element(element_id)
        
        # Verify client was called correctly
        mock_http_client.delete.assert_called_once_with(f"/api/elements/{element_id}")
        
        assert result["success"] is True
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_query_elements_integration(self, mock_http_client):
        """Test element querying through MCP tool."""
        mock_elements = [
            {"id": "1", "type": "rectangle", "x": 100},
            {"id": "2", "type": "ellipse", "x": 200}
        ]
        mock_http_client.get_json.return_value = {"elements": mock_elements}
        
        query_request = {
            "type": "rectangle",
            "filter": {"x": 100}
        }
        
        with patch('excalidraw_mcp.mcp_tools.get_canvas_client', return_value=mock_http_client):
            result = await query_elements(query_request)
        
        # Verify client was called
        mock_http_client.get_json.assert_called_once_with("/api/elements")
        
        # Check result filtering (this would be more complex in real implementation)
        assert "elements" in result
    
    @pytest.mark.integration
    @pytest.mark.asyncio 
    async def test_create_element_validation_error(self, mock_http_client):
        """Test element creation with validation errors."""
        invalid_data = {
            "type": "invalid_type",
            "x": "not_a_number"
        }
        
        with patch('excalidraw_mcp.mcp_tools.get_canvas_client', return_value=mock_http_client):
            with pytest.raises(Exception):  # Should raise validation error
                await create_element(invalid_data)
        
        # HTTP client should not be called due to validation failure
        mock_http_client.post_json.assert_not_called()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_http_client_connection_error(self, mock_http_client):
        """Test handling of HTTP connection errors."""
        # Simulate connection error
        mock_http_client.post_json.side_effect = Exception("Connection failed")
        
        with patch('excalidraw_mcp.mcp_tools.get_canvas_client', return_value=mock_http_client):
            with pytest.raises(Exception, match="Connection failed"):
                await create_element({"type": "rectangle", "x": 100, "y": 200})
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_canvas_server_error_response(self, mock_http_client):
        """Test handling of canvas server error responses."""
        # Simulate server error
        mock_http_client.post_json.return_value = {
            "error": "Server error",
            "success": False
        }
        
        sample_data = {"type": "rectangle", "x": 100, "y": 200}
        
        with patch('excalidraw_mcp.mcp_tools.get_canvas_client', return_value=mock_http_client):
            result = await create_element(sample_data)
        
        # Should return the error response
        assert result["success"] is False
        assert result["error"] == "Server error"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_element_operations(self, mock_http_client):
        """Test concurrent element operations."""
        import asyncio
        
        # Mock different responses for each call
        mock_http_client.post_json.return_value = {"id": "test", "success": True}
        mock_http_client.put_json.return_value = {"success": True}
        mock_http_client.delete.return_value = True
        
        element_data = {"type": "rectangle", "x": 100, "y": 200}
        update_data = {"id": "test-123", "x": 150}
        
        with patch('excalidraw_mcp.mcp_tools.get_canvas_client', return_value=mock_http_client):
            # Run operations concurrently
            results = await asyncio.gather(
                create_element(element_data),
                update_element(update_data),
                delete_element("delete-123"),
                return_exceptions=True
            )
        
        # All operations should succeed
        assert len(results) == 3
        assert all(not isinstance(result, Exception) for result in results)
        assert results[0]["success"] is True  # create
        assert results[1]["success"] is True  # update  
        assert results[2]["success"] is True  # delete
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_bulk_element_creation(self, mock_http_client, batch_element_data, performance_monitor):
        """Test bulk element creation performance."""
        # Generate 100 elements
        elements = batch_element_data(100)
        
        mock_http_client.post_json.return_value = {"id": "test", "success": True}
        
        with patch('excalidraw_mcp.mcp_tools.get_canvas_client', return_value=mock_http_client):
            # Create all elements
            tasks = []
            for element_data in elements:
                tasks.append(create_element(element_data))
            
            results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 100
        assert all(result["success"] for result in results)
        
        # HTTP client should have been called 100 times
        assert mock_http_client.post_json.call_count == 100
        
        # Performance monitoring handled by fixture
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_element_lifecycle(self, mock_http_client, sample_element_data):
        """Test complete element lifecycle: create -> update -> delete."""
        element_id = "lifecycle-test-123"
        
        # Mock responses for each operation
        mock_http_client.post_json.return_value = {"id": element_id, "success": True}
        mock_http_client.put_json.return_value = {"success": True}
        mock_http_client.delete.return_value = True
        
        with patch('excalidraw_mcp.mcp_tools.get_canvas_client', return_value=mock_http_client):
            # 1. Create element
            create_result = await create_element(sample_element_data)
            assert create_result["success"] is True
            
            # 2. Update element
            update_data = {"id": element_id, "x": 300, "y": 400}
            update_result = await update_element(update_data)
            assert update_result["success"] is True
            
            # 3. Delete element
            delete_result = await delete_element(element_id)
            assert delete_result["success"] is True
        
        # Verify all operations were called
        mock_http_client.post_json.assert_called_once()
        mock_http_client.put_json.assert_called_once()
        mock_http_client.delete.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_client_context_manager(self, mock_http_client, sample_element_data):
        """Test that HTTP client context manager is used correctly."""
        mock_http_client.post_json.return_value = {"id": "test", "success": True}
        
        with patch('excalidraw_mcp.mcp_tools.get_canvas_client', return_value=mock_http_client):
            await create_element(sample_element_data)
        
        # Verify context manager methods were called
        mock_http_client.__aenter__.assert_called_once()
        mock_http_client.__aexit__.assert_called_once()