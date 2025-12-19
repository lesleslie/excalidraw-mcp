"""Configuration management for Excalidraw MCP server."""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import tomli

    _tomli: Any = tomli
except ImportError:
    _tomli = None

# Import mcp-common security utilities for JWT validation (Phase 3 Security Hardening)
try:
    from mcp_common.security import APIKeyValidator

    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False


@dataclass
class SecurityConfig:
    """Security-related configuration."""

    # Authentication
    auth_enabled: bool = False  # Disabled by default for development
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    token_expiration_hours: int = 24

    # CORS
    allowed_origins: list[str] = field(default_factory=list)
    cors_credentials: bool = True
    cors_methods: list[str] = field(default_factory=list)
    cors_headers: list[str] = field(default_factory=list)

    # Rate limiting
    rate_limit_window_minutes: int = 15
    rate_limit_max_requests: int = 100

    def __post_init__(self) -> None:
        pass

    def get_masked_jwt_secret(self) -> str:
        """Get masked JWT secret for safe logging (Phase 3 Security Hardening).

        Returns:
            Masked secret string (e.g., "...xyz1") for safe display in logs
        """
        if not self.jwt_secret:
            return "***"

        if SECURITY_AVAILABLE:
            return APIKeyValidator.mask_key(self.jwt_secret, visible_chars=4)

        # Fallback masking without security module
        if len(self.jwt_secret) <= 4:
            return "***"
        return f"...{self.jwt_secret[-4:]}"

    def validate_jwt_secret_at_startup(self) -> None:
        """Validate JWT secret at server startup (Phase 3 Security Hardening).

        Raises:
            SystemExit: If JWT secret is invalid when auth is enabled
        """
        # Skip validation if auth is disabled
        if not self.auth_enabled:
            return

        # Check if JWT_SECRET is set when auth is enabled
        if not self.jwt_secret or not self.jwt_secret.strip():
            print("\n❌ JWT Secret Validation Failed", file=sys.stderr)
            print("   AUTH_ENABLED is true but JWT_SECRET is not set", file=sys.stderr)
            print(
                "   Set JWT_SECRET environment variable for authentication",
                file=sys.stderr,
            )
            sys.exit(1)

        if SECURITY_AVAILABLE:
            # Use generic validator with minimum 32 characters for JWT secrets
            validator = APIKeyValidator(min_length=32)
            try:
                validator.validate(self.jwt_secret, raise_on_invalid=True)
                masked_secret = self.get_masked_jwt_secret()
                print(f"✅ JWT Secret validated: {masked_secret}", file=sys.stderr)
            except ValueError:
                print("\n⚠️  JWT Secret Warning", file=sys.stderr)
                print(
                    f"   JWT secret appears weak ({len(self.jwt_secret)} characters)",
                    file=sys.stderr,
                )
                print(
                    "   Minimum 32 characters recommended for security", file=sys.stderr
                )
                # Warn but allow for backwards compatibility
        else:
            # Basic validation without security module
            if len(self.jwt_secret) < 16:
                print("\n⚠️  JWT Secret Warning", file=sys.stderr)
                print(
                    f"   JWT secret appears very weak ({len(self.jwt_secret)} characters)",
                    file=sys.stderr,
                )
                print(
                    "   Minimum 32 characters recommended for security", file=sys.stderr
                )


@dataclass
class ServerConfig:
    """Server configuration settings."""

    # Express server
    express_url: str = "http://localhost:3031"
    express_host: str = "localhost"
    express_port: int = 3031

    # Health checks
    health_check_timeout_seconds: float = 5.0
    health_check_interval_seconds: int = 30
    health_check_max_failures: int = 3

    # Sync operations
    sync_operation_timeout_seconds: float = 10.0
    sync_retry_attempts: int = 3
    sync_retry_delay_seconds: float = 1.0
    sync_retry_max_delay_seconds: float = 30.0
    sync_retry_exponential_base: float = 2.0
    sync_retry_jitter: bool = True

    # Process management
    canvas_auto_start: bool = True
    startup_timeout_seconds: int = 30
    startup_retry_delay_seconds: float = 1.0
    graceful_shutdown_timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        """Validate and parse configuration."""
        try:
            parsed = urlparse(self.express_url)
            if parsed.hostname:
                self.express_host = parsed.hostname
            if parsed.port:
                self.express_port = parsed.port
        except ValueError as e:
            # Re-raise with our custom message
            if "Port out of range" in str(e):
                raise ValueError("Express port must be between 1 and 65535")
            raise


@dataclass
class PerformanceConfig:
    """Performance-related configuration."""

    # Connection pooling
    http_pool_connections: int = 10
    http_pool_maxsize: int = 20
    http_keep_alive: bool = True

    # WebSocket
    websocket_ping_interval: int = 30
    websocket_ping_timeout: int = 10
    websocket_close_timeout: int = 10

    # Memory management
    max_elements_per_canvas: int = 10000
    element_cache_ttl_hours: int = 24
    memory_cleanup_interval_minutes: int = 60

    # Message batching
    websocket_batch_size: int = 50
    websocket_batch_timeout_ms: int = 100

    # Query optimization
    enable_spatial_indexing: bool = True
    query_result_limit: int = 1000


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""

    # Core monitoring
    enabled: bool = True
    health_check_interval_seconds: int = 10
    health_check_timeout_seconds: float = 3.0
    consecutive_failure_threshold: int = 3

    # Metrics collection
    metrics_enabled: bool = True
    metrics_collection_interval_seconds: int = 30
    memory_monitoring_enabled: bool = True
    performance_metrics_enabled: bool = True

    # Circuit breaker
    circuit_breaker_enabled: bool = True
    circuit_failure_threshold: int = 5
    circuit_recovery_timeout_seconds: int = 60
    circuit_half_open_max_calls: int = 3

    # Alerting
    alerting_enabled: bool = True
    alert_channels: list[str] = field(default_factory=list)
    alert_deduplication_window_seconds: int = 300
    alert_throttle_max_per_hour: int = 10

    # Resource monitoring
    resource_monitoring_enabled: bool = True
    cpu_threshold_percent: float = 80.0
    memory_threshold_percent: float = 85.0
    memory_leak_detection_enabled: bool = True

    # Request tracing
    request_tracing_enabled: bool = True
    trace_sampling_rate: float = 1.0
    trace_headers_enabled: bool = True

    def __post_init__(self) -> None:
        pass

        # Validate thresholds
        if not (0 < self.cpu_threshold_percent <= 100):
            raise ValueError("CPU threshold must be between 0 and 100")
        if not (0 < self.memory_threshold_percent <= 100):
            raise ValueError("Memory threshold must be between 0 and 100")
        if not (0 <= self.trace_sampling_rate <= 1.0):
            raise ValueError("Trace sampling rate must be between 0 and 1")


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    structured_logging: bool = True
    json_format: bool = False
    file_path: str | None = None
    max_file_size_mb: int = 100
    backup_count: int = 5

    # Security logging
    audit_enabled: bool = True
    audit_file_path: str | None = None
    sensitive_fields: list[str] = field(default_factory=list)

    # Correlation tracking
    correlation_id_enabled: bool = True
    correlation_header: str = "X-Correlation-ID"

    def __post_init__(self) -> None:
        pass


@dataclass
class MCPConfig:
    """MCP server configuration."""

    http_enabled: bool = False
    http_host: str = "127.0.0.1"
    http_port: int = 3030
    canvas_server_url: str = "http://localhost:3031"


class Config:
    """Main configuration class."""

    def __init__(self) -> None:
        self.security = SecurityConfig()
        self.server = ServerConfig()
        self.performance = PerformanceConfig()
        self.logging = LoggingConfig()
        self.monitoring = MonitoringConfig()
        self.mcp = MCPConfig()
        self._load_from_pyproject()
        self._load_from_environment()
        self._validate()
        # Phase 3 Security Hardening: Validate JWT secret at startup
        self.security.validate_jwt_secret_at_startup()

    def _load_from_pyproject(self) -> None:
        """Load MCP configuration from pyproject.toml."""
        project_path = Path.cwd()
        pyproject_path = project_path / "pyproject.toml"

        if not pyproject_path.exists() or not _tomli:
            return

        from contextlib import suppress

        with suppress(Exception):
            with pyproject_path.open("rb") as f:
                pyproject_data = _tomli.load(f)

            mcp_config = pyproject_data.get("tool", {}).get("excalidraw-mcp", {})

            if mcp_config:
                self.mcp.http_enabled = mcp_config.get(
                    "http_enabled", self.mcp.http_enabled
                )
                self.mcp.http_host = mcp_config.get("mcp_http_host", self.mcp.http_host)
                self.mcp.http_port = mcp_config.get("mcp_http_port", self.mcp.http_port)
                self.mcp.canvas_server_url = mcp_config.get(
                    "canvas_server_url", self.mcp.canvas_server_url
                )

    def _load_security_config_from_environment(self) -> None:
        """Load security configuration from environment variables."""
        self.security.auth_enabled = (
            os.getenv("AUTH_ENABLED", "false").lower() == "true"
        )
        self.security.jwt_secret = os.getenv("JWT_SECRET", "")

        origins_env = os.getenv("ALLOWED_ORIGINS")
        if origins_env:
            self.security.allowed_origins = [o.strip() for o in origins_env.split(",")]

    def _load_server_config_from_environment(self) -> None:
        """Load server configuration from environment variables."""
        self.server.express_url = os.getenv(
            "EXPRESS_SERVER_URL", self.server.express_url
        )
        self.server.canvas_auto_start = (
            os.getenv("CANVAS_AUTO_START", "true").lower() != "false"
        )

        # Retry configuration from environment
        from contextlib import suppress

        sync_retry_attempts = os.getenv("SYNC_RETRY_ATTEMPTS")
        if sync_retry_attempts:
            with suppress(ValueError):
                self.server.sync_retry_attempts = int(sync_retry_attempts)

        sync_retry_delay = os.getenv("SYNC_RETRY_DELAY_SECONDS")
        if sync_retry_delay:
            with suppress(ValueError):
                self.server.sync_retry_delay_seconds = float(sync_retry_delay)

        sync_retry_max_delay = os.getenv("SYNC_RETRY_MAX_DELAY_SECONDS")
        if sync_retry_max_delay:
            with suppress(ValueError):
                self.server.sync_retry_max_delay_seconds = float(sync_retry_max_delay)

        sync_retry_base = os.getenv("SYNC_RETRY_EXPONENTIAL_BASE")
        if sync_retry_base:
            with suppress(ValueError):
                self.server.sync_retry_exponential_base = float(sync_retry_base)

        sync_retry_jitter = os.getenv("SYNC_RETRY_JITTER")
        if sync_retry_jitter:
            self.server.sync_retry_jitter = sync_retry_jitter.lower() == "true"

        # Parse the updated URL
        self.server.__post_init__()

    def _load_performance_config_from_environment(self) -> None:
        """Load performance configuration from environment variables."""
        from contextlib import suppress

        # Performance config
        max_elements = os.getenv("MAX_ELEMENTS")
        if max_elements:
            with suppress(ValueError):
                self.performance.max_elements_per_canvas = int(max_elements)

    def _load_logging_config_from_environment(self) -> None:
        """Load logging configuration from environment variables."""
        self.logging.level = os.getenv("LOG_LEVEL", self.logging.level)
        self.logging.structured_logging = (
            os.getenv("STRUCTURED_LOGGING", "true").lower() == "true"
        )
        self.logging.json_format = os.getenv("JSON_LOGGING", "false").lower() == "true"
        self.logging.file_path = os.getenv("LOG_FILE")
        self.logging.audit_file_path = os.getenv("AUDIT_LOG_FILE")

    def _load_monitoring_config_from_environment(self) -> None:
        """Load monitoring configuration from environment variables."""
        from contextlib import suppress

        # Monitoring config
        self.monitoring.enabled = (
            os.getenv("MONITORING_ENABLED", "true").lower() == "true"
        )
        self.monitoring.metrics_enabled = (
            os.getenv("METRICS_ENABLED", "true").lower() == "true"
        )
        self.monitoring.alerting_enabled = (
            os.getenv("ALERTING_ENABLED", "true").lower() == "true"
        )
        self.monitoring.circuit_breaker_enabled = (
            os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"
        )

        health_check_interval = os.getenv("HEALTH_CHECK_INTERVAL")
        if health_check_interval:
            with suppress(ValueError):
                self.monitoring.health_check_interval_seconds = int(
                    health_check_interval
                )

        cpu_threshold = os.getenv("CPU_THRESHOLD")
        if cpu_threshold:
            with suppress(ValueError):
                self.monitoring.cpu_threshold_percent = float(cpu_threshold)

        memory_threshold = os.getenv("MEMORY_THRESHOLD")
        if memory_threshold:
            with suppress(ValueError):
                self.monitoring.memory_threshold_percent = float(memory_threshold)

    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        self._load_security_config_from_environment()
        self._load_server_config_from_environment()
        self._load_performance_config_from_environment()
        self._load_logging_config_from_environment()
        self._load_monitoring_config_from_environment()

    def _validate_security_config(self, errors: list[str]) -> None:
        """Validate security configuration values."""
        if self.security.auth_enabled and not self.security.jwt_secret:
            errors.append("JWT_SECRET is required when authentication is enabled")

        if self.security.token_expiration_hours <= 0:
            errors.append("Token expiration must be positive")

    def _validate_server_config(self, errors: list[str]) -> None:
        """Validate server configuration values."""
        if self.server.express_port <= 0 or self.server.express_port > 65535:
            errors.append("Express port must be between 1 and 65535")

        if self.server.health_check_timeout_seconds <= 0:
            errors.append("Health check timeout must be positive")

        if self.server.sync_retry_attempts < 0:
            errors.append("Sync retry attempts must be non-negative")

        if self.server.sync_retry_delay_seconds <= 0:
            errors.append("Sync retry delay must be positive")

        if self.server.sync_retry_max_delay_seconds <= 0:
            errors.append("Sync retry max delay must be positive")

        if self.server.sync_retry_exponential_base <= 1.0:
            errors.append("Sync retry exponential base must be greater than 1.0")

    def _validate_performance_config(self, errors: list[str]) -> None:
        """Validate performance configuration values."""
        if self.performance.max_elements_per_canvas <= 0:
            errors.append("Max elements per canvas must be positive")

        if self.performance.websocket_batch_size <= 0:
            errors.append("WebSocket batch size must be positive")

    def _validate_monitoring_config(self, errors: list[str]) -> None:
        """Validate monitoring configuration values."""
        if self.monitoring.health_check_interval_seconds <= 0:
            errors.append("Health check interval must be positive")

        if self.monitoring.consecutive_failure_threshold <= 0:
            errors.append("Consecutive failure threshold must be positive")

        if self.monitoring.circuit_failure_threshold <= 0:
            errors.append("Circuit breaker failure threshold must be positive")

    def _validate(self) -> None:
        """Validate configuration values."""
        errors: list[str] = []
        self._validate_security_config(errors)
        self._validate_server_config(errors)
        self._validate_performance_config(errors)
        self._validate_monitoring_config(errors)

        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return os.getenv("ENVIRONMENT", "development").lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"


# Global configuration instance
config = Config()
