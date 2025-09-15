"""Additional tests to cover missing lines in http_client.py"""

from unittest.mock import Mock, patch

import httpx
import pytest
import pytest_asyncio

from excalidraw_mcp.http_client import CanvasHTTPClient


class TestHttpClientCoverage:
    """Additional tests to cover missing lines in http_client.py"""

    @pytest_asyncio.fixture
    async def http_client(self):
        """Create HTTP client for testing."""
        client = CanvasHTTPClient()
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_health_check_force_bypasses_cache(self, http_client):
        """Test that force=True bypasses health check caching."""
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # First call
            result1 = await http_client.check_health()
            assert result1 is True

            # Second call with force=True should call HTTP client again
            result2 = await http_client.check_health(force=True)
            assert result2 is True

            # Should call the HTTP client twice due to force=True
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_health_check_double_check_after_lock(self, http_client):
        """Test double-check after acquiring lock in health check."""
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # First call to populate cache
            await http_client.check_health()

            # Patch the lock to simulate the double-check scenario
            with patch.object(http_client, "_lock"):
                # Second call with force=True should still work
                result = await http_client.check_health(force=True)
                assert result is True

    @pytest.mark.asyncio
    async def test_post_json_retry_logic(self, http_client):
        """Test POST request retry logic with various status codes."""
        test_data = {"type": "rectangle", "x": 100, "y": 200}

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            # Test with 500 status code that should trigger retry
            mock_response_500 = Mock()
            mock_response_500.status_code = 500
            mock_response_500.text = "Internal Server Error"

            # Test with 201 status code that should succeed
            mock_response_201 = Mock()
            mock_response_201.status_code = 201
            mock_response_201.json.return_value = {"success": True}

            mock_post.side_effect = [mock_response_500, mock_response_201]

            result = await http_client.post_json("/api/elements", test_data, retries=2)

            assert result == {"success": True}
            assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_post_json_all_retries_fail(self, http_client):
        """Test POST request where all retries fail."""
        test_data = {"type": "rectangle", "x": 100, "y": 200}

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            # All calls fail with 500 status code
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response

            result = await http_client.post_json("/api/elements", test_data, retries=2)

            assert result is None
            assert mock_post.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_post_json_non_success_status_codes_still_retry(self, http_client):
        """Test POST request with non-success status codes that still trigger retries."""
        test_data = {"type": "rectangle", "x": 100, "y": 200}

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            mock_response_400 = Mock()
            mock_response_400.status_code = 400  # Bad request
            mock_response_400.text = "Bad Request"

            mock_response_200 = Mock()
            mock_response_200.status_code = 200
            mock_response_200.json.return_value = {"success": True}

            mock_post.side_effect = [mock_response_400, mock_response_400, mock_response_200]

            result = await http_client.post_json("/api/elements", test_data, retries=2)

            assert result == {"success": True}
            assert mock_post.call_count == 3  # All retries used

    @pytest.mark.asyncio
    async def test_put_json_failure(self, http_client):
        """Test PUT request with failure response."""
        test_data = {"x": 150, "y": 250}

        with patch.object(httpx.AsyncClient, "put") as mock_put:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_put.return_value = mock_response

            result = await http_client.put_json("/api/elements/test-123", test_data)

            assert result is None
            assert mock_put.call_count == 1

    @pytest.mark.asyncio
    async def test_put_json_exception(self, http_client):
        """Test PUT request with exception."""
        test_data = {"x": 150, "y": 250}

        with patch.object(httpx.AsyncClient, "put") as mock_put:
            mock_put.side_effect = Exception("Network error")

            result = await http_client.put_json("/api/elements/test-123", test_data)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_json_failure(self, http_client):
        """Test GET request with failure response."""
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_get.return_value = mock_response

            result = await http_client.get_json("/api/elements")

            assert result is None
            assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_get_json_exception(self, http_client):
        """Test GET request with exception."""
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = await http_client.get_json("/api/elements")

            assert result is None

    @pytest.mark.asyncio
    async def test_delete_exception(self, http_client):
        """Test DELETE request with exception."""
        with patch.object(httpx.AsyncClient, "delete") as mock_delete:
            mock_delete.side_effect = Exception("Network error")

            result = await http_client.delete("/api/elements/test-123")

            assert result is False