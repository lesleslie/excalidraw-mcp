"""Tests for configuration management."""

import os
import pytest
from unittest.mock import patch

from excalidraw_mcp.config import Config, SecurityConfig, ServerConfig


class TestConfig:
    """Test configuration loading and validation."""
    
    def test_default_config_creation(self):
        """Test that default configuration is created correctly."""
        config = Config()
        
        assert config.security.auth_enabled is True
        assert config.server.express_url == "http://localhost:3031"
        assert config.performance.max_elements_per_canvas == 10000
        assert config.logging.level == "INFO"
    
    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            "AUTH_ENABLED": "false",
            "EXPRESS_SERVER_URL": "http://localhost:3032",
            "JWT_SECRET": "test-secret",
            "MAX_ELEMENTS": "5000",
            "LOG_LEVEL": "DEBUG"
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = Config()
            
            assert config.security.auth_enabled is False
            assert config.server.express_url == "http://localhost:3032"
            assert config.security.jwt_secret == "test-secret"
            assert config.performance.max_elements_per_canvas == 5000
            assert config.logging.level == "DEBUG"
    
    def test_allowed_origins_parsing(self):
        """Test parsing of allowed origins from environment."""
        env_vars = {
            "ALLOWED_ORIGINS": "http://localhost:3000,https://example.com,http://127.0.0.1:8080"
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = Config()
            
            expected_origins = [
                "http://localhost:3000",
                "https://example.com", 
                "http://127.0.0.1:8080"
            ]
            assert config.security.allowed_origins == expected_origins
    
    def test_config_validation_success(self):
        """Test successful configuration validation."""
        # Should not raise any exceptions
        config = Config()
        config.security.jwt_secret = "valid-secret"
        config._validate()
    
    def test_config_validation_missing_jwt_secret(self):
        """Test validation failure when JWT secret is missing."""
        with patch.dict(os.environ, {"AUTH_ENABLED": "true", "JWT_SECRET": ""}, clear=False):
            with pytest.raises(ValueError) as exc_info:
                Config()
            
            assert "JWT_SECRET is required" in str(exc_info.value)
    
    def test_config_validation_invalid_port(self):
        """Test validation failure for invalid port."""
        with patch.dict(os.environ, {"EXPRESS_SERVER_URL": "http://localhost:70000"}, clear=False):
            with pytest.raises(ValueError) as exc_info:
                Config()
            
            assert "port must be between 1 and 65535" in str(exc_info.value)
    
    def test_config_validation_negative_values(self):
        """Test validation failure for negative values."""
        with patch.dict(os.environ, {"MAX_ELEMENTS": "-100"}, clear=False):
            with pytest.raises(ValueError) as exc_info:
                Config()
            
            assert "Max elements per canvas must be positive" in str(exc_info.value)
    
    def test_development_mode_detection(self):
        """Test development mode detection."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=False):
            config = Config()
            assert config.is_development is True
            assert config.is_production is False
    
    def test_production_mode_detection(self):
        """Test production mode detection."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False):
            config = Config()
            assert config.is_development is False
            assert config.is_production is True


class TestSecurityConfig:
    """Test security configuration."""
    
    def test_security_config_defaults(self):
        """Test security configuration defaults."""
        config = SecurityConfig()
        
        assert config.auth_enabled is True
        assert config.jwt_algorithm == "HS256"
        assert config.token_expiration_hours == 24
        assert "http://localhost:3031" in config.allowed_origins
        assert config.cors_credentials is True
        assert "Authorization" in config.cors_headers
    
    def test_security_config_post_init(self):
        """Test security configuration post-initialization."""
        config = SecurityConfig()
        
        # Check that default values are set
        assert config.allowed_origins is not None
        assert len(config.allowed_origins) > 0
        assert config.cors_methods is not None
        assert "GET" in config.cors_methods
        assert "POST" in config.cors_methods


class TestServerConfig:
    """Test server configuration."""
    
    def test_server_config_defaults(self):
        """Test server configuration defaults."""
        config = ServerConfig()
        
        assert config.express_url == "http://localhost:3031"
        assert config.express_host == "localhost"
        assert config.express_port == 3031
        assert config.health_check_timeout_seconds == 5.0
        assert config.canvas_auto_start is True
    
    def test_server_config_url_parsing(self):
        """Test URL parsing in server configuration."""
        config = ServerConfig()
        config.express_url = "http://example.com:8080"
        config.__post_init__()
        
        assert config.express_host == "example.com"
        assert config.express_port == 8080
    
    def test_server_config_custom_port(self):
        """Test custom port configuration."""
        config = ServerConfig()
        config.express_url = "https://api.example.com:443"
        config.__post_init__()
        
        assert config.express_host == "api.example.com"
        assert config.express_port == 443