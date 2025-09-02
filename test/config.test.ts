/**
 * Tests for TypeScript configuration management
 */

import { config, configManager } from '../src/config';

describe('Configuration Management', () => {

  describe('ConfigManager', () => {

    it('should load default configuration', () => {
      expect(config.server.host).toBe('localhost');
      expect(config.server.port).toBe(3032); // Test port from setup
      expect(config.security.authEnabled).toBe(false); // Disabled in test
      expect(config.logging.level).toBe('debug');
    });

    it('should detect test environment', () => {
      expect(configManager.isTest).toBe(true);
      expect(configManager.isDevelopment).toBe(false);
      expect(configManager.isProduction).toBe(false);
    });

    it('should parse allowed origins correctly', () => {
      expect(config.security.allowedOrigins).toEqual([
        'http://localhost:3000',
        'http://localhost:3032'
      ]);
    });

    it('should have proper CORS configuration', () => {
      expect(config.security.corsCredentials).toBe(true);
      expect(config.security.corsMethods).toContain('GET');
      expect(config.security.corsMethods).toContain('POST');
      expect(config.security.corsHeaders).toContain('Authorization');
    });

    it('should have performance settings', () => {
      expect(config.performance.maxElementsPerCanvas).toBeGreaterThan(0);
      expect(config.performance.websocketBatchSize).toBeGreaterThan(0);
      expect(config.performance.queryResultLimit).toBeGreaterThan(0);
    });

  });

  describe('Environment Variable Parsing', () => {

    it('should parse boolean values correctly', () => {
      // In test setup, AUTH_ENABLED is set to 'false'
      expect(config.security.authEnabled).toBe(false);
    });

    it('should parse number values correctly', () => {
      // Port should be parsed as number
      expect(typeof config.server.port).toBe('number');
      expect(config.server.port).toBe(3032);
    });

    it('should parse array values correctly', () => {
      // ALLOWED_ORIGINS should be split into array
      expect(Array.isArray(config.security.allowedOrigins)).toBe(true);
      expect(config.security.allowedOrigins.length).toBeGreaterThan(0);
    });

  });

  describe('Configuration Validation', () => {

    it('should have valid JWT secret in test mode', () => {
      expect(config.security.jwtSecret).toBe('test-secret-key');
    });

    it('should have valid port range', () => {
      expect(config.server.port).toBeGreaterThan(0);
      expect(config.server.port).toBeLessThan(65536);
    });

    it('should have positive timeout values', () => {
      expect(config.server.websocketPingInterval).toBeGreaterThan(0);
      expect(config.server.websocketPingTimeout).toBeGreaterThan(0);
    });

    it('should have positive performance limits', () => {
      expect(config.performance.maxElementsPerCanvas).toBeGreaterThan(0);
      expect(config.performance.websocketBatchSize).toBeGreaterThan(0);
    });

  });

});
