"""Comprehensive tests for SceneExporter covering all export formats and error scenarios."""

import pytest
import json
from excalidraw_mcp.export import SceneExporter, export_scene, ExportFormat


class TestSceneExporterInitialization:
    """Test SceneExporter initialization and setup."""

    def test_exporter_initialization(self):
        """Test that exporter initializes correctly."""
        exporter = SceneExporter()

        assert hasattr(exporter, "playwright_available")
        assert isinstance(exporter.playwright_available, bool)

    def test_exporter_checks_playwright_availability(self):
        """Test that exporter checks for Playwright availability."""
        exporter = SceneExporter()

        # Playwright_available should be a boolean
        assert isinstance(exporter.playwright_available, bool)

        # sync_playwright should be set if available
        if exporter.playwright_available:
            assert hasattr(exporter, "sync_playwright")


class TestJSONExport:
    """Test JSON export functionality."""

    @pytest.fixture
    def exporter(self):
        return SceneExporter()

    @pytest.mark.asyncio
    async def test_export_to_json_basic(self, exporter):
        """Test basic JSON export."""
        elements = [{"type": "rectangle", "x": 10, "y": 20, "width": 100, "height": 50}]

        result = await exporter.export_scene(elements, format="json")

        assert isinstance(result, bytes)
        data = json.loads(result.decode("utf-8"))
        assert data["type"] == "excalidraw"
        assert data["version"] == 2
        assert data["source"] == "https://excalidraw.com"
        assert len(data["elements"]) == 1
        assert data["elements"][0]["type"] == "rectangle"

    @pytest.mark.asyncio
    async def test_export_to_json_multiple_elements(self, exporter):
        """Test JSON export with multiple elements."""
        elements = [
            {"type": "rectangle", "x": 0, "y": 0, "width": 100, "height": 100},
            {"type": "ellipse", "x": 150, "y": 0, "width": 80, "height": 80},
            {"type": "text", "text": "Hello", "x": 50, "y": 150},
        ]

        result = await exporter.export_scene(elements, format="json")

        data = json.loads(result.decode("utf-8"))
        assert len(data["elements"]) == 3

    @pytest.mark.asyncio
    async def test_export_to_json_with_app_state(self, exporter):
        """Test that JSON export includes app state."""
        elements = [{"type": "rectangle"}]

        result = await exporter.export_scene(elements, format="json")

        data = json.loads(result.decode("utf-8"))
        assert "appState" in data
        assert "viewBackgroundColor" in data["appState"]
        # Just check appState exists and has expected structure
        assert "gridSize" in data["appState"]


class TestExcalidrawFileExport:
    """Test .excalidraw file export functionality."""

    @pytest.fixture
    def exporter(self):
        return SceneExporter()

    @pytest.mark.asyncio
    async def test_export_to_excalidraw_format(self, exporter):
        """Test export to .excalidraw format."""
        elements = [{"type": "rectangle", "x": 0, "y": 0}]

        result = await exporter.export_scene(elements, format="excalidraw")

        assert isinstance(result, bytes)
        data = json.loads(result.decode("utf-8"))
        assert data["type"] == "excalidraw"
        assert data["version"] == 2

    @pytest.mark.asyncio
    async def test_excalidraw_export_with_embed(self, exporter):
        """Test .excalidraw export with embed option."""
        elements = [{"type": "ellipse"}]

        result = await exporter.export_scene(elements, format="excalidraw", embed=True)

        data = json.loads(result.decode("utf-8"))
        assert data["appState"]["embedScene"] is True

    @pytest.mark.asyncio
    async def test_excalidraw_export_without_embed(self, exporter):
        """Test .excalidraw export without embed option."""
        elements = [{"type": "rectangle"}]

        result = await exporter.export_scene(elements, format="excalidraw", embed=False)

        data = json.loads(result.decode("utf-8"))
        assert data["appState"]["embedScene"] is False

    @pytest.mark.asyncio
    async def test_excalidraw_export_includes_files(self, exporter):
        """Test that .excalidraw export includes files dict."""
        elements = [{"type": "image", "fileId": "img123"}]

        result = await exporter.export_scene(elements, format="excalidraw")

        data = json.loads(result.decode("utf-8"))
        assert "files" in data
        assert isinstance(data["files"], dict)


class TestSVGExport:
    """Test SVG export functionality."""

    @pytest.fixture
    def exporter(self):
        return SceneExporter()

    @pytest.mark.asyncio
    async def test_export_to_svg_basic(self, exporter):
        """Test basic SVG export."""
        elements = [{"type": "rectangle", "x": 10, "y": 20, "width": 100, "height": 50}]

        result = await exporter.export_scene(elements, format="svg")

        assert isinstance(result, bytes)
        svg_text = result.decode("utf-8")
        assert "<svg" in svg_text
        assert "</svg>" in svg_text
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg_text

    @pytest.mark.asyncio
    async def test_svg_export_with_custom_dimensions(self, exporter):
        """Test SVG export with custom dimensions."""
        elements = [{"type": "rectangle"}]

        result = await exporter.export_scene(
            elements, format="svg", width=800, height=600
        )

        svg_text = result.decode("utf-8")
        assert 'width="800"' in svg_text
        assert 'height="600"' in svg_text
        assert 'viewBox="0 0 800 600"' in svg_text

    @pytest.mark.asyncio
    async def test_svg_export_with_background(self, exporter):
        """Test SVG export with custom background."""
        elements = [{"type": "rectangle"}]

        result = await exporter.export_scene(
            elements, format="svg", background="#f0f0f0"
        )

        svg_text = result.decode("utf-8")
        assert '<rect width="100%" height="100%" fill="#f0f0f0"/>' in svg_text

    @pytest.mark.asyncio
    async def test_svg_export_rectangle_element(self, exporter):
        """Test SVG export of rectangle element."""
        elements = [
            {
                "type": "rectangle",
                "x": 10,
                "y": 20,
                "width": 100,
                "height": 50,
                "backgroundColor": "#ff0000",
                "strokeColor": "#000000",
                "strokeWidth": 2,
            }
        ]

        result = await exporter.export_scene(elements, format="svg")

        svg_text = result.decode("utf-8")
        assert '<rect x="10" y="20" width="100" height="50"' in svg_text
        assert 'fill="#ff0000"' in svg_text
        assert 'stroke="#000000"' in svg_text
        assert 'stroke-width="2"' in svg_text

    @pytest.mark.asyncio
    async def test_svg_export_ellipse_element(self, exporter):
        """Test SVG export of ellipse element."""
        elements = [
            {
                "type": "ellipse",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 80,
                "backgroundColor": "#00ff00",
            }
        ]

        result = await exporter.export_scene(elements, format="svg")

        svg_text = result.decode("utf-8")
        assert "<ellipse" in svg_text
        # Allow for float formatting (50 or 50.0)
        assert 'cx="50' in svg_text  # x + width/2
        assert 'cy="40' in svg_text  # y + height/2
        assert 'rx="50' in svg_text  # width/2
        assert 'ry="40' in svg_text  # height/2

    @pytest.mark.asyncio
    async def test_svg_export_text_element(self, exporter):
        """Test SVG export of text element."""
        elements = [
            {
                "type": "text",
                "text": "Hello World",
                "x": 50,
                "y": 100,
                "fontSize": 20,
                "strokeColor": "#0000ff",
            }
        ]

        result = await exporter.export_scene(elements, format="svg")

        svg_text = result.decode("utf-8")
        assert '<text x="50" y="100"' in svg_text
        assert 'font-size="20"' in svg_text
        assert 'fill="#0000ff"' in svg_text
        assert "Hello World" in svg_text

    @pytest.mark.asyncio
    async def test_svg_export_line_element(self, exporter):
        """Test SVG export of line element."""
        elements = [
            {
                "type": "line",
                "points": [[0, 0], [100, 100]],
                "strokeColor": "#ff0000",
                "strokeWidth": 3,
            }
        ]

        result = await exporter.export_scene(elements, format="svg")

        svg_text = result.decode("utf-8")
        assert '<line x1="0" y1="0" x2="100" y2="100"' in svg_text
        assert 'stroke="#ff0000"' in svg_text
        assert 'stroke-width="3"' in svg_text

    @pytest.mark.asyncio
    async def test_svg_export_unsupported_element(self, exporter):
        """Test SVG export with unsupported element type."""
        elements = [{"type": "unsupported", "x": 0, "y": 0}]

        result = await exporter.export_scene(elements, format="svg")

        # Should still create SVG but skip unsupported element
        svg_text = result.decode("utf-8")
        assert "<svg" in svg_text
        assert "</svg>" in svg_text

    @pytest.mark.asyncio
    async def test_svg_export_multiple_elements(self, exporter):
        """Test SVG export with multiple elements."""
        elements = [
            {"type": "rectangle", "x": 0, "y": 0, "width": 50, "height": 50},
            {"type": "ellipse", "x": 100, "y": 0, "width": 50, "height": 50},
            {"type": "text", "text": "Test", "x": 50, "y": 100},
        ]

        result = await exporter.export_scene(elements, format="svg")

        svg_text = result.decode("utf-8")
        assert "<rect" in svg_text
        assert "<ellipse" in svg_text
        assert "<text" in svg_text


class TestPNGExport:
    """Test PNG export functionality."""

    @pytest.fixture
    def exporter(self):
        return SceneExporter()

    @pytest.mark.asyncio
    async def test_export_to_png_placeholder(self, exporter):
        """Test PNG export returns placeholder when Playwright unavailable."""
        elements = [{"type": "rectangle"}]

        # If Playwright is not available, should return placeholder
        if not exporter.playwright_available:
            result = await exporter.export_scene(elements, format="png")

            assert isinstance(result, bytes)
            # PNG signature
            assert result[:8] == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.asyncio
    async def test_png_export_placeholder_is_valid_png(self, exporter):
        """Test that placeholder PNG has valid PNG structure."""
        elements = [{"type": "rectangle"}]

        result = await exporter.export_scene(elements, format="png")

        # Check PNG signature
        assert result.startswith(b"\x89PNG\r\n\x1a\n")
        # Check PNG end chunk
        assert result.endswith(b"IEND\xaeB`\x82")


class TestHTMLSceneCreation:
    """Test HTML scene creation for PNG rendering."""

    @pytest.fixture
    def exporter(self):
        return SceneExporter()

    def test_create_scene_html_basic(self, exporter):
        """Test basic HTML scene creation."""
        elements = [{"type": "rectangle"}]

        html = exporter._create_scene_html(elements, 800, 600, "#ffffff")

        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "<body>" in html
        assert "</body>" in html
        assert "</html>" in html
        assert "<svg" in html

    def test_create_scene_html_includes_svg(self, exporter):
        """Test that HTML scene includes SVG content."""
        elements = [{"type": "rectangle", "x": 10, "y": 20}]

        html = exporter._create_scene_html(elements, 800, 600, "#ffffff")

        assert "<svg" in html
        assert "</svg>" in html

    def test_create_scene_html_has_styles(self, exporter):
        """Test that HTML scene has inline styles."""
        elements = [{"type": "rectangle"}]

        html = exporter._create_scene_html(elements, 800, 600, "#ffffff")

        assert "<style>" in html
        assert "margin: 0" in html
        assert "padding: 0" in html


class TestPlaceholderPNG:
    """Test placeholder PNG creation."""

    @pytest.fixture
    def exporter(self):
        return SceneExporter()

    def test_placeholder_png_structure(self, exporter):
        """Test placeholder PNG has correct structure."""
        placeholder = exporter._create_placeholder_png()

        assert isinstance(placeholder, bytes)
        assert len(placeholder) > 0

    def test_placeholder_png_signature(self, exporter):
        """Test placeholder PNG has valid PNG signature."""
        placeholder = exporter._create_placeholder_png()

        # PNG signature: 89 50 4E 47 0D 0A 1A 0A
        assert placeholder[0:8] == b"\x89PNG\r\n\x1a\n"

    def test_placeholder_png_has_iend_chunk(self, exporter):
        """Test placeholder PNG ends with IEND chunk."""
        placeholder = exporter._create_placeholder_png()

        # IEND chunk: 49 45 4E 44 AE 42 60 82
        assert b"IEND" in placeholder
        assert placeholder.endswith(b"\xaeB`\x82")


class TestElementToSVGConversion:
    """Test individual element to SVG conversion."""

    @pytest.fixture
    def exporter(self):
        return SceneExporter()

    def test_rectangle_to_svg(self, exporter):
        """Test rectangle element to SVG conversion."""
        element = {
            "type": "rectangle",
            "x": 10,
            "y": 20,
            "width": 100,
            "height": 50,
            "backgroundColor": "#ff0000",
            "strokeColor": "#000000",
            "strokeWidth": 2,
        }

        svg = exporter._element_to_svg(element)

        assert svg is not None
        assert "<rect" in svg
        assert 'x="10"' in svg
        assert 'y="20"' in svg
        assert 'width="100"' in svg
        assert 'height="50"' in svg

    def test_ellipse_to_svg(self, exporter):
        """Test ellipse element to SVG conversion."""
        element = {
            "type": "ellipse",
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 80,
            "backgroundColor": "#00ff00",
        }

        svg = exporter._element_to_svg(element)

        assert svg is not None
        assert "<ellipse" in svg

    def test_text_to_svg(self, exporter):
        """Test text element to SVG conversion."""
        element = {
            "type": "text",
            "text": "Hello",
            "x": 50,
            "y": 100,
            "fontSize": 20,
            "strokeColor": "#0000ff",
        }

        svg = exporter._element_to_svg(element)

        assert svg is not None
        assert "<text" in svg
        assert "Hello" in svg

    def test_line_to_svg(self, exporter):
        """Test line element to SVG conversion."""
        element = {
            "type": "line",
            "points": [[0, 0], [100, 100]],
            "strokeColor": "#ff0000",
            "strokeWidth": 2,
        }

        svg = exporter._element_to_svg(element)

        assert svg is not None
        assert "<line" in svg

    def test_unsupported_element_returns_none(self, exporter):
        """Test unsupported element type returns None."""
        element = {"type": "unsupported", "x": 0, "y": 0}

        svg = exporter._element_to_svg(element)

        assert svg is None

    def test_line_with_insufficient_points(self, exporter):
        """Test line with insufficient points returns None."""
        element = {"type": "line", "points": [[0, 0]]}

        svg = exporter._element_to_svg(element)

        assert svg is None


class TestErrorScenarios:
    """Test error handling and edge cases."""

    @pytest.fixture
    def exporter(self):
        return SceneExporter()

    @pytest.mark.asyncio
    async def test_invalid_format_raises_error(self, exporter):
        """Test that invalid format raises ValueError."""
        elements = [{"type": "rectangle"}]

        with pytest.raises(ValueError, match="Unsupported export format"):
            await exporter.export_scene(elements, format="invalid")

    @pytest.mark.asyncio
    async def test_export_empty_elements_list(self, exporter):
        """Test export with empty elements list."""
        elements = []

        result = await exporter.export_scene(elements, format="json")

        data = json.loads(result.decode("utf-8"))
        assert data["elements"] == []

    @pytest.mark.asyncio
    async def test_export_element_missing_optional_fields(self, exporter):
        """Test export with elements missing optional fields."""
        elements = [{"type": "rectangle"}]  # Only required field

        result = await exporter.export_scene(elements, format="json")

        # Should not raise error
        assert result is not None

    def test_element_to_svg_missing_properties(self, exporter):
        """Test element to SVG with missing properties."""
        element = {"type": "rectangle"}  # Missing x, y, width, height

        svg = exporter._element_to_svg(element)

        # Should use defaults
        assert svg is not None
        assert "<rect" in svg


class TestConvenienceFunction:
    """Test the export_scene convenience function."""

    @pytest.mark.asyncio
    async def test_export_scene_convenience_json(self):
        """Test convenience function for JSON export."""
        elements = [{"type": "rectangle"}]

        result = await export_scene(elements, format="json")

        assert isinstance(result, bytes)
        assert b'"type": "excalidraw"' in result

    @pytest.mark.asyncio
    async def test_export_scene_convenience_svg(self):
        """Test convenience function for SVG export."""
        elements = [{"type": "rectangle"}]

        result = await export_scene(elements, format="svg")

        assert isinstance(result, bytes)
        assert b"<svg" in result

    @pytest.mark.asyncio
    async def test_export_scene_with_options(self):
        """Test convenience function with export options."""
        elements = [{"type": "rectangle"}]

        result = await export_scene(
            elements,
            format="svg",
            width=1920,
            height=1080,
            background="#f0f0f0"
        )

        svg_text = result.decode("utf-8")
        assert 'width="1920"' in svg_text
        assert 'height="1080"' in svg_text
        assert 'fill="#f0f0f0"' in svg_text


class TestExportFormatType:
    """Test ExportFormat type validation."""

    def test_export_format_is_literal(self):
        """Test that ExportFormat is a proper Literal type."""
        valid_formats = ["png", "svg", "json", "excalidraw"]

        for fmt in valid_formats:
            assert fmt in ExportFormat.__args__


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def exporter(self):
        return SceneExporter()

    @pytest.mark.asyncio
    async def test_very_large_dimensions(self, exporter):
        """Test export with very large dimensions."""
        elements = [{"type": "rectangle"}]

        result = await exporter.export_scene(
            elements, format="svg", width=100000, height=100000
        )

        svg_text = result.decode("utf-8")
        assert 'width="100000"' in svg_text
        assert 'height="100000"' in svg_text

    @pytest.mark.asyncio
    async def test_zero_dimensions(self, exporter):
        """Test export with zero dimensions."""
        elements = [{"type": "rectangle"}]

        result = await exporter.export_scene(
            elements, format="svg", width=0, height=0
        )

        # Should still work
        assert result is not None

    @pytest.mark.asyncio
    async def test_special_characters_in_text(self, exporter):
        """Test export with special characters in text."""
        elements = [{"type": "text", "text": "Hello <>&\"'", "x": 0, "y": 0}]

        result = await exporter.export_scene(elements, format="svg")

        # Should handle special characters
        assert result is not None
        assert "Hello" in result.decode("utf-8")

    @pytest.mark.asyncio
    async def test_unicode_in_text(self, exporter):
        """Test export with Unicode characters."""
        elements = [{"type": "text", "text": "Hello 世界 🌍", "x": 0, "y": 0}]

        result = await exporter.export_scene(elements, format="svg")

        # Should handle Unicode
        assert result is not None
        svg_text = result.decode("utf-8")
        assert "Hello" in svg_text

    @pytest.mark.asyncio
    async def test_many_elements(self, exporter):
        """Test export with many elements."""
        elements = [
            {"type": "rectangle", "x": i * 10, "y": 0}
            for i in range(100)
        ]

        result = await exporter.export_scene(elements, format="json")

        data = json.loads(result.decode("utf-8"))
        assert len(data["elements"]) == 100
