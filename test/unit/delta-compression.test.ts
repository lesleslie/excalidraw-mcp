/**
 * Unit tests for delta compression utilities
 */

import {
  calculateElementDelta,
  applyElementDelta,
  compressElementUpdates,
  validateDelta,
  mergeDeltas,
  reconstructElement,
  DeltaHistory,
  type ElementDelta,
} from '../../src/utils/delta-compression';
import { ServerElement } from '../../src/types';

describe('Delta Compression', () => {
  const mockOldElement: ServerElement = {
    id: 'test-123',
    type: 'rectangle',
    x: 100,
    y: 200,
    width: 150,
    height: 100,
    strokeColor: '#000000',
    backgroundColor: '#ffffff',
    strokeWidth: 2,
    opacity: 100,
    roughness: 1,
    version: 1,
    createdAt: '2025-01-01T00:00:00.000Z',
    updatedAt: '2025-01-01T00:00:00.000Z',
    locked: false,
  };

  const mockNewElement: ServerElement = {
    ...mockOldElement,
    x: 120, // Small change
    strokeColor: '#ff0000', // Color change
    version: 2,
    updatedAt: '2025-01-01T00:01:00.000Z',
  };

  describe('calculateElementDelta', () => {
    it('should return full element when no old element exists', () => {
      const result = calculateElementDelta(undefined, mockNewElement);
      
      expect(result.hasDelta).toBe(false);
      expect(result.fullElement).toEqual(mockNewElement);
      expect(result.delta).toBeUndefined();
    });

    it('should return delta when elements differ', () => {
      const result = calculateElementDelta(mockOldElement, mockNewElement);
      
      expect(result.hasDelta).toBe(true);
      expect(result.delta).toBeDefined();
      expect(result.delta!.id).toBe('test-123');
      expect(result.delta!.version).toBe(2);
      expect(result.delta!.changes).toMatchObject({
        x: 120,
        strokeColor: '#ff0000',
        version: 2,
        updatedAt: '2025-01-01T00:01:00.000Z',
      });
    });

    it('should return full element when changes are extensive', () => {
      const extensiveChanges: ServerElement = {
        ...mockOldElement,
        x: 300,
        y: 400,
        width: 500,
        height: 600,
        strokeColor: '#ff0000',
        backgroundColor: '#00ff00',
        strokeWidth: 5,
        opacity: 50,
        roughness: 2,
        version: 2,
        updatedAt: '2025-01-01T00:01:00.000Z',
      };

      const result = calculateElementDelta(mockOldElement, extensiveChanges);
      
      expect(result.hasDelta).toBe(false);
      expect(result.fullElement).toEqual(extensiveChanges);
    });

    it('should handle identical elements', () => {
      const result = calculateElementDelta(mockOldElement, mockOldElement);
      
      // Should still include version and timestamp in changes
      expect(result.hasDelta).toBe(true);
      expect(result.delta!.changes).toMatchObject({
        version: mockOldElement.version,
        updatedAt: mockOldElement.updatedAt,
      });
    });
  });

  describe('applyElementDelta', () => {
    it('should apply delta changes correctly', () => {
      const delta: ElementDelta = {
        id: 'test-123',
        version: 2,
        changes: {
          x: 120,
          strokeColor: '#ff0000',
          version: 2,
          updatedAt: '2025-01-01T00:01:00.000Z',
        },
        timestamp: '2025-01-01T00:01:00.000Z',
      };

      const result = applyElementDelta(mockOldElement, delta);

      expect(result.x).toBe(120);
      expect(result.strokeColor).toBe('#ff0000');
      expect(result.version).toBe(2);
      expect(result.updatedAt).toBe('2025-01-01T00:01:00.000Z');
      expect(result.id).toBe('test-123'); // ID should not change
    });

    it('should throw error for outdated delta version', () => {
      const outdatedDelta: ElementDelta = {
        id: 'test-123',
        version: 1, // Same as current version
        changes: { x: 120 },
        timestamp: '2025-01-01T00:01:00.000Z',
      };

      expect(() => {
        applyElementDelta(mockOldElement, outdatedDelta);
      }).toThrow('Delta version 1 is not newer than base version 1');
    });

    it('should preserve base element properties not in delta', () => {
      const minimalDelta: ElementDelta = {
        id: 'test-123',
        version: 2,
        changes: { x: 120 },
        timestamp: '2025-01-01T00:01:00.000Z',
      };

      const result = applyElementDelta(mockOldElement, minimalDelta);

      expect(result.x).toBe(120); // Changed
      expect(result.y).toBe(200); // Unchanged
      expect(result.strokeColor).toBe('#000000'); // Unchanged
      expect(result.type).toBe('rectangle'); // Unchanged
    });
  });

  describe('compressElementUpdates', () => {
    it('should identify deleted elements', () => {
      const oldElements = new Map([
        ['keep', mockOldElement],
        ['delete', { ...mockOldElement, id: 'delete' }],
      ]);
      const newElements = new Map([
        ['keep', mockNewElement],
      ]);

      const result = compressElementUpdates(oldElements, newElements);

      expect(result.deletedIds).toContain('delete');
      expect(result.deletedIds).not.toContain('keep');
    });

    it('should generate deltas for changed elements', () => {
      const oldElements = new Map([['test-123', mockOldElement]]);
      const newElements = new Map([['test-123', mockNewElement]]);

      const result = compressElementUpdates(oldElements, newElements);

      expect(result.deltas).toHaveLength(1);
      expect(result.deltas[0].id).toBe('test-123');
      expect(result.fullElements).toHaveLength(0);
    });

    it('should include new elements as full elements', () => {
      const oldElements = new Map();
      const newElements = new Map([['new-123', mockNewElement]]);

      const result = compressElementUpdates(oldElements, newElements);

      expect(result.fullElements).toHaveLength(1);
      expect(result.fullElements[0]).toEqual(mockNewElement);
      expect(result.deltas).toHaveLength(0);
    });
  });

  describe('validateDelta', () => {
    const validDelta: ElementDelta = {
      id: 'test-123',
      version: 2,
      changes: { x: 120 },
      timestamp: '2025-01-01T00:01:00.000Z',
    };

    it('should validate correct delta', () => {
      expect(validateDelta(validDelta)).toBe(true);
    });

    it('should reject delta without required fields', () => {
      expect(validateDelta({ ...validDelta, id: '' })).toBe(false);
      expect(validateDelta({ ...validDelta, version: 0 })).toBe(false);
      expect(validateDelta({ ...validDelta, timestamp: '' })).toBe(false);
      expect(validateDelta({ ...validDelta, changes: {} })).toBe(false);
    });

    it('should reject delta with invalid version', () => {
      expect(validateDelta({ ...validDelta, version: 0 })).toBe(false);
      expect(validateDelta({ ...validDelta, version: -1 })).toBe(false);
    });

    it('should reject delta with invalid timestamp', () => {
      expect(validateDelta({ ...validDelta, timestamp: 'invalid-date' })).toBe(false);
    });
  });

  describe('mergeDeltas', () => {
    const delta1: ElementDelta = {
      id: 'test-123',
      version: 2,
      changes: { x: 120 },
      timestamp: '2025-01-01T00:01:00.000Z',
    };

    const delta2: ElementDelta = {
      id: 'test-123',
      version: 3,
      changes: { y: 300, strokeColor: '#ff0000' },
      timestamp: '2025-01-01T00:02:00.000Z',
    };

    it('should merge sequential deltas', () => {
      const result = mergeDeltas([delta1, delta2]);

      expect(result).toBeDefined();
      expect(result!.id).toBe('test-123');
      expect(result!.version).toBe(3);
      expect(result!.changes).toMatchObject({
        x: 120,
        y: 300,
        strokeColor: '#ff0000',
      });
      expect(result!.timestamp).toBe('2025-01-01T00:02:00.000Z');
    });

    it('should return null for empty array', () => {
      expect(mergeDeltas([])).toBeNull();
    });

    it('should return single delta unchanged', () => {
      const result = mergeDeltas([delta1]);
      expect(result).toEqual(delta1);
    });

    it('should throw error for non-sequential deltas', () => {
      const nonSequentialDelta: ElementDelta = {
        ...delta2,
        version: 5, // Gap in version sequence
      };

      expect(() => {
        mergeDeltas([delta1, nonSequentialDelta]);
      }).toThrow('Cannot merge non-sequential deltas');
    });
  });

  describe('reconstructElement', () => {
    it('should reconstruct element from base and deltas', () => {
      const deltas: ElementDelta[] = [
        {
          id: 'test-123',
          version: 2,
          changes: { x: 120 },
          timestamp: '2025-01-01T00:01:00.000Z',
        },
        {
          id: 'test-123',
          version: 3,
          changes: { y: 300, strokeColor: '#ff0000' },
          timestamp: '2025-01-01T00:02:00.000Z',
        },
      ];

      const result = reconstructElement(mockOldElement, deltas);

      expect(result.x).toBe(120);
      expect(result.y).toBe(300);
      expect(result.strokeColor).toBe('#ff0000');
      expect(result.version).toBe(3);
      expect(result.updatedAt).toBe('2025-01-01T00:02:00.000Z');
    });

    it('should handle empty deltas array', () => {
      const result = reconstructElement(mockOldElement, []);
      expect(result).toEqual(mockOldElement);
    });
  });

  describe('DeltaHistory', () => {
    let history: DeltaHistory;

    beforeEach(() => {
      history = new DeltaHistory();
    });

    it('should store and retrieve deltas', () => {
      const delta: ElementDelta = {
        id: 'test-123',
        version: 2,
        changes: { x: 120 },
        timestamp: '2025-01-01T00:01:00.000Z',
      };

      history.addDelta(delta);

      const retrieved = history.getHistory('test-123');
      expect(retrieved).toHaveLength(1);
      expect(retrieved[0]).toEqual(delta);
    });

    it('should limit history length', () => {
      const delta: ElementDelta = {
        id: 'test-123',
        version: 1,
        changes: { x: 120 },
        timestamp: '2025-01-01T00:01:00.000Z',
      };

      // Add more deltas than the limit (100)
      for (let i = 0; i < 150; i++) {
        history.addDelta({ ...delta, version: i + 1 });
      }

      const retrieved = history.getHistory('test-123');
      expect(retrieved.length).toBeLessThanOrEqual(100);
    });

    it('should get last delta', () => {
      const delta1: ElementDelta = {
        id: 'test-123',
        version: 1,
        changes: { x: 120 },
        timestamp: '2025-01-01T00:01:00.000Z',
      };

      const delta2: ElementDelta = {
        id: 'test-123',
        version: 2,
        changes: { y: 300 },
        timestamp: '2025-01-01T00:02:00.000Z',
      };

      history.addDelta(delta1);
      history.addDelta(delta2);

      const last = history.getLastDelta('test-123');
      expect(last).toEqual(delta2);
    });

    it('should clear history', () => {
      const delta: ElementDelta = {
        id: 'test-123',
        version: 1,
        changes: { x: 120 },
        timestamp: '2025-01-01T00:01:00.000Z',
      };

      history.addDelta(delta);
      history.clearHistory('test-123');

      expect(history.getHistory('test-123')).toHaveLength(0);
    });

    it('should provide statistics', () => {
      const delta: ElementDelta = {
        id: 'test-123',
        version: 1,
        changes: { x: 120 },
        timestamp: '2025-01-01T00:01:00.000Z',
      };

      history.addDelta(delta);
      history.addDelta({ ...delta, id: 'test-456' });

      const stats = history.getStats();
      expect(stats.totalElements).toBe(2);
      expect(stats.totalDeltas).toBe(2);
      expect(stats.memoryUsage).toBeGreaterThan(0);
    });
  });
});