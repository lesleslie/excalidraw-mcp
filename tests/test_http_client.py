"""Tests for HTTP client with connection pooling."""

from unittest.mock import Mock, patch

import httpx
import pytest

from excalidraw_mcp.http_client import CanvasHTTPClient, HealthCacheEntry


class TestCanvasHTTPClient:
    """Test the Canvas HTTP client."""

    @pytest.fixture
    async def http_client(self):
        """Create HTTP client for testing."""
        client = CanvasHTTPClient()
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_health_check_success(self, http_client):
        """Test successful health check."""
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = await http_client.check_health()

            assert result is True
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, http_client):
        """Test failed health check."""
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            result = await http_client.check_health()

            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_exception(self, http_client):
        """Test health check with network exception."""
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")

            result = await http_client.check_health()

            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_caching(self, http_client):
        """Test health check result caching."""
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # First call
            result1 = await http_client.check_health()
            assert result1 is True

            # Second call should use cache
            result2 = await http_client.check_health()
            assert result2 is True

            # Should only call the HTTP client once due to caching
            assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_post_json_success(self, http_client):
        """Test successful POST request."""
        test_data = {"type": "rectangle", "x": 100, "y": 200}
        expected_response = {"id": "test-123", "success": True}

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = expected_response
            mock_post.return_value = mock_response

            result = await http_client.post_json("/api/elements", test_data)

            assert result == expected_response
            mock_post.assert_called_once()

            # Check that JSON data was passed correctly
            call_args = mock_post.call_args
            assert call_args[1]["json"] == test_data

    @pytest.mark.asyncio
    async def test_post_json_with_retries(self, http_client):
        """Test POST request with retries on failure."""
        test_data = {"type": "rectangle", "x": 100, "y": 200}

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            # First two calls fail, third succeeds
            mock_responses = [
                Mock(status_code=500),
                Mock(status_code=503),
                Mock(status_code=200, json=lambda: {"success": True}),
            ]
            mock_post.side_effect = mock_responses

            result = await http_client.post_json("/api/elements", test_data, retries=3)

            assert result == {"success": True}
            assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_post_json_timeout(self, http_client):
        """Test POST request timeout handling."""
        test_data = {"type": "rectangle", "x": 100, "y": 200}

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            result = await http_client.post_json("/api/elements", test_data)

            assert result is None

    @pytest.mark.asyncio
    async def test_put_json_success(self, http_client):
        """Test successful PUT request."""
        test_data = {"x": 150, "y": 250}
        expected_response = {"success": True}

        with patch.object(httpx.AsyncClient, "put") as mock_put:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = expected_response
            mock_put.return_value = mock_response

            result = await http_client.put_json("/api/elements/test-123", test_data)

            assert result == expected_response
            mock_put.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_success(self, http_client):
        """Test successful DELETE request."""
        with patch.object(httpx.AsyncClient, "delete") as mock_delete:
            mock_response = Mock()
            mock_response.status_code = 204
            mock_delete.return_value = mock_response

            result = await http_client.delete("/api/elements/test-123")

            assert result is True
            mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_failure(self, http_client):
        """Test failed DELETE request."""
        with patch.object(httpx.AsyncClient, "delete") as mock_delete:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_delete.return_value = mock_response

            result = await http_client.delete("/api/elements/nonexistent")

            assert result is False

    @pytest.mark.asyncio
    async def test_get_json_success(self, http_client):
        """Test successful GET request."""
        expected_response = {"elements": [{"id": "test-123"}]}

        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = expected_response
            mock_get.return_value = mock_response

            result = await http_client.get_json("/api/elements")

            assert result == expected_response
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test HTTP client as context manager."""
        async with CanvasHTTPClient() as client:
            assert client._client is not None

        # Client should be closed after exiting context
        assert client._client is None

    @pytest.mark.asyncio
    async def test_health_failure_count(self, http_client):
        """Test health failure count tracking."""
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")

            # Multiple failed health checks
            await http_client.check_health(force=True)
            await http_client.check_health(force=True)
            await http_client.check_health(force=True)

            assert http_client.health_failure_count == 3
            assert http_client.is_healthy is False


class TestHealthCacheEntry:
    """Test health cache entry data structure."""

    def test_health_cache_entry_creation(self):
        """Test creating a health cache entry."""
        entry = HealthCacheEntry(status=True, timestamp=1234567890.0)

        assert entry.status is True
        assert entry.timestamp == 1234567890.0
        assert entry.failure_count == 0

    def test_health_cache_entry_with_failures(self):
        """Test health cache entry with failure count."""
        entry = HealthCacheEntry(status=False, timestamp=1234567890.0, failure_count=5)

        assert entry.status is False
        assert entry.failure_count == 5
