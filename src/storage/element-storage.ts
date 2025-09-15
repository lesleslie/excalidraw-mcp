/**
 * Element storage with LRU cache, indexing, and memory management
 */

import { LRUCache } from 'lru-cache';
import { ServerElement, ElementType } from '../types';
import { config } from '../config';

export interface SpatialIndex {
  x: number;
  y: number;
  width: number;
  height: number;
  elementId: string;
}

export interface QueryFilter {
  type?: ElementType;
  x?: number;
  y?: number;
  locked?: boolean;
  spatialBounds?: {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
  };
}

export interface QueryOptions {
  limit?: number;
  offset?: number;
  sortBy?: 'createdAt' | 'updatedAt' | 'x' | 'y';
  sortOrder?: 'asc' | 'desc';
}

/**
 * QuadTree implementation for spatial indexing
 */
class QuadTreeNode {
  private bounds: { x: number; y: number; width: number; height: number };
  private elements: SpatialIndex[] = [];
  private children: QuadTreeNode[] | null = null;
  private readonly maxElements = 10;
  private readonly maxDepth = 5;
  private depth: number;

  constructor(bounds: { x: number; y: number; width: number; height: number }, depth = 0) {
    this.bounds = bounds;
    this.depth = depth;
  }

  insert(element: SpatialIndex): void {
    if (!this.contains(element)) {
      return;
    }

    if (this.elements.length < this.maxElements || this.depth >= this.maxDepth) {
      this.elements.push(element);
      return;
    }

    if (!this.children) {
      this.subdivide();
    }

    for (const child of this.children!) {
      child.insert(element);
    }
  }

  query(bounds: { x: number; y: number; width: number; height: number }): string[] {
    const result: string[] = [];

    if (!this.intersects(bounds)) {
      return result;
    }

    for (const element of this.elements) {
      if (this.elementIntersects(element, bounds)) {
        result.push(element.elementId);
      }
    }

    if (this.children) {
      for (const child of this.children) {
        result.push(...child.query(bounds));
      }
    }

    return result;
  }

  remove(elementId: string): boolean {
    const index = this.elements.findIndex(el => el.elementId === elementId);
    if (index !== -1) {
      this.elements.splice(index, 1);
      return true;
    }

    if (this.children) {
      for (const child of this.children) {
        if (child.remove(elementId)) {
          return true;
        }
      }
    }

    return false;
  }

  private contains(element: SpatialIndex): boolean {
    return (
      element.x >= this.bounds.x &&
      element.x < this.bounds.x + this.bounds.width &&
      element.y >= this.bounds.y &&
      element.y < this.bounds.y + this.bounds.height
    );
  }

  private intersects(bounds: { x: number; y: number; width: number; height: number }): boolean {
    return !(
      bounds.x >= this.bounds.x + this.bounds.width ||
      bounds.x + bounds.width <= this.bounds.x ||
      bounds.y >= this.bounds.y + this.bounds.height ||
      bounds.y + bounds.height <= this.bounds.y
    );
  }

  private elementIntersects(element: SpatialIndex, bounds: { x: number; y: number; width: number; height: number }): boolean {
    return !(
      element.x >= bounds.x + bounds.width ||
      element.x + element.width <= bounds.x ||
      element.y >= bounds.y + bounds.height ||
      element.y + element.height <= bounds.y
    );
  }

  private subdivide(): void {
    const halfWidth = this.bounds.width / 2;
    const halfHeight = this.bounds.height / 2;
    const x = this.bounds.x;
    const y = this.bounds.y;

    this.children = [
      new QuadTreeNode({ x, y, width: halfWidth, height: halfHeight }, this.depth + 1),
      new QuadTreeNode({ x: x + halfWidth, y, width: halfWidth, height: halfHeight }, this.depth + 1),
      new QuadTreeNode({ x, y: y + halfHeight, width: halfWidth, height: halfHeight }, this.depth + 1),
      new QuadTreeNode({ x: x + halfWidth, y: y + halfHeight, width: halfWidth, height: halfHeight }, this.depth + 1),
    ];

    for (const element of this.elements) {
      for (const child of this.children) {
        child.insert(element);
      }
    }

    this.elements = [];
  }
}

/**
 * Element storage manager with LRU cache and spatial indexing
 */
export class ElementStorage {
  private cache: LRUCache<string, ServerElement>;
  private typeIndex: Map<ElementType, Set<string>> = new Map();
  private spatialIndex: QuadTreeNode;
  private lastCleanup: number = Date.now();

  constructor(startCleanupInterval = true) {
    // Initialize LRU cache
    this.cache = new LRUCache<string, ServerElement>({
      max: config.performance.maxElementsPerCanvas,
      ttl: config.performance.elementCacheTtlHours * 60 * 60 * 1000, // Convert to milliseconds
      dispose: (element, key) => {
        this.removeFromIndexes(key, element);
      },
      updateAgeOnGet: true,
      updateAgeOnHas: true,
    });

    // Initialize spatial index with world bounds
    this.spatialIndex = new QuadTreeNode({
      x: -1000000,
      y: -1000000,
      width: 2000000,
      height: 2000000
    });

    // Initialize type indexes
    for (const type of ['rectangle', 'ellipse', 'diamond', 'text', 'line', 'arrow', 'draw', 'image', 'frame', 'embeddable', 'magicframe'] as ElementType[]) {
      this.typeIndex.set(type, new Set());
    }

    // Start cleanup interval (unless disabled for tests)
    if (startCleanupInterval) {
      this.startCleanupInterval();
    }
  }

  /**
   * Store an element
   */
  set(id: string, element: ServerElement): void {
    // Remove from old indexes if updating
    const existing = this.cache.get(id);
    if (existing) {
      this.removeFromIndexes(id, existing);
    }

    // Store in cache
    this.cache.set(id, element);

    // Add to indexes
    this.addToIndexes(id, element);
  }

  /**
   * Get an element by ID
   */
  get(id: string): ServerElement | undefined {
    return this.cache.get(id);
  }

  /**
   * Check if an element exists
   */
  has(id: string): boolean {
    return this.cache.has(id);
  }

  /**
   * Delete an element
   */
  delete(id: string): boolean {
    const element = this.cache.get(id);
    if (element) {
      this.removeFromIndexes(id, element);
      return this.cache.delete(id);
    }
    return false;
  }

  /**
   * Get all elements (with pagination)
   */
  getAll(options: QueryOptions = {}): ServerElement[] {
    const elements = Array.from(this.cache.values());

    // Sort elements
    if (options.sortBy) {
      elements.sort((a, b) => {
        const aVal = a[options.sortBy!];
        const bVal = b[options.sortBy!];

        let comparison = 0;
        if (aVal < bVal) comparison = -1;
        else if (aVal > bVal) comparison = 1;

        return options.sortOrder === 'desc' ? -comparison : comparison;
      });
    }

    // Apply pagination
    const offset = options.offset || 0;
    const limit = options.limit || elements.length;

    return elements.slice(offset, offset + limit);
  }

  /**
   * Query elements with filters
   */
  query(filter: QueryFilter, options: QueryOptions = {}): ServerElement[] {
    let candidateIds: Set<string> | null = null;

    // Use type index if type filter is specified
    if (filter.type) {
      candidateIds = this.typeIndex.get(filter.type) || new Set();
    }

    // Use spatial index if spatial bounds are specified
    if (filter.spatialBounds && config.performance.enableSpatialIndexing) {
      // Convert from {minX, maxX, minY, maxY} to {x, y, width, height}
      const bounds = {
        x: filter.spatialBounds.minX,
        y: filter.spatialBounds.minY,
        width: filter.spatialBounds.maxX - filter.spatialBounds.minX,
        height: filter.spatialBounds.maxY - filter.spatialBounds.minY
      };
      const spatialIds = new Set(this.spatialIndex.query(bounds));
      candidateIds = candidateIds ?
        new Set([...candidateIds].filter(id => spatialIds.has(id))) :
        spatialIds;
    }

    // Get elements to check
    const elementsToCheck = candidateIds ?
      Array.from(candidateIds).map(id => this.cache.get(id)).filter(Boolean) as ServerElement[] :
      Array.from(this.cache.values());

    // Apply filters
    let filteredElements = elementsToCheck.filter(element => {
      if (filter.x !== undefined && element.x !== filter.x) return false;
      if (filter.y !== undefined && element.y !== filter.y) return false;
      if (filter.locked !== undefined && element.locked !== filter.locked) return false;
      return true;
    });

    // Sort elements
    if (options.sortBy) {
      filteredElements.sort((a, b) => {
        const aVal = a[options.sortBy!];
        const bVal = b[options.sortBy!];

        let comparison = 0;
        if (aVal < bVal) comparison = -1;
        else if (aVal > bVal) comparison = 1;

        return options.sortOrder === 'desc' ? -comparison : comparison;
      });
    }

    // Apply pagination
    const offset = options.offset || 0;
    const limit = Math.min(options.limit || filteredElements.length, config.performance.queryResultLimit);

    return filteredElements.slice(offset, offset + limit);
  }

  /**
   * Get storage statistics
   */
  getStats(): {
    totalElements: number;
    cacheSize: number;
    maxSize: number;
    memoryUsage: number;
    typeDistribution: Record<string, number>;
  } {
    const typeDistribution: Record<string, number> = {};
    for (const [type, ids] of this.typeIndex.entries()) {
      typeDistribution[type] = ids.size;
    }

    return {
      totalElements: this.cache.size,
      cacheSize: this.cache.size,
      maxSize: this.cache.max,
      memoryUsage: this.cache.size * 1024, // Rough estimate
      typeDistribution
    };
  }

  /**
   * Clear all elements
   */
  clear(): void {
    this.cache.clear();
    this.typeIndex.clear();
    this.spatialIndex = new QuadTreeNode({
      x: -1000000,
      y: -1000000,
      width: 2000000,
      height: 2000000
    });

    // Reinitialize type indexes
    for (const type of ['rectangle', 'ellipse', 'diamond', 'text', 'line', 'arrow', 'draw', 'image', 'frame', 'embeddable', 'magicframe'] as ElementType[]) {
      this.typeIndex.set(type, new Set());
    }
  }

  /**
   * Force garbage collection
   */
  forceCleanup(): void {
    this.cache.purgeStale();
    this.lastCleanup = Date.now();
  }

  private addToIndexes(id: string, element: ServerElement): void {
    // Add to type index
    const typeSet = this.typeIndex.get(element.type);
    if (typeSet) {
      typeSet.add(id);
    }

    // Add to spatial index
    if (config.performance.enableSpatialIndexing) {
      this.spatialIndex.insert({
        x: element.x,
        y: element.y,
        width: element.width || 0,
        height: element.height || 0,
        elementId: id
      });
    }
  }

  private removeFromIndexes(id: string, element: ServerElement): void {
    // Remove from type index
    const typeSet = this.typeIndex.get(element.type);
    if (typeSet) {
      typeSet.delete(id);
    }

    // Remove from spatial index
    if (config.performance.enableSpatialIndexing) {
      this.spatialIndex.remove(id);
    }
  }

  private cleanupInterval: NodeJS.Timeout | null = null;

  private startCleanupInterval(): void {
    this.cleanupInterval = setInterval(() => {
      const now = Date.now();
      const interval = config.performance.memoryCleanupIntervalMinutes * 60 * 1000;

      if (now - this.lastCleanup >= interval) {
        this.forceCleanup();
      }
    }, 60000); // Check every minute
  }

  /**
   * Destroy the storage instance and clean up resources
   */
  destroy(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
  }
}

// Global storage instance
export const elementStorage = new ElementStorage(false);
