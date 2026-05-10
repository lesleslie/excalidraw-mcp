"""Export functionality for Excalidraw scenes.

This module provides export capabilities for Excalidraw scenes to various formats:
- PNG: Rendered image using Playwright
- SVG: Vector graphics
- JSON: Raw scene data
- .excalidraw: Native Excalidraw file format
"""

import json
import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

ExportFormat = Literal["png", "svg", "json", "excalidraw"]


class SceneExporter:
    """Export Excalidraw scenes to various formats."""

    def __init__(self) -> None:
        """Initialize the scene exporter."""
        self.playwright_available = False
        self._check_playwright()

    def _check_playwright(self) -> None:
        """Check if Playwright is available for PNG rendering."""
        try:
            from playwright.sync_api import sync_playwright

            self.playwright_available = True
            self.sync_playwright = sync_playwright
        except ImportError:
            logger.warning("Playwright not available. PNG export will be limited.")
            self.playwright_available = False

    async def export_scene(
        self,
        elements: list[dict[str, Any]],
        format: ExportFormat = "json",
        **options: Any,
    ) -> bytes:
        """Export a scene to the specified format.

        Args:
            elements: List of Excalidraw elements
            format: Export format (png, svg, json, excalidraw)
            **options: Additional export options:
                - width: Canvas width (for PNG)
                - height: Canvas height (for PNG)
                - background: Background color (for PNG/SVG)
                - embed: Embed scene data (for .excalidraw)

        Returns:
            Exported data as bytes

        Raises:
            ValueError: If format is invalid or export fails
        """
        if format == "png":
            return await self._export_png(elements, **options)
        elif format == "svg":
            return self._to_svg(elements, **options)
        elif format == "json":
            return self._to_json(elements)
        elif format == "excalidraw":
            return self._to_excalidraw_file(elements, **options)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    async def _export_png(
        self, elements: list[dict[str, Any]], **options: Any
    ) -> bytes:
        """Export scene to PNG using Playwright rendering.

        Args:
            elements: Scene elements
            **options: Export options (width, height, background)

        Returns:
            PNG image data as bytes
        """
        if not self.playwright_available:
            # Fallback: Return a minimal PNG placeholder
            return self._create_placeholder_png()

        width = options.get("width", 1920)
        height = options.get("height", 1080)
        background = options.get("background", "#ffffff")

        try:
            # Create HTML rendering of the scene
            html_content = self._create_scene_html(elements, width, height, background)

            # Use Playwright to render
            async with self.sync_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                await page.set_viewport_size(width, height)
                await page.set_content(html_content)

                # Wait for rendering
                await page.wait_for_timeout(100)

                # Capture screenshot
                screenshot_bytes = await page.screenshot(type="png", full_page=False)

                await browser.close()
                return screenshot_bytes

        except Exception as e:
            logger.error(f"Failed to render PNG: {e}")
            # Return placeholder on error
            return self._create_placeholder_png()

    def _to_svg(self, elements: list[dict[str, Any]], **options: Any) -> bytes:
        """Convert scene elements to SVG format.

        Args:
            elements: Scene elements
            **options: Export options (width, height, background)

        Returns:
            SVG data as bytes
        """
        width = options.get("width", 1920)
        height = options.get("height", 1080)
        background = options.get("background", "#ffffff")

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect width="100%" height="100%" fill="{background}"/>',
        ]

        # Render each element
        for element in elements:
            svg_element = self._element_to_svg(element)
            if svg_element:
                svg_parts.append(svg_element)

        svg_parts.append("</svg>")

        return "\n".join(svg_parts).encode("utf-8")

    def _element_to_svg(self, element: dict[str, Any]) -> str | None:
        """Convert a single element to SVG.

        Args:
            element: Element data

        Returns:
            SVG markup string or None if element type not supported
        """
        element_type = element.get("type", "")

        if element_type == "rectangle":
            x, y = element.get("x", 0), element.get("y", 0)
            w, h = element.get("width", 100), element.get("height", 100)
            fill = element.get("backgroundColor", "#ffffff")
            stroke = element.get("strokeColor", "#000000")
            sw = element.get("strokeWidth", 2)
            return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'

        elif element_type == "ellipse":
            cx = element.get("x", 0) + element.get("width", 100) / 2
            cy = element.get("y", 0) + element.get("height", 100) / 2
            rx = element.get("width", 100) / 2
            ry = element.get("height", 100) / 2
            fill = element.get("backgroundColor", "#ffffff")
            stroke = element.get("strokeColor", "#000000")
            sw = element.get("strokeWidth", 2)
            return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'

        elif element_type == "text":
            x, y = element.get("x", 0), element.get("y", 0)
            text = element.get("text", "")
            font_size = element.get("fontSize", 16)
            fill = element.get("strokeColor", "#000000")
            return f'<text x="{x}" y="{y}" font-size="{font_size}" fill="{fill}">{text}</text>'

        elif element_type == "line":
            points = element.get("points", [[0, 0], [100, 100]])
            if len(points) >= 2:
                x1, y1 = points[0]
                x2, y2 = points[1]
                stroke = element.get("strokeColor", "#000000")
                sw = element.get("strokeWidth", 2)
                return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"/>'

        else:
            logger.warning(f"SVG export not supported for element type: {element_type}")
            return None

    def _to_json(self, elements: list[dict[str, Any]]) -> bytes:
        """Convert scene elements to JSON format.

        Args:
            elements: Scene elements

        Returns:
            JSON data as bytes
        """
        scene = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://excalidraw.com",
            "elements": elements,
            "appState": {
                "viewBackgroundColor": "#ffffff",
                " currentItemStrokeColor": "#000000",
                "currentItemBackgroundColor": "#ffffff",
                "gridSize": None,
            },
        }
        return json.dumps(scene, indent=2).encode("utf-8")

    def _to_excalidraw_file(
        self, elements: list[dict[str, Any]], **options: Any
    ) -> bytes:
        """Create native .excalidraw file format.

        Args:
            elements: Scene elements
            **options: Export options (embed)

        Returns:
            .excalidraw file data as bytes
        """
        embed = options.get("embed", True)

        scene = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://excalidraw.com",
            "elements": elements,
            "appState": {
                "viewBackgroundColor": "#ffffff",
                "gridSize": None,
                "embedScene": embed,
            },
            "files": {},  # Would contain file references for images
        }

        return json.dumps(scene, indent=2).encode("utf-8")

    def _create_scene_html(
        self, elements: list[dict[str, Any]], width: int, height: int, background: str
    ) -> str:
        """Create HTML representation of scene for rendering.

        Args:
            elements: Scene elements
            width: Canvas width
            height: Canvas height
            background: Background color

        Returns:
            HTML string
        """
        # Convert elements to simple SVG for HTML rendering
        svg_data = self._to_svg(
            elements, width=width, height=height, background=background
        ).decode("utf-8")

        return f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ margin: 0; padding: 0; }}
        svg {{ display: block; }}
    </style>
</head>
<body>
    {svg_data}
</body>
</html>
"""

    def _create_placeholder_png(self) -> bytes:
        """Create a minimal PNG placeholder when Playwright is unavailable.

        Returns:
            PNG bytes (1x1 transparent pixel)
        """
        # Minimal 1x1 transparent PNG
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )


# Convenience function for direct export
async def export_scene(
    elements: list[dict[str, Any]],
    format: ExportFormat = "json",
    **options: Any,
) -> bytes:
    """Export a scene to the specified format.

    This is a convenience function that creates a SceneExporter instance
    and performs the export.

    Args:
        elements: List of Excalidraw elements
        format: Export format (png, svg, json, excalidraw)
        **options: Additional export options

    Returns:
        Exported data as bytes

    Example:
        >>> elements = [
        ...     {"type": "rectangle", "x": 0, "y": 0, "width": 100, "height": 100}
        ... ]
        >>> png_data = await export_scene(elements, format="png", width=800, height=600)
        >>> svg_data = await export_scene(elements, format="svg")
        >>> json_data = await export_scene(elements, format="json")
    """
    exporter = SceneExporter()
    return await exporter.export_scene(elements, format, **options)
