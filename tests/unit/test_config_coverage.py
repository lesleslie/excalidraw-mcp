"""Additional tests to cover missing lines in config.py"""

import os
from unittest.mock import patch

import pytest

from excalidraw_mcp.config import Config


def test_config_validation_token_expiration_positive():
    """Test validation passes for positive token expiration."""
    with patch.dict(
        os.environ, {"AUTH_ENABLED": "true", "JWT_SECRET": "test-secret"}, clear=False
    ):
        config = Config()
        config.security.token_expiration_hours = 1  # Positive value
        # Should not raise exception
        config._validate()


def test_config_validation_token_expiration_zero():
    """Test validation fails for zero token expiration."""
    with patch.dict(
        os.environ, {"AUTH_ENABLED": "true", "JWT_SECRET": "test-secret"}, clear=False
    ):
        with pytest.raises(ValueError) as exc_info:
            config = Config()
            config.security.token_expiration_hours = 0  # Zero value
            config._validate()

        assert "Token expiration must be positive" in str(exc_info.value)


def test_config_validation_token_expiration_negative():
    """Test validation fails for negative token expiration."""
    with patch.dict(
        os.environ, {"AUTH_ENABLED": "true", "JWT_SECRET": "test-secret"}, clear=False
    ):
        with pytest.raises(ValueError) as exc_info:
            config = Config()
            config.security.token_expiration_hours = -1  # Negative value
            config._validate()

        assert "Token expiration must be positive" in str(exc_info.value)


def test_config_validation_health_check_timeout_positive():
    """Test validation passes for positive health check timeout."""
    config = Config()
    config.server.health_check_timeout_seconds = 1.0  # Positive value
    # Should not raise exception
    config._validate()


def test_config_validation_health_check_timeout_zero():
    """Test validation fails for zero health check timeout."""
    with pytest.raises(ValueError) as exc_info:
        config = Config()
        config.server.health_check_timeout_seconds = 0.0  # Zero value
        config._validate()

    assert "Health check timeout must be positive" in str(exc_info.value)


def test_config_validation_health_check_timeout_negative():
    """Test validation fails for negative health check timeout."""
    with pytest.raises(ValueError) as exc_info:
        config = Config()
        config.server.health_check_timeout_seconds = -1.0  # Negative value
        config._validate()

    assert "Health check timeout must be positive" in str(exc_info.value)


def test_config_validation_websocket_batch_size_positive():
    """Test validation passes for positive websocket batch size."""
    config = Config()
    config.performance.websocket_batch_size = 1  # Positive value
    # Should not raise exception
    config._validate()


def test_config_validation_websocket_batch_size_zero():
    """Test validation fails for zero websocket batch size."""
    with pytest.raises(ValueError) as exc_info:
        config = Config()
        config.performance.websocket_batch_size = 0  # Zero value
        config._validate()

    assert "WebSocket batch size must be positive" in str(exc_info.value)


def test_config_validation_websocket_batch_size_negative():
    """Test validation fails for negative websocket batch size."""
    with pytest.raises(ValueError) as exc_info:
        config = Config()
        config.performance.websocket_batch_size = -1  # Negative value
        config._validate()

    assert "WebSocket batch size must be positive" in str(exc_info.value)
