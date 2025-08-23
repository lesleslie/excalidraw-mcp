/**
 * Jest test setup and configuration
 */

// Set test environment
process.env.NODE_ENV = 'test';
process.env.AUTH_ENABLED = 'false';
process.env.JWT_SECRET = 'test-secret-key';
process.env.PORT = '3032'; // Different port for tests
process.env.ALLOWED_ORIGINS = 'http://localhost:3000,http://localhost:3032';

// Mock console methods to reduce noise in tests unless explicitly needed
const originalConsole = { ...console };

beforeEach(() => {
  // Reset console for each test
  Object.assign(console, originalConsole);
});

// Global test utilities
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeValidUUID(): R;
      toBeValidElement(): R;
      toBeValidWebSocketMessage(): R;
    }
  }
}

// Custom Jest matchers
expect.extend({
  toBeValidUUID(received: string) {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    const pass = uuidRegex.test(received);
    
    if (pass) {
      return {
        message: () => `expected ${received} not to be a valid UUID`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be a valid UUID`,
        pass: false,
      };
    }
  },
  
  toBeValidElement(received: any) {
    const requiredFields = ['id', 'type', 'x', 'y', 'version', 'createdAt', 'updatedAt'];
    const missingFields = requiredFields.filter(field => !(field in received));
    
    if (missingFields.length === 0) {
      return {
        message: () => `expected element not to have all required fields`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected element to have required fields: ${missingFields.join(', ')}`,
        pass: false,
      };
    }
  },
  
  toBeValidWebSocketMessage(received: any) {
    const hasType = 'type' in received && typeof received.type === 'string';
    const hasTimestamp = 'timestamp' in received || 'data' in received;
    
    if (hasType && hasTimestamp) {
      return {
        message: () => `expected WebSocket message not to be valid`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected WebSocket message to have 'type' and timestamp/data fields`,
        pass: false,
      };
    }
  }
});

// Mock WebSocket for tests
class MockWebSocket {
  public readyState = 1; // OPEN
  public url?: string;
  private listeners: { [event: string]: Function[] } = {};
  
  constructor(url?: string) {
    this.url = url;
  }
  
  send(data: string): void {
    // Mock send - could be extended to simulate responses
  }
  
  close(code?: number, reason?: string): void {
    this.readyState = 3; // CLOSED
    this.emit('close', { code, reason });
  }
  
  on(event: string, listener: Function): void {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(listener);
  }
  
  emit(event: string, data?: any): void {
    if (this.listeners[event]) {
      this.listeners[event].forEach(listener => listener(data));
    }
  }
  
  ping(): void {
    // Mock ping
  }
}

// Make MockWebSocket available globally for tests
(global as any).MockWebSocket = MockWebSocket;