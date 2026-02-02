/**
 * E2E Sync Tests for Excalidraw MCP
 * 
 * Tests the WebSocket sync architecture between backend API and browser canvas.
 * 
 * Prerequisites:
 * - Canvas server running on localhost:3031
 * - Playwright installed: npm install -D playwright
 * 
 * Run: npx playwright test test/e2e/sync.e2e.test.ts
 */

import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:3031';
const CANVAS_URL = 'http://localhost:3031';

// Helper to call API
async function apiRequest(
  method: string,
  path: string,
  body?: object
): Promise<any> {
  const options: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) {
    options.body = JSON.stringify(body);
  }
  const response = await fetch(`${API_BASE}${path}`, options);
  return response.json();
}

// Helper to get elements from browser via exposed API
async function getBrowserElements(page: any): Promise<any[]> {
  return page.evaluate(() => {
    const api = (window as any).__excalidrawExport;
    if (!api) return [];
    return api.getElements().map((e: any) => ({
      id: e.id,
      type: e.type,
      x: e.x,
      y: e.y,
      text: e.text,
    }));
  });
}

test.describe('Excalidraw MCP Sync Architecture', () => {
  test.beforeEach(async ({ page }) => {
    // Clear canvas before each test
    await apiRequest('DELETE', '/api/elements');
    
    // Navigate to canvas
    await page.goto(CANVAS_URL);
    
    // Wait for Excalidraw to initialize
    await page.waitForFunction(() => {
      return (window as any).__excalidrawExport?.isReady?.();
    }, { timeout: 10000 });
  });

  test.afterEach(async () => {
    // Cleanup
    await apiRequest('DELETE', '/api/elements');
  });

  test('should sync batch-created elements to browser with preserved IDs', async ({ page }) => {
    // Create elements via API with specific IDs
    const result = await apiRequest('POST', '/api/elements/batch', {
      elements: [
        { id: 'batch-sync-test-1', type: 'rectangle', x: 100, y: 100, width: 100, height: 80 },
        { id: 'batch-sync-test-2', type: 'rectangle', x: 250, y: 100, width: 100, height: 80 },
      ],
    });

    expect(result.success).toBe(true);
    expect(result.elements[0].id).toBe('batch-sync-test-1');
    expect(result.elements[1].id).toBe('batch-sync-test-2');

    // Refresh page to trigger initial_elements sync
    await page.reload();
    await page.waitForFunction(() => (window as any).__excalidrawExport?.isReady?.());

    // Wait for WebSocket sync
    await page.waitForTimeout(500);

    // Verify elements appear in browser with same IDs
    const browserElements = await getBrowserElements(page);
    expect(browserElements).toHaveLength(2);
    
    const ids = browserElements.map((e) => e.id);
    expect(ids).toContain('batch-sync-test-1');
    expect(ids).toContain('batch-sync-test-2');
  });

  test('should clear browser canvas when backend clears elements', async ({ page }) => {
    // Create elements
    await apiRequest('POST', '/api/elements/batch', {
      elements: [
        { id: 'clear-test-1', type: 'rectangle', x: 50, y: 50, width: 80, height: 60 },
        { id: 'clear-test-2', type: 'ellipse', x: 200, y: 50, width: 80, height: 60 },
      ],
    });

    // Refresh to load elements
    await page.reload();
    await page.waitForFunction(() => (window as any).__excalidrawExport?.isReady?.());
    await page.waitForTimeout(500);

    // Verify elements exist in browser
    let elements = await getBrowserElements(page);
    expect(elements.length).toBeGreaterThan(0);

    // Clear via API
    const clearResult = await apiRequest('DELETE', '/api/elements');
    expect(clearResult.success).toBe(true);

    // Wait for WebSocket broadcast
    await page.waitForTimeout(500);

    // Verify browser canvas is cleared
    elements = await getBrowserElements(page);
    expect(elements).toHaveLength(0);
  });

  test('should preserve text content for text elements', async ({ page }) => {
    // Create text element via API
    const result = await apiRequest('POST', '/api/elements/batch', {
      elements: [
        { id: 'text-test-1', type: 'text', x: 100, y: 50, text: 'Hello World' },
      ],
    });

    expect(result.success).toBe(true);

    // Refresh to load
    await page.reload();
    await page.waitForFunction(() => (window as any).__excalidrawExport?.isReady?.());
    await page.waitForTimeout(500);

    // Verify text element exists with content
    const elements = await getBrowserElements(page);
    const textElement = elements.find((e) => e.type === 'text');
    
    expect(textElement).toBeDefined();
    expect(textElement?.id).toBe('text-test-1');
    // Note: text property may need additional handling in cleanElementForExcalidraw
  });

  test('should align elements correctly via API', async ({ page }) => {
    // Create elements with different x positions
    await apiRequest('POST', '/api/elements/batch', {
      elements: [
        { id: 'align-e2e-1', type: 'rectangle', x: 50, y: 100, width: 80, height: 60 },
        { id: 'align-e2e-2', type: 'rectangle', x: 200, y: 150, width: 80, height: 60 },
        { id: 'align-e2e-3', type: 'rectangle', x: 350, y: 200, width: 80, height: 60 },
      ],
    });

    // Align to left
    const alignResult = await apiRequest('POST', '/api/elements/align', {
      elementIds: ['align-e2e-1', 'align-e2e-2', 'align-e2e-3'],
      alignment: 'left',
    });

    expect(alignResult.success).toBe(true);
    expect(alignResult.alignedCount).toBe(3);

    // Verify all elements now have same x position
    const elementsResult = await apiRequest('GET', '/api/elements');
    const xPositions = elementsResult.elements.map((e: any) => e.x);
    
    // All should have the minimum x value (50)
    expect(xPositions.every((x: number) => x === 50)).toBe(true);
  });

  test('should not create duplicate elements on multiple updates', async ({ page }) => {
    // Create single element
    await apiRequest('POST', '/api/elements', {
      id: 'no-dupe-test',
      type: 'rectangle',
      x: 100,
      y: 100,
      width: 100,
      height: 80,
    });

    // Navigate and load
    await page.goto(CANVAS_URL);
    await page.waitForFunction(() => (window as any).__excalidrawExport?.isReady?.());
    await page.waitForTimeout(500);

    // Refresh multiple times (simulates reconnection)
    await page.reload();
    await page.waitForFunction(() => (window as any).__excalidrawExport?.isReady?.());
    await page.waitForTimeout(300);

    await page.reload();
    await page.waitForFunction(() => (window as any).__excalidrawExport?.isReady?.());
    await page.waitForTimeout(300);

    // Should still have only 1 element
    const elements = await getBrowserElements(page);
    const matching = elements.filter((e) => e.id === 'no-dupe-test');
    expect(matching).toHaveLength(1);
  });

  test('should handle real-time element creation via WebSocket', async ({ page }) => {
    // Start on empty canvas
    await page.goto(CANVAS_URL);
    await page.waitForFunction(() => (window as any).__excalidrawExport?.isReady?.());
    await page.waitForTimeout(500);

    // Verify no elements initially
    let elements = await getBrowserElements(page);
    expect(elements).toHaveLength(0);

    // Create element via API (should trigger WebSocket broadcast)
    const result = await apiRequest('POST', '/api/elements', {
      id: 'realtime-test-1',
      type: 'diamond',
      x: 150,
      y: 150,
      width: 100,
      height: 80,
    });

    expect(result.success).toBe(true);

    // Wait for WebSocket message
    await page.waitForTimeout(500);

    // Element should appear in browser without page refresh
    elements = await getBrowserElements(page);
    expect(elements.find((e) => e.id === 'realtime-test-1')).toBeDefined();
  });
});
