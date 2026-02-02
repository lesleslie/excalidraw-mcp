"""Playwright-based export service for high-fidelity SVG/PNG exports.

Uses a headless browser to leverage Excalidraw's native export functions,
producing identical output to the browser UI.
"""

import asyncio
import base64
import logging
from typing import Any

from .config import config

logger = logging.getLogger(__name__)

# Playwright is optional - only needed for export
try:
    from playwright.async_api import Browser, Page, async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None  # type: ignore
    Page = None  # type: ignore
    async_playwright = None  # type: ignore


class ExportService:
    """Manages a persistent browser instance for high-fidelity exports.
    
    Uses Playwright to run Excalidraw's native exportToSvg/exportToBlob
    functions in a headless browser, producing pixel-perfect output.
    """

    def __init__(self) -> None:
        self._browser: Any = None
        self._page: Any = None
        self._playwright: Any = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_browser(self) -> None:
        """Lazily initialize browser on first use."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright not installed. Install with: pip install playwright && playwright install chromium"
            )

        async with self._lock:
            if self._initialized:
                return

            logger.info("Initializing Playwright browser for exports...")
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            self._page = await self._browser.new_page()

            # Navigate to the frontend and wait for Excalidraw to load
            frontend_url = config.server.express_url
            logger.info(f"Loading Excalidraw frontend at {frontend_url}")
            
            await self._page.goto(frontend_url, wait_until="networkidle")
            
            # Wait for Excalidraw export API to be ready
            await self._page.wait_for_function(
                "() => window.__excalidrawExport && window.__excalidrawExport.isReady()",
                timeout=30000,
            )
            
            self._initialized = True
            logger.info("Export service ready")

    async def _refresh_elements(self) -> None:
        """Refresh elements from backend to ensure latest state."""
        # Trigger a reload of elements from the API
        await self._page.evaluate("""
            async () => {
                const response = await fetch('/api/elements');
                const data = await response.json();
                if (data.success && data.elements) {
                    // Elements are already loaded via WebSocket sync
                    // Just wait a bit for any pending updates
                    await new Promise(r => setTimeout(r, 100));
                }
            }
        """)

    async def _load_elements_from_file(self, file_path: str) -> None:
        """Load elements from an .excalidraw file into the canvas."""
        import json
        from pathlib import Path
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        
        # Extract elements from the Excalidraw file format
        elements = data.get("elements", [])
        app_state = data.get("appState", {})
        
        # Load elements into the canvas via the export API
        await self._page.evaluate("""
            (data) => {
                if (!window.__excalidrawExport) {
                    throw new Error('Excalidraw export API not available');
                }
                window.__excalidrawExport.loadElements(data.elements, data.appState);
            }
        """, {"elements": elements, "appState": app_state})
        
        logger.info(f"Loaded {len(elements)} elements from {file_path}")

    async def export_svg(self, file_path: str, background_color: str = "#ffffff") -> str:
        """Export an .excalidraw file to SVG.
        
        Args:
            file_path: Path to .excalidraw file to export.
            background_color: Background color (default: #ffffff white).
        
        Returns:
            SVG markup as a string.
        """
        await self._ensure_browser()
        await self._load_elements_from_file(file_path)

        svg_content: str = await self._page.evaluate("""
            async (bgColor) => {
                if (!window.__excalidrawExport) {
                    throw new Error('Excalidraw export API not available');
                }
                return await window.__excalidrawExport.toSvg(bgColor);
            }
        """, background_color)

        logger.info(f"Exported SVG ({len(svg_content)} bytes)")
        return svg_content

    async def export_png(self, file_path: str, background_color: str = "#ffffff") -> bytes:
        """Export an .excalidraw file to PNG.
        
        Args:
            file_path: Path to .excalidraw file to export.
            background_color: Background color (default: #ffffff white).
        
        Returns:
            PNG image as bytes.
        """
        await self._ensure_browser()
        await self._load_elements_from_file(file_path)

        data_url: str = await self._page.evaluate("""
            async (bgColor) => {
                if (!window.__excalidrawExport) {
                    throw new Error('Excalidraw export API not available');
                }
                return await window.__excalidrawExport.toPng(bgColor);
            }
        """, background_color)

        # Parse data URL: data:image/png;base64,<base64data>
        if data_url.startswith("data:image/png;base64,"):
            base64_data = data_url.split(",", 1)[1]
            png_bytes = base64.b64decode(base64_data)
            logger.info(f"Exported PNG ({len(png_bytes)} bytes)")
            return png_bytes
        else:
            raise ValueError("Unexpected data URL format from PNG export")

    async def get_element_count(self) -> int:
        """Get the current element count from the canvas."""
        await self._ensure_browser()
        
        count: int = await self._page.evaluate("""
            () => {
                if (!window.__excalidrawExport) {
                    return 0;
                }
                return window.__excalidrawExport.getElements().length;
            }
        """)
        return count

    async def close(self) -> None:
        """Close browser and cleanup resources."""
        async with self._lock:
            if self._browser:
                await self._browser.close()
                self._browser = None
                self._page = None

            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            self._initialized = False
            logger.info("Export service closed")

    @property
    def is_available(self) -> bool:
        """Check if Playwright is available for exports."""
        return PLAYWRIGHT_AVAILABLE


# Singleton instance
export_service = ExportService()
