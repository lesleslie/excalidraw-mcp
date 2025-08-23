/**
 * Tests for element storage with LRU cache and indexing
 */

import { ElementStorage } from '../../src/storage/element-storage';
import { ServerElement, ElementType } from '../../src/types';

describe('ElementStorage', () => {
  let storage: ElementStorage;
  
  beforeEach(() => {
    storage = new ElementStorage();
  });
  
  afterEach(() => {
    storage.clear();
  });
  
  const createTestElement = (id: string, type: ElementType = 'rectangle', x = 0, y = 0): ServerElement => ({
    id,
    type,
    x,
    y,
    width: 100,
    height: 100,
    strokeColor: '#000000',
    backgroundColor: '#ffffff',
    strokeWidth: 2,
    opacity: 100,
    roughness: 1,
    version: 1,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    locked: false
  });
  
  describe('Basic Storage Operations', () => {
    
    it('should store and retrieve elements', () => {
      const element = createTestElement('test-1');
      
      storage.set('test-1', element);
      const retrieved = storage.get('test-1');
      
      expect(retrieved).toEqual(element);
    });
    
    it('should check element existence', () => {
      const element = createTestElement('test-1');
      
      expect(storage.has('test-1')).toBe(false);
      
      storage.set('test-1', element);
      expect(storage.has('test-1')).toBe(true);
    });
    
    it('should delete elements', () => {
      const element = createTestElement('test-1');
      
      storage.set('test-1', element);
      expect(storage.has('test-1')).toBe(true);
      
      const deleted = storage.delete('test-1');
      expect(deleted).toBe(true);
      expect(storage.has('test-1')).toBe(false);
    });
    
    it('should return false when deleting non-existent element', () => {
      const deleted = storage.delete('non-existent');
      expect(deleted).toBe(false);
    });
    
    it('should clear all elements', () => {
      storage.set('test-1', createTestElement('test-1'));
      storage.set('test-2', createTestElement('test-2'));
      
      expect(storage.getAll().length).toBe(2);
      
      storage.clear();
      expect(storage.getAll().length).toBe(0);
    });
    
  });
  
  describe('Type Indexing', () => {
    
    it('should filter elements by type', () => {
      storage.set('rect-1', createTestElement('rect-1', 'rectangle'));
      storage.set('circle-1', createTestElement('circle-1', 'ellipse'));
      storage.set('rect-2', createTestElement('rect-2', 'rectangle'));
      
      const rectangles = storage.query({ type: 'rectangle' });
      expect(rectangles).toHaveLength(2);
      expect(rectangles.every(el => el.type === 'rectangle')).toBe(true);
      
      const ellipses = storage.query({ type: 'ellipse' });
      expect(ellipses).toHaveLength(1);
      expect(ellipses[0].type).toBe('ellipse');
    });
    
    it('should return empty array for non-existent type', () => {
      storage.set('rect-1', createTestElement('rect-1', 'rectangle'));
      
      const arrows = storage.query({ type: 'arrow' });
      expect(arrows).toHaveLength(0);
    });
    
  });
  
  describe('Position Filtering', () => {
    
    it('should filter elements by exact position', () => {
      storage.set('el-1', createTestElement('el-1', 'rectangle', 100, 200));
      storage.set('el-2', createTestElement('el-2', 'rectangle', 150, 250));
      storage.set('el-3', createTestElement('el-3', 'rectangle', 100, 200));
      
      const elementsAt100_200 = storage.query({ x: 100, y: 200 });
      expect(elementsAt100_200).toHaveLength(2);
      expect(elementsAt100_200.every(el => el.x === 100 && el.y === 200)).toBe(true);
    });
    
    it('should filter elements by single coordinate', () => {
      storage.set('el-1', createTestElement('el-1', 'rectangle', 100, 200));
      storage.set('el-2', createTestElement('el-2', 'rectangle', 100, 250));
      storage.set('el-3', createTestElement('el-3', 'rectangle', 150, 200));
      
      const elementsAtX100 = storage.query({ x: 100 });
      expect(elementsAtX100).toHaveLength(2);
      expect(elementsAtX100.every(el => el.x === 100)).toBe(true);
    });
    
  });
  
  describe('Combined Filtering', () => {
    
    it('should filter by multiple criteria', () => {
      storage.set('rect-1', createTestElement('rect-1', 'rectangle', 100, 200));
      storage.set('rect-2', createTestElement('rect-2', 'rectangle', 150, 200));
      storage.set('ellipse-1', createTestElement('ellipse-1', 'ellipse', 100, 200));
      
      const filteredElements = storage.query({
        type: 'rectangle',
        x: 100,
        y: 200
      });
      
      expect(filteredElements).toHaveLength(1);
      expect(filteredElements[0].id).toBe('rect-1');
    });
    
    it('should handle locked element filtering', () => {
      const lockedElement = createTestElement('locked-1');
      lockedElement.locked = true;
      
      storage.set('normal-1', createTestElement('normal-1'));
      storage.set('locked-1', lockedElement);
      
      const lockedElements = storage.query({ locked: true });
      expect(lockedElements).toHaveLength(1);
      expect(lockedElements[0].locked).toBe(true);
      
      const unlockedElements = storage.query({ locked: false });
      expect(unlockedElements).toHaveLength(1);
      expect(unlockedElements[0].locked).toBe(false);
    });
    
  });
  
  describe('Pagination and Sorting', () => {
    
    it('should support pagination', () => {
      // Add multiple elements
      for (let i = 0; i < 10; i++) {
        storage.set(`el-${i}`, createTestElement(`el-${i}`));
      }
      
      const firstPage = storage.getAll({ limit: 5, offset: 0 });
      expect(firstPage).toHaveLength(5);
      
      const secondPage = storage.getAll({ limit: 5, offset: 5 });
      expect(secondPage).toHaveLength(5);
      
      // Should have different elements
      const firstPageIds = firstPage.map(el => el.id);
      const secondPageIds = secondPage.map(el => el.id);
      expect(firstPageIds).not.toEqual(secondPageIds);
    });
    
    it('should support sorting by x coordinate', () => {
      storage.set('el-1', createTestElement('el-1', 'rectangle', 300, 0));
      storage.set('el-2', createTestElement('el-2', 'rectangle', 100, 0));
      storage.set('el-3', createTestElement('el-3', 'rectangle', 200, 0));
      
      const sortedAsc = storage.getAll({ sortBy: 'x', sortOrder: 'asc' });
      expect(sortedAsc.map(el => el.x)).toEqual([100, 200, 300]);
      
      const sortedDesc = storage.getAll({ sortBy: 'x', sortOrder: 'desc' });
      expect(sortedDesc.map(el => el.x)).toEqual([300, 200, 100]);
    });
    
    it('should apply pagination to query results', () => {
      // Add rectangles and ellipses
      for (let i = 0; i < 5; i++) {
        storage.set(`rect-${i}`, createTestElement(`rect-${i}`, 'rectangle'));
        storage.set(`ellipse-${i}`, createTestElement(`ellipse-${i}`, 'ellipse'));
      }
      
      const rectangles = storage.query(
        { type: 'rectangle' },
        { limit: 3, offset: 1 }
      );
      
      expect(rectangles).toHaveLength(3);
      expect(rectangles.every(el => el.type === 'rectangle')).toBe(true);
    });
    
  });
  
  describe('Spatial Indexing', () => {
    
    it('should support spatial bounds queries', () => {
      storage.set('inside', createTestElement('inside', 'rectangle', 50, 50));
      storage.set('outside', createTestElement('outside', 'rectangle', 200, 200));
      storage.set('edge', createTestElement('edge', 'rectangle', 100, 100));
      
      const spatialBounds = {
        minX: 0,
        maxX: 150,
        minY: 0,
        maxY: 150
      };
      
      const elementsInBounds = storage.query({ spatialBounds });
      
      // Should include elements within bounds
      const foundIds = elementsInBounds.map(el => el.id);
      expect(foundIds).toContain('inside');
      expect(foundIds).toContain('edge');
      expect(foundIds).not.toContain('outside');
    });
    
  });
  
  describe('Storage Statistics', () => {
    
    it('should provide accurate storage statistics', () => {
      storage.set('rect-1', createTestElement('rect-1', 'rectangle'));
      storage.set('rect-2', createTestElement('rect-2', 'rectangle'));
      storage.set('ellipse-1', createTestElement('ellipse-1', 'ellipse'));
      
      const stats = storage.getStats();
      
      expect(stats.totalElements).toBe(3);
      expect(stats.typeDistribution.rectangle).toBe(2);
      expect(stats.typeDistribution.ellipse).toBe(1);
      expect(stats.memoryUsage).toBeGreaterThan(0);
    });
    
    it('should track cache size correctly', () => {
      const stats1 = storage.getStats();
      expect(stats1.totalElements).toBe(0);
      
      storage.set('el-1', createTestElement('el-1'));
      const stats2 = storage.getStats();
      expect(stats2.totalElements).toBe(1);
      
      storage.delete('el-1');
      const stats3 = storage.getStats();
      expect(stats3.totalElements).toBe(0);
    });
    
  });
  
  describe('Memory Management', () => {
    
    it('should handle cache cleanup', () => {
      // This test verifies that forceCleanup doesn't throw errors
      storage.set('el-1', createTestElement('el-1'));
      
      expect(() => storage.forceCleanup()).not.toThrow();
      
      // Element should still be there after cleanup (not expired)
      expect(storage.has('el-1')).toBe(true);
    });
    
  });
  
});