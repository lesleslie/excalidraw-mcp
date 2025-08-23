"""Pytest configuration and shared fixtures."""

import asyncio
import os
import pytest
import tempfile
from unittest.mock import Mock, AsyncMock
from typing import AsyncGenerator, Generator

import httpx
from excalidraw_mcp.config import Config
from excalidraw_mcp.http_client import CanvasHTTPClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Create a test configuration."""
    # Create temporary directories for test logs
    temp_dir = tempfile.mkdtemp()
    
    config = Config()
    
    # Override with test settings
    config.server.express_url = "http://localhost:3032"  # Different port for tests
    config.server.canvas_auto_start = False  # Don't auto-start in tests
    config.security.auth_enabled = False  # Disable auth for tests
    config.logging.file_path = os.path.join(temp_dir, "test.log")
    config.logging.audit_file_path = os.path.join(temp_dir, "audit.log")
    config.performance.max_elements_per_canvas = 100  # Lower limit for tests
    
    return config


@pytest.fixture
async def mock_http_client():
    """Create a mock HTTP client for testing."""
    client = Mock(spec=CanvasHTTPClient)
    
    # Mock async methods
    client.check_health = AsyncMock(return_value=True)
    client.post_json = AsyncMock(return_value={"success": True})
    client.put_json = AsyncMock(return_value={"success": True})
    client.delete = AsyncMock(return_value=True)
    client.get_json = AsyncMock(return_value={"elements": []})
    client.close = AsyncMock()
    
    # Mock context manager
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    
    return client


@pytest.fixture
def sample_element_data():
    """Sample element data for testing."""
    return {
        "type": "rectangle",
        "x": 100,
        "y": 200,
        "width": 150,
        "height": 100,
        "strokeColor": "#000000",
        "backgroundColor": "#ffffff",
        "strokeWidth": 2,
        "opacity": 100,
        "roughness": 1,
    }


@pytest.fixture
def sample_server_element():
    """Sample server element for testing."""
    return {
        "id": "test-element-123",
        "type": "rectangle",
        "x": 100,
        "y": 200,
        "width": 150,
        "height": 100,
        "strokeColor": "#000000",
        "backgroundColor": "#ffffff",
        "strokeWidth": 2,
        "opacity": 100,
        "roughness": 1,
        "version": 1,
        "createdAt": "2025-01-01T00:00:00.000Z",
        "updatedAt": "2025-01-01T00:00:00.000Z",
        "locked": False,
    }


@pytest.fixture
async def mock_canvas_server():
    """Mock canvas server responses."""
    responses = {
        "health": {"status": "ok"},
        "elements": {"elements": []},
        "create": {"id": "new-element-123", "success": True},
        "update": {"success": True},
        "delete": {"success": True},
    }
    
    async def mock_request(method: str, url: str, **kwargs):
        # Simulate different responses based on URL
        if url.endswith("/health"):
            return httpx.Response(200, json=responses["health"])
        elif url.endswith("/api/elements") and method == "GET":
            return httpx.Response(200, json=responses["elements"])
        elif url.endswith("/api/elements") and method == "POST":
            return httpx.Response(201, json=responses["create"])
        elif "/api/elements/" in url and method == "PUT":
            return httpx.Response(200, json=responses["update"])
        elif "/api/elements/" in url and method == "DELETE":
            return httpx.Response(204, json=responses["delete"])
        else:
            return httpx.Response(404, json={"error": "Not found"})
    
    return mock_request


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for process management tests."""
    mock_process = Mock()
    mock_process.pid = 12345
    mock_process.returncode = None
    mock_process.poll.return_value = None
    
    return mock_process


@pytest.fixture
def environment_variables():
    """Set up test environment variables."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    test_env = {
        "ENVIRONMENT": "test",
        "EXPRESS_SERVER_URL": "http://localhost:3032",
        "CANVAS_AUTO_START": "false",
        "AUTH_ENABLED": "false",
        "JWT_SECRET": "test-secret-key",
        "LOG_LEVEL": "DEBUG",
    }
    
    os.environ.update(test_env)
    
    yield test_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
async def async_client():
    """Create an async HTTP client for integration tests."""
    async with httpx.AsyncClient() as client:
        yield client


# Pytest markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (deselect with '-m \"not unit\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "websocket: marks tests that require WebSocket functionality"
    )


# Performance testing fixtures
@pytest.fixture
def performance_monitor():
    """Monitor performance during tests."""
    import time
    import psutil
    
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss
    
    yield {
        'start_time': start_time,
        'start_memory': start_memory
    }
    
    end_time = time.time()
    end_memory = psutil.Process().memory_info().rss
    
    duration = end_time - start_time
    memory_delta = end_memory - start_memory
    
    # Log performance metrics for slow tests
    if duration > 1.0:  # More than 1 second
        print(f"\nSlow test detected: {duration:.2f}s, Memory delta: {memory_delta / 1024 / 1024:.2f}MB")


@pytest.fixture
def element_factory():
    """Factory for creating test elements."""
    from excalidraw_mcp.element_factory import ElementFactory
    
    factory = ElementFactory()
    
    def create_test_element(element_type="rectangle", **kwargs):
        base_data = {
            "type": element_type,
            "x": kwargs.get("x", 100),
            "y": kwargs.get("y", 200),
            "width": kwargs.get("width", 150),
            "height": kwargs.get("height", 100),
            "strokeColor": kwargs.get("strokeColor", "#000000"),
            "backgroundColor": kwargs.get("backgroundColor", "#ffffff"),
        }
        base_data.update(kwargs)
        return factory.create_element(base_data)
    
    return create_test_element


@pytest.fixture
async def integration_test_server():
    """Set up a real canvas server for integration tests."""
    import subprocess
    import time
    import httpx
    
    # Start canvas server in test mode
    process = subprocess.Popen(
        ["npm", "run", "canvas"],
        env={**os.environ, "PORT": "3033", "NODE_ENV": "test"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to be ready
    client = httpx.AsyncClient()
    max_retries = 30
    for _ in range(max_retries):
        try:
            response = await client.get("http://localhost:3033/health")
            if response.status_code == 200:
                break
        except:
            pass
        time.sleep(0.5)
    else:
        process.terminate()
        raise RuntimeError("Integration test server failed to start")
    
    yield "http://localhost:3033"
    
    # Cleanup
    await client.aclose()
    process.terminate()
    process.wait(timeout=10)


@pytest.fixture
def websocket_mock():
    """Mock WebSocket for testing real-time features."""
    from unittest.mock import Mock, AsyncMock
    
    ws_mock = Mock()
    ws_mock.send = AsyncMock()
    ws_mock.recv = AsyncMock()
    ws_mock.close = AsyncMock()
    ws_mock.closed = False
    
    # Simulate message queue
    ws_mock._message_queue = []
    
    async def mock_recv():
        if ws_mock._message_queue:
            return ws_mock._message_queue.pop(0)
        else:
            # Simulate waiting
            await asyncio.sleep(0.1)
            return '{"type": "heartbeat"}'
    
    ws_mock.recv = mock_recv
    
    def add_message(message):
        ws_mock._message_queue.append(message)
    
    ws_mock.add_message = add_message
    
    return ws_mock


@pytest.fixture
def batch_element_data():
    """Generate batch test data for multiple elements."""
    def generate_batch(count=5, element_type="rectangle"):
        elements = []
        for i in range(count):
            elements.append({
                "type": element_type,
                "x": 100 + i * 50,
                "y": 200 + i * 30,
                "width": 100,
                "height": 80,
                "strokeColor": f"#00{i:02d}000",
                "backgroundColor": "#ffffff",
            })
        return elements
    
    return generate_batch


@pytest.fixture
def security_test_data():
    """Generate potentially malicious test data for security tests."""
    return {
        "xss_text": "<script>alert('xss')</script>",
        "sql_injection": "'; DROP TABLE elements; --",
        "oversized_data": "A" * 1000000,  # 1MB string
        "invalid_coords": {"x": float('inf'), "y": float('nan')},
        "negative_dimensions": {"width": -100, "height": -50},
        "invalid_colors": ["javascript:alert(1)", "#GGGGGG", "rgb(300,300,300)"],
        "malformed_json": '{"incomplete": json data',
        "unicode_attacks": "𝕏𝕏𝕏" * 1000,
    }


@pytest.fixture
def delta_compression_test_data():
    """Test data for delta compression features."""
    old_element = {
        "id": "test-123",
        "type": "rectangle",
        "x": 100,
        "y": 200,
        "width": 150,
        "height": 100,
        "strokeColor": "#000000",
        "version": 1,
        "updatedAt": "2025-01-01T00:00:00.000Z"
    }
    
    new_element = {
        **old_element,
        "x": 120,  # Small change
        "strokeColor": "#ff0000",  # Color change
        "version": 2,
        "updatedAt": "2025-01-01T00:01:00.000Z"
    }
    
    return {"old": old_element, "new": new_element}


@pytest.fixture
async def rate_limiter_mock():
    """Mock rate limiter for testing rate limiting functionality."""
    from collections import defaultdict, deque
    import time
    
    class MockRateLimiter:
        def __init__(self, max_requests=100, window_minutes=15):
            self.max_requests = max_requests
            self.window_seconds = window_minutes * 60
            self.requests = defaultdict(deque)
        
        async def is_allowed(self, identifier: str) -> bool:
            now = time.time()
            user_requests = self.requests[identifier]
            
            # Remove old requests outside the window
            while user_requests and user_requests[0] < now - self.window_seconds:
                user_requests.popleft()
            
            # Check if under limit
            if len(user_requests) < self.max_requests:
                user_requests.append(now)
                return True
            
            return False
        
        def reset(self, identifier: str = None):
            if identifier:
                self.requests[identifier].clear()
            else:
                self.requests.clear()
    
    return MockRateLimiter()


# Auto-use fixtures for common setup
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically set up test environment for all tests."""
    # Ensure we're in test mode
    os.environ["ENVIRONMENT"] = "test"
    
    yield
    
    # Cleanup after test
    # Remove any temporary files, etc.
    pass


# Custom pytest collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file paths."""
    for item in items:
        # Add markers based on test file location
        if "unit" in item.fspath.dirname:
            item.add_marker(pytest.mark.unit)
        elif "integration" in item.fspath.dirname:
            item.add_marker(pytest.mark.integration)
        elif "e2e" in item.fspath.dirname:
            item.add_marker(pytest.mark.e2e)
        elif "performance" in item.fspath.dirname:
            item.add_marker(pytest.mark.performance)
        elif "security" in item.fspath.dirname:
            item.add_marker(pytest.mark.security)
        
        # Add slow marker for tests taking more than expected time
        if hasattr(item, 'function') and getattr(item.function, '__name__', '').startswith('test_slow_'):
            item.add_marker(pytest.mark.slow)