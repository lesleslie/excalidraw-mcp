/**
 * Configuration management for Express canvas server
 */

export interface SecurityConfig {
  authEnabled: boolean;
  jwtSecret: string;
  jwtAlgorithm: string;
  tokenExpirationHours: number;

  // CORS configuration
  allowedOrigins: string[];
  corsCredentials: boolean;
  corsMethods: string[];
  corsHeaders: string[];

  // Rate limiting
  rateLimitWindowMinutes: number;
  rateLimitMaxRequests: number;
}

export interface ServerConfig {
  host: string;
  port: number;
  environment: 'development' | 'production' | 'test';

  // WebSocket configuration
  websocketPingInterval: number;
  websocketPingTimeout: number;
  websocketCloseTimeout: number;
}

export interface PerformanceConfig {
  // Memory management
  maxElementsPerCanvas: number;
  elementCacheTtlHours: number;
  memoryCleanupIntervalMinutes: number;

  // Message batching
  websocketBatchSize: number;
  websocketBatchTimeoutMs: number;

  // Query optimization
  enableSpatialIndexing: boolean;
  queryResultLimit: number;
}

export interface LoggingConfig {
  level: 'error' | 'warn' | 'info' | 'debug';
  format: string;
  filePath?: string;
  maxFileSizeMb: number;
  backupCount: number;

  // Security logging
  auditEnabled: boolean;
  auditFilePath?: string;
  sensitiveFields: string[];
}

export interface AppConfig {
  security: SecurityConfig;
  server: ServerConfig;
  performance: PerformanceConfig;
  logging: LoggingConfig;
}

function getEnvString(key: string, defaultValue: string): string {
  return process.env[key] || defaultValue;
}

function getEnvNumber(key: string, defaultValue: number): number {
  const value = process.env[key];
  return value ? parseInt(value, 10) : defaultValue;
}

function getEnvBoolean(key: string, defaultValue: boolean): boolean {
  const value = process.env[key];
  if (!value) return defaultValue;
  return value.toLowerCase() !== 'false';
}

function getEnvArray(key: string, defaultValue: string[]): string[] {
  const value = process.env[key];
  return value ? value.split(',').map(s => s.trim()) : defaultValue;
}

class ConfigManager {
  private _config: AppConfig;

  constructor() {
    this._config = this.loadFromEnvironment();
    this.validate();
  }

  private loadFromEnvironment(): AppConfig {
    const isDevelopment = getEnvString('NODE_ENV', 'development') === 'development';

    return {
      security: {
        authEnabled: getEnvBoolean('AUTH_ENABLED', !isDevelopment),
        jwtSecret: getEnvString('JWT_SECRET', isDevelopment ? 'dev-secret-key' : ''),
        jwtAlgorithm: 'HS256',
        tokenExpirationHours: getEnvNumber('TOKEN_EXPIRATION_HOURS', 24),

        allowedOrigins: getEnvArray('ALLOWED_ORIGINS', [
          'http://localhost:3031',
          'http://127.0.0.1:3031',
          ...(isDevelopment ? ['http://localhost:3000', 'http://localhost:5173'] : [])
        ]),
        corsCredentials: getEnvBoolean('CORS_CREDENTIALS', true),
        corsMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        corsHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],

        rateLimitWindowMinutes: getEnvNumber('RATE_LIMIT_WINDOW_MINUTES', 15),
        rateLimitMaxRequests: getEnvNumber('RATE_LIMIT_MAX_REQUESTS', isDevelopment ? 1000 : 100),
      },

      server: {
        host: getEnvString('HOST', 'localhost'),
        port: getEnvNumber('PORT', 3031),
        environment: getEnvString('NODE_ENV', 'development') as 'development' | 'production' | 'test',

        websocketPingInterval: getEnvNumber('WS_PING_INTERVAL', 30000),
        websocketPingTimeout: getEnvNumber('WS_PING_TIMEOUT', 10000),
        websocketCloseTimeout: getEnvNumber('WS_CLOSE_TIMEOUT', 10000),
      },

      performance: {
        maxElementsPerCanvas: getEnvNumber('MAX_ELEMENTS_PER_CANVAS', 10000),
        elementCacheTtlHours: getEnvNumber('ELEMENT_CACHE_TTL_HOURS', 24),
        memoryCleanupIntervalMinutes: getEnvNumber('MEMORY_CLEANUP_INTERVAL_MINUTES', 60),

        websocketBatchSize: getEnvNumber('WEBSOCKET_BATCH_SIZE', 50),
        websocketBatchTimeoutMs: getEnvNumber('WEBSOCKET_BATCH_TIMEOUT_MS', 100),

        enableSpatialIndexing: getEnvBoolean('ENABLE_SPATIAL_INDEXING', true),
        queryResultLimit: getEnvNumber('QUERY_RESULT_LIMIT', 1000),
      },

      logging: {
        level: getEnvString('LOG_LEVEL', isDevelopment ? 'debug' : 'info') as 'error' | 'warn' | 'info' | 'debug',
        format: 'combined',
        filePath: getEnvString('LOG_FILE', ''),
        maxFileSizeMb: getEnvNumber('LOG_MAX_FILE_SIZE_MB', 100),
        backupCount: getEnvNumber('LOG_BACKUP_COUNT', 5),

        auditEnabled: getEnvBoolean('AUDIT_ENABLED', !isDevelopment),
        auditFilePath: getEnvString('AUDIT_LOG_FILE', ''),
        sensitiveFields: getEnvArray('SENSITIVE_FIELDS', ['password', 'token', 'secret', 'key']),
      },
    };
  }

  private validate(): void {
    const errors: string[] = [];

    // Security validation
    if (this._config.security.authEnabled && !this._config.security.jwtSecret) {
      errors.push('JWT_SECRET is required when authentication is enabled');
    }

    if (this._config.security.tokenExpirationHours <= 0) {
      errors.push('Token expiration must be positive');
    }

    // Server validation
    if (this._config.server.port <= 0 || this._config.server.port > 65535) {
      errors.push('Port must be between 1 and 65535');
    }

    // Performance validation
    if (this._config.performance.maxElementsPerCanvas <= 0) {
      errors.push('Max elements per canvas must be positive');
    }

    if (this._config.performance.websocketBatchSize <= 0) {
      errors.push('WebSocket batch size must be positive');
    }

    if (errors.length > 0) {
      throw new Error(`Configuration validation failed: ${errors.join('; ')}`);
    }
  }

  get config(): AppConfig {
    return this._config;
  }

  get isDevelopment(): boolean {
    return this._config.server.environment === 'development';
  }

  get isProduction(): boolean {
    return this._config.server.environment === 'production';
  }

  get isTest(): boolean {
    return this._config.server.environment === 'test';
  }
}

// Global configuration instance
export const configManager = new ConfigManager();
export const config = configManager.config;
