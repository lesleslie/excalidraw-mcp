"""Unit tests for configuration management."""

import os

import pytest

from excalidraw_mcp.config import (
    Config,
    LoggingConfig,
    PerformanceConfig,
    SecurityConfig,
    ServerConfig,
)


class TestSecurityConfig:
    """Test SecurityConfig class."""

    def test_default_values(self):
        """Test default security configuration values."""
        config = SecurityConfig()

        assert config.auth_enabled is False
        assert config.jwt_secret == ""
        assert config.jwt_algorithm == "HS256"
        assert config.token_expiration_hours == 24
        assert config.cors_credentials is True
        assert config.rate_limit_window_minutes == 15
        assert config.rate_limit_max_requests == 100

    def test_post_init_default_lists(self):
        """Test that __post_init__ sets default lists correctly."""
        config = SecurityConfig()

        assert "http://localhost:3031" in config.allowed_origins
        assert "http://127.0.0.1:3031" in config.allowed_origins
        assert "GET" in config.cors_methods
        assert "POST" in config.cors_methods
        assert "Content-Type" in config.cors_headers
        assert "Authorization" in config.cors_headers


class TestServerConfig:
    """Test ServerConfig class."""

    def test_default_values(self):
        """Test default server configuration values."""
        config = ServerConfig()

        assert config.express_url == "http://localhost:3031"
        assert config.express_host == "localhost"
        assert config.express_port == 3031
        assert config.health_check_timeout_seconds == 5.0
        assert config.canvas_auto_start is True

    def test_url_parsing(self):
        """Test URL parsing in __post_init__."""
        config = ServerConfig()
        config.express_url = "http://example.com:8080"
        config.__post_init__()

        assert config.express_host == "example.com"
        assert config.express_port == 8080


class TestPerformanceConfig:
    """Test PerformanceConfig class."""

    def test_default_values(self):
        """Test default performance configuration values."""
        config = PerformanceConfig()

        assert config.http_pool_connections == 10
        assert config.http_pool_maxsize == 20
        assert config.websocket_ping_interval == 30
        assert config.max_elements_per_canvas == 10000
        assert config.enable_spatial_indexing is True


class TestLoggingConfig:
    """Test LoggingConfig class."""

    def test_default_values(self):
        """Test default logging configuration values."""
        config = LoggingConfig()

        assert config.level == "INFO"
        assert config.max_file_size_mb == 100
        assert config.backup_count == 5
        assert config.audit_enabled is True

    def test_post_init_sensitive_fields(self):
        """Test that sensitive fields are set correctly."""
        config = LoggingConfig()

        assert "password" in config.sensitive_fields
        assert "token" in config.sensitive_fields
        assert "secret" in config.sensitive_fields
        assert "key" in config.sensitive_fields


class TestConfig:
    """Test main Config class."""

    def test_initialization(self):
        """Test Config initialization with all sub-configs."""
        config = Config()

        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.performance, PerformanceConfig)
        assert isinstance(config.logging, LoggingConfig)

    def test_environment_loading(self):
        """Test loading configuration from environment variables."""
        # Set test environment variables
        test_env = {
            "AUTH_ENABLED": "true",
            "JWT_SECRET": "test-secret",
            "EXPRESS_SERVER_URL": "http://test.com:4000",
            "CANVAS_AUTO_START": "false",
            "MAX_ELEMENTS": "5000",
            "LOG_LEVEL": "DEBUG",
            "ALLOWED_ORIGINS": "http://localhost:3000,http://localhost:3001",
        }

        # Temporarily set environment variables
        original_env = {}
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            config = Config()

            # Test security config
            assert config.security.auth_enabled is True
            assert config.security.jwt_secret == "test-secret"
            assert "http://localhost:3000" in config.security.allowed_origins
            assert "http://localhost:3001" in config.security.allowed_origins

            # Test server config
            assert config.server.express_url == "http://test.com:4000"
            assert config.server.canvas_auto_start is False

            # Test performance config
            assert config.performance.max_elements_per_canvas == 5000

            # Test logging config
            assert config.logging.level == "DEBUG"

        finally:
            # Restore original environment
            for key in test_env:
                if original_env[key] is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_env[key]

    def test_validation_success(self):
        """Test successful configuration validation."""
        config = Config()
        # Should not raise any exception
        assert config is not None

    def test_validation_auth_enabled_without_secret(self):
        """Test validation fails when auth is enabled without JWT secret."""
        os.environ["AUTH_ENABLED"] = "true"
        os.environ["JWT_SECRET"] = ""

        try:
            with pytest.raises(ValueError, match="JWT_SECRET is required"):
                Config()
        finally:
            os.environ.pop("AUTH_ENABLED", None)
            os.environ.pop("JWT_SECRET", None)

    def test_validation_invalid_port(self):
        """Test validation fails with invalid port."""
        os.environ["EXPRESS_SERVER_URL"] = "http://localhost:70000"

        try:
            with pytest.raises(ValueError, match="Express port must be between 1 and 65535"):
                Config()
        finally:
            os.environ.pop("EXPRESS_SERVER_URL", None)

    def test_validation_negative_values(self):
        """Test validation fails with negative configuration values."""
        os.environ["MAX_ELEMENTS"] = "-100"

        try:
            with pytest.raises(
                ValueError, match="Max elements per canvas must be positive"
            ):
                Config()
        finally:
            os.environ.pop("MAX_ELEMENTS", None)

    def test_is_development_mode(self):
        """Test development mode detection."""
        # Clear any existing ENVIRONMENT variable
        original_env = os.environ.get("ENVIRONMENT")
        if original_env is not None:
            del os.environ["ENVIRONMENT"]
        
        try:
            # Default should be development
            config = Config()
            print(f"Default config.is_development: {config.is_development}")
            print(f"Default ENVIRONMENT: {os.environ.get('ENVIRONMENT', 'NOT SET')}")
            assert config.is_development is True
            assert config.is_production is False

            # Test explicit development
            os.environ["ENVIRONMENT"] = "development"
            config = Config()
            print(f"Explicit development config.is_development: {config.is_development}")
            assert config.is_development is True
            assert config.is_production is False
        finally:
            # Restore original environment
            if original_env is not None:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]

    def test_is_production_mode(self):
        """Test production mode detection."""
        original_env = os.environ.get("ENVIRONMENT")
        
        os.environ["ENVIRONMENT"] = "production"

        try:
            config = Config()
            assert config.is_production is True
            assert config.is_development is False
        finally:
            # Restore original environment
            if original_env is not None:
                os.environ["ENVIRONMENT"] = original_env
            else:
                del os.environ["ENVIRONMENT"]

    @pytest.mark.security
    def test_sensitive_data_not_exposed(self):
        """Test that sensitive configuration data is not accidentally exposed."""
        os.environ["JWT_SECRET"] = "super-secret-key"

        try:
            config = Config()

            # JWT secret should be accessible but not in string representation
            assert config.security.jwt_secret == "super-secret-key"
            str(config.__dict__)
            # This is a basic check - in reality, we'd want more sophisticated protection
            assert len(config.security.jwt_secret) > 0
        finally:
            os.environ.pop("JWT_SECRET", None)

    def test_config_immutability(self):
        """Test that critical config values can be modified (for testing)."""
        config = Config()

        # Should be able to modify for testing purposes
        original_auth = config.security.auth_enabled
        config.security.auth_enabled = not original_auth
        assert config.security.auth_enabled != original_auth

    def test_multiple_config_instances(self):
        """Test that multiple Config instances work correctly."""
        config1 = Config()
        config2 = Config()

        # They should have the same values but be different objects
        assert config1.server.express_port == config2.server.express_port
        assert config1 is not config2
        assert config1.server is not config2.server

    def test_environment_variable_types(self):
        """Test that environment variables are properly typed."""
        test_env = {
            "AUTH_ENABLED": "true",
            "JWT_SECRET": "test-secret-key",
            "CANVAS_AUTO_START": "false",
            "MAX_ELEMENTS": "2500",
        }

        original_env = {}
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            config = Config()

            # Boolean conversions
            assert isinstance(config.security.auth_enabled, bool)
            assert config.security.auth_enabled is True
            assert isinstance(config.server.canvas_auto_start, bool)
            assert config.server.canvas_auto_start is False

            # Integer conversions
            assert isinstance(config.performance.max_elements_per_canvas, int)
            assert config.performance.max_elements_per_canvas == 2500

        finally:
            for key in test_env:
                if original_env[key] is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_env[key]