"""Tests for Excalidraw element types and export functionality."""

import pytest

from excalidraw_mcp.element_factory import ElementFactory
from excalidraw_mcp.export import SceneExporter, export_scene


@pytest.mark.asyncio
async def test_export_scene_to_json():
    """Test exporting scene to JSON format."""
    elements = [
        {"type": "rectangle", "x": 10, "y": 20, "width": 100, "height": 50}
    ]

    json_data = await export_scene(elements, format="json")

    assert json_data is not None
    assert b'"type": "excalidraw"' in json_data
    assert b'"elements"' in json_data
    assert b'"rectangle"' in json_data


@pytest.mark.asyncio
async def test_export_scene_to_svg():
    """Test exporting scene to SVG format."""
    elements = [
        {
            "type": "rectangle",
            "x": 10,
            "y": 20,
            "width": 100,
            "height": 50,
            "backgroundColor": "#ff0000",
            "strokeColor": "#000000",
        }
    ]

    svg_data = await export_scene(elements, format="svg", width=800, height=600)

    assert svg_data is not None
    assert b"<svg" in svg_data
    assert b"</svg>" in svg_data
    assert b'<rect x="10" y="20" width="100" height="50"' in svg_data
    assert b'fill="#ff0000"' in svg_data


@pytest.mark.asyncio
async def test_export_scene_to_excalidraw():
    """Test exporting scene to .excalidraw format."""
    elements = [{"type": "ellipse", "x": 0, "y": 0, "width": 200, "height": 150}]

    excalidraw_data = await export_scene(elements, format="excalidraw")

    assert excalidraw_data is not None
    assert b'"type": "excalidraw"' in excalidraw_data
    assert b'"version": 2' in excalidraw_data
    assert b'"source": "https://excalidraw.com"' in excalidraw_data


@pytest.mark.asyncio
async def test_export_scene_to_png_placeholder():
    """Test PNG export with placeholder when Playwright unavailable."""
    elements = [{"type": "text", "x": 50, "y": 50, "text": "Hello"}]

    png_data = await export_scene(elements, format="png", width=800, height=600)

    # Should return PNG (either rendered or placeholder)
    assert png_data is not None
    assert len(png_data) > 0
    # PNG signature
    assert png_data[:8] == b"\x89PNG\r\n\x1a\n"


def test_element_factory_creates_all_types():
    """Test that ElementFactory supports all required element types."""
    factory = ElementFactory()

    # All element types that should be supported
    element_types = [
        ("rectangle", "rectangle"),
        ("ellipse", "ellipse"),
        ("diamond", "diamond"),
        ("text", "text"),
        ("line", "line"),
        ("arrow", "arrow"),
        ("draw", "draw"),
        ("image", "image"),
        ("frame", "frame"),
        ("embeddable", "embeddable"),
        ("magicframe", "embeddable"),  # magicframe uses embeddable type
    ]

    for input_type, expected_type in element_types:
        element_data = {"type": input_type, "x": 0, "y": 0}
        element = factory.create_element(element_data)

        assert element is not None
        assert element["type"] == expected_type, f"Expected {expected_type}, got {element['type']} for input {input_type}"
        assert "id" in element
        assert "createdAt" in element
        assert "updatedAt" in element


def test_element_factory_draw_properties():
    """Test freedraw element creation with points data."""
    factory = ElementFactory()

    element_data = {
        "type": "draw",
        "points": [[0, 0], [50, 50], [100, 0]],
        "isComplete": True,
    }

    element = factory.create_element(element_data)

    assert element["type"] == "draw"
    assert "points" in element
    assert element["points"] == [[0, 0], [50, 50], [100, 0]]
    assert element.get("backgroundColor") == "transparent"


def test_element_factory_image_properties():
    """Test image element creation with file ID."""
    factory = ElementFactory()

    element_data = {
        "type": "image",
        "fileId": "image_abc123",
        "x": 100,
        "y": 200,
        "scale": 1.5,
    }

    element = factory.create_element(element_data)

    assert element["type"] == "image"
    assert element["fileId"] == "image_abc123"
    assert element["scale"] == 1.5
    assert element["width"] is not None
    assert element["height"] is not None


def test_element_factory_frame_properties():
    """Test frame element creation with name."""
    factory = ElementFactory()

    element_data = {"type": "frame", "name": "My Frame", "children": []}

    element = factory.create_element(element_data)

    assert element["type"] == "frame"
    assert element["name"] == "My Frame"
    assert element["children"] == []
    assert element.get("backgroundColor") == "transparent"


def test_element_factory_embeddable_properties():
    """Test embeddable element creation with seed."""
    factory = ElementFactory()

    element_data = {
        "type": "embeddable",
        "seed": "embed_123",
        "width": 800,
        "height": 600,
    }

    element = factory.create_element(element_data)

    assert element["type"] == "embeddable"
    assert element["seed"] == "embed_123"
    assert element["width"] == 800.0
    assert element["height"] == 600.0


def test_element_factory_arrow_with_arrowheads():
    """Test arrow element with start and end arrowheads."""
    factory = ElementFactory()

    element_data = {
        "type": "arrow",
        "x": 0,
        "y": 0,
        "width": 100,
        "height": 100,
        "arrowhead": "dot",
        "startArrowhead": None,
        "endArrowhead": "arrow",
    }

    element = factory.create_element(element_data)

    assert element["type"] == "arrow"
    assert element["arrowhead"] == "dot"
    assert element["endArrowhead"] == "arrow"
    assert element.get("backgroundColor") == "transparent"


def test_element_factory_text_with_alignment():
    """Test text element with text alignment properties."""
    factory = ElementFactory()

    element_data = {
        "type": "text",
        "text": "Hello World",
        "x": 100,
        "y": 200,
        "textAlign": "center",
        "verticalAlign": "middle",
    }

    element = factory.create_element(element_data)

    assert element["type"] == "text"
    assert element["text"] == "Hello World"
    assert element["textAlign"] == "center"
    assert element["verticalAlign"] == "middle"


@pytest.mark.asyncio
async def test_svg_export_multiple_elements():
    """Test SVG export with multiple element types."""
    elements = [
        {
            "type": "rectangle",
            "x": 10,
            "y": 10,
            "width": 100,
            "height": 50,
            "backgroundColor": "#e0e0e0",
        },
        {
            "type": "ellipse",
            "x": 150,
            "y": 10,
            "width": 80,
            "height": 80,
            "backgroundColor": "#ffe0e0",
        },
        {
            "type": "text",
            "text": "Test",
            "x": 50,
            "y": 100,
            "fontSize": 20,
        },
    ]

    svg_data = await export_scene(elements, format="svg")

    assert b"<rect" in svg_data
    assert b"<ellipse" in svg_data
    assert b"<text" in svg_data
    assert b"Test" in svg_data


@pytest.mark.asyncio
async def test_scene_exporter_custom_dimensions():
    """Test SceneExporter with custom dimensions."""
    exporter = SceneExporter()
    elements = [{"type": "rectangle", "x": 0, "y": 0, "width": 50, "height": 50}]

    # Test with custom dimensions
    json_data = await exporter.export_scene(
        elements, format="json", width=400, height=300
    )

    assert json_data is not None
    assert b'"elements"' in json_data


def test_element_validation_rejects_invalid_type():
    """Test that validation rejects invalid element types."""
    factory = ElementFactory()

    with pytest.raises(ValueError, match="Invalid element type"):
        factory.validate_element_data({"type": "invalid_type"})


def test_element_validation_accepts_valid_elements():
    """Test that validation accepts valid elements with defaults."""
    factory = ElementFactory()

    # Valid element with defaults
    element_data = {"type": "rectangle", "x": 0, "y": 0}
    validated = factory.validate_element_data(element_data)

    assert validated is not None
    assert validated["type"] == "rectangle"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
