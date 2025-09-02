/**
 * Delta compression utilities for efficient WebSocket updates
 */

import { ServerElement } from '../types';

export interface ElementDelta {
  id: string;
  version: number;
  changes: Partial<ServerElement>;
  timestamp: string;
}

export interface DeltaCompressionResult {
  hasDelta: boolean;
  delta?: ElementDelta;
  fullElement?: ServerElement;
}

/**
 * Calculate the difference between two elements
 */
export function calculateElementDelta(
  oldElement: ServerElement | undefined,
  newElement: ServerElement
): DeltaCompressionResult {
  // If no old element, send full element
  if (!oldElement) {
    return {
      hasDelta: false,
      fullElement: newElement
    };
  }

  // Calculate changes
  const changes: Partial<ServerElement> = {};
  let hasChanges = false;

  // Check each property for changes
  const properties: (keyof ServerElement)[] = [
    'type', 'x', 'y', 'width', 'height', 'text', 'strokeColor',
    'backgroundColor', 'strokeWidth', 'opacity', 'roughness',
    'fontSize', 'fontFamily', 'locked'
  ];

  for (const prop of properties) {
    if (oldElement[prop] !== newElement[prop]) {
      (changes as any)[prop] = newElement[prop];
      hasChanges = true;
    }
  }

  // Always include version and timestamp in delta
  changes.version = newElement.version;
  changes.updatedAt = newElement.updatedAt;

  // If significant changes, send delta; otherwise send full element
  if (hasChanges && Object.keys(changes).length < properties.length / 2) {
    return {
      hasDelta: true,
      delta: {
        id: newElement.id,
        version: newElement.version ?? 1,
        changes,
        timestamp: newElement.updatedAt ?? new Date().toISOString()
      }
    };
  } else {
    return {
      hasDelta: false,
      fullElement: newElement
    };
  }
}

/**
 * Apply a delta to an existing element
 */
export function applyElementDelta(
  baseElement: ServerElement,
  delta: ElementDelta
): ServerElement {
  // Verify version compatibility
  if (delta.version <= (baseElement.version ?? 0)) {
    throw new Error(`Delta version ${delta.version} is not newer than base version ${baseElement.version}`);
  }

  // Apply changes
  const updatedElement: ServerElement = {
    ...baseElement,
    ...delta.changes,
    id: baseElement.id, // Ensure ID doesn't change
    version: delta.version,
    updatedAt: delta.timestamp
  };

  return updatedElement;
}

/**
 * Compress multiple element updates into minimal deltas
 */
export function compressElementUpdates(
  oldElements: Map<string, ServerElement>,
  newElements: Map<string, ServerElement>
): {
  deltas: ElementDelta[];
  fullElements: ServerElement[];
  deletedIds: string[];
} {
  const deltas: ElementDelta[] = [];
  const fullElements: ServerElement[] = [];
  const deletedIds: string[] = [];

  // Find deleted elements
  for (const oldId of oldElements.keys()) {
    if (!newElements.has(oldId)) {
      deletedIds.push(oldId);
    }
  }

  // Process updated and new elements
  for (const [newId, newElement] of newElements.entries()) {
    const oldElement = oldElements.get(newId);
    const result = calculateElementDelta(oldElement, newElement);

    if (result.hasDelta && result.delta) {
      deltas.push(result.delta);
    } else if (result.fullElement) {
      fullElements.push(result.fullElement);
    }
  }

  return { deltas, fullElements, deletedIds };
}

/**
 * Validate delta integrity
 */
export function validateDelta(delta: ElementDelta): boolean {
  // Check required fields
  if (!delta.id || !delta.version || !delta.timestamp || !delta.changes) {
    return false;
  }

  // Check version is positive
  if (delta.version <= 0) {
    return false;
  }

  // Check timestamp format
  try {
    new Date(delta.timestamp);
  } catch {
    return false;
  }

  // Check changes object is not empty
  if (Object.keys(delta.changes).length === 0) {
    return false;
  }

  return true;
}

/**
 * Merge multiple deltas for the same element
 */
export function mergeDeltas(deltas: ElementDelta[]): ElementDelta | null {
  if (deltas.length === 0) return null;
  if (deltas.length === 1) return deltas[0] ?? null;

  // Sort deltas by version
  const sortedDeltas = deltas.sort((a, b) => a.version - b.version);

  // Verify deltas are sequential
  for (let i = 1; i < sortedDeltas.length; i++) {
    if (sortedDeltas[i]?.version !== (sortedDeltas[i - 1]?.version ?? 0) + 1) {
      throw new Error('Cannot merge non-sequential deltas');
    }
  }

  // Merge changes
  const mergedChanges: Partial<ServerElement> = {};
  for (const delta of sortedDeltas) {
    if (delta) {
      Object.assign(mergedChanges, delta.changes);
    }
  }

  const firstDelta = sortedDeltas[0];
  const lastDelta = sortedDeltas[sortedDeltas.length - 1];

  if (!firstDelta || !lastDelta) {
    throw new Error('Cannot merge empty deltas');
  }

  return {
    id: firstDelta.id,
    version: lastDelta.version,
    changes: mergedChanges,
    timestamp: lastDelta.timestamp
  };
}

/**
 * Calculate compression ratio for deltas vs full elements
 */
export function calculateCompressionRatio(
  fullElementSize: number,
  deltaSize: number
): number {
  if (fullElementSize === 0) return 0;
  return 1 - (deltaSize / fullElementSize);
}

/**
 * Serialize delta for transmission
 */
export function serializeDelta(delta: ElementDelta): string {
  return JSON.stringify(delta);
}

/**
 * Deserialize delta from transmission
 */
export function deserializeDelta(deltaString: string): ElementDelta {
  try {
    const delta = JSON.parse(deltaString) as ElementDelta;

    if (!validateDelta(delta)) {
      throw new Error('Invalid delta format');
    }

    return delta;
  } catch (error) {
    throw new Error(`Failed to deserialize delta: ${error instanceof Error ? error.message : String(error)}`);
  }
}

/**
 * Create a full element snapshot from base + deltas
 */
export function reconstructElement(
  baseElement: ServerElement,
  deltas: ElementDelta[]
): ServerElement {
  let currentElement = baseElement;

  // Sort deltas by version
  const sortedDeltas = deltas.sort((a, b) => a.version - b.version);

  for (const delta of sortedDeltas) {
    currentElement = applyElementDelta(currentElement, delta);
  }

  return currentElement;
}

/**
 * Delta history management for conflict resolution
 */
export class DeltaHistory {
  private history: Map<string, ElementDelta[]> = new Map();
  private maxHistoryLength = 100;

  addDelta(delta: ElementDelta): void {
    if (!this.history.has(delta.id)) {
      this.history.set(delta.id, []);
    }

    const elementHistory = this.history.get(delta.id)!;
    elementHistory.push(delta);

    // Limit history size
    if (elementHistory.length > this.maxHistoryLength) {
      elementHistory.shift();
    }
  }

  getHistory(elementId: string): ElementDelta[] {
    return this.history.get(elementId) || [];
  }

  getLastDelta(elementId: string): ElementDelta | undefined {
    const elementHistory = this.history.get(elementId);
    return elementHistory?.[elementHistory.length - 1];
  }

  clearHistory(elementId: string): void {
    this.history.delete(elementId);
  }

  clearAllHistory(): void {
    this.history.clear();
  }

  getStats(): { totalElements: number; totalDeltas: number; memoryUsage: number } {
    let totalDeltas = 0;
    for (const history of this.history.values()) {
      totalDeltas += history.length;
    }

    return {
      totalElements: this.history.size,
      totalDeltas,
      memoryUsage: totalDeltas * 1024 // Rough estimate
    };
  }
}
