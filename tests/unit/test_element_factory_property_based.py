"""Property-based tests for ElementFactory using Hypothesis."""

import pytest
from hypothesis import given, strategies as st, settings
from excalidraw_mcp.element_factory import ElementFactory


class TestPropertyBasedElementCreation:
    """Property-based tests for element creation."""

    @given(
        element_type=st.sampled_from([
            "rectangle", "ellipse", "diamond", "text", "line", "arrow",
            "draw", "image", "frame", "embeddable"
        ]),
        x=st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False),
        y=st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False),
        width=st.one_of(st.none(), st.floats(min_value=0, max_value=5000, allow_nan=False, allow_infinity=False)),
        height=st.one_of(st.none(), st.floats(min_value=0, max_value=5000, allow_nan=False, allow_infinity=False)),
    )
    @settings(max_examples=20)
    def test_element_creation_preserves_coordinates(self, element_type, x, y, width, height):
        """Test that element creation preserves coordinate values."""
        element_data = {
            "type": element_type,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        }

        element = factory.create_element(element_data)

        assert element["x"] == x
        assert element["y"] == y
        if width is not None:
            assert element["width"] == width
        if height is not None:
            assert element["height"] == height

    @given(
        stroke_width=st.floats(min_value=0, max_value=50, allow_nan=False, allow_infinity=False),
        opacity=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
        roughness=st.floats(min_value=0, max_value=3, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_visual_properties_converted_to_float(self, stroke_width, opacity, roughness):
        """Test that visual properties are converted to floats."""
        factory = ElementFactory()
        element_data = {
            "type": "rectangle",
            "strokeWidth": stroke_width,
            "opacity": opacity,
            "roughness": roughness,
        }

        element = factory.create_element(element_data)

        assert isinstance(element["strokeWidth"], float)
        assert isinstance(element["opacity"], float)
        assert isinstance(element["roughness"], float)
        assert element["strokeWidth"] == stroke_width
        assert element["opacity"] == opacity
        assert element["roughness"] == roughness

    @given(
        text=st.text(min_size=0, max_size=1000),
        font_size=st.floats(min_value=8, max_value=200, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_text_element_preserves_content(self, text, font_size):
        """Test that text elements preserve text content and font size."""
        element_data = {
            "type": "text",
            "text": text,
            "fontSize": font_size,
        }

        element = factory.create_element(element_data)

        assert element["type"] == "text"
        assert element["text"] == text
        assert element["fontSize"] == font_size

    @given(
        points=st.lists(
            st.lists(
                st.floats(min_value=-5000, max_value=5000, allow_nan=False, allow_infinity=False),
                min_size=2,
                max_size=2,
            ),
            min_size=2,
            max_size=100,
        ),
    )
    @settings(max_examples=20)
    def test_draw_element_preserves_points(self, points):
        """Test that draw elements preserve points data."""
        factory = ElementFactory()
        element_data = {
            "type": "draw",
            "points": points,
        }

        element = factory.create_element(element_data)

        assert element["type"] == "draw"
        assert element["points"] == points

    @given(
        scale=st.floats(min_value=0.1, max_value=10, allow_nan=False, allow_infinity=False),
        file_id=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=20)
    def test_image_element_properties(self, scale, file_id):
        """Test that image elements preserve scale and file ID."""
        factory = ElementFactory()
        element_data = {
            "type": "image",
            "fileId": file_id,
            "scale": scale,
        }

        element = factory.create_element(element_data)

        assert element["type"] == "image"
        assert element["fileId"] == file_id
        assert element["scale"] == scale

    @given(
        element_id=st.uuids().map(lambda u: str(u)),
        x=st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False),
        y=st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_update_data_converts_coordinates(self, element_id, x, y):
        """Test that update data converts coordinates to float."""
        factory = ElementFactory()
        update_data = {
            "id": str(element_id),
            "x": x,
            "y": y,
        }

        result = factory.prepare_update_data(update_data)

        assert result["id"] == str(element_id)
        assert isinstance(result["x"], float)
        assert isinstance(result["y"], float)
        assert result["x"] == x
        assert result["y"] == y


class TestPropertyBasedValidation:
    """Property-based tests for validation logic."""

    @given(
        r=st.integers(min_value=0, max_value=255),
        g=st.integers(min_value=0, max_value=255),
        b=st.integers(min_value=0, max_value=255),
    )
    @settings(max_examples=20)
    def test_valid_hex_colors_accepted(self, r, g, b):
        """Test that valid hex colors are accepted."""
        factory = ElementFactory()
        color = f"#{r:02x}{g:02x}{b:02x}"
        element_data = {
            "type": "rectangle",
            "strokeColor": color,
            "backgroundColor": color,
        }

        result = factory.validate_element_data(element_data)

        assert result["strokeColor"] == color
        assert result["backgroundColor"] == color

    @given(
        width=st.one_of(
            st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
            st.none(),
        ),
        height=st.one_of(
            st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
            st.none(),
        ),
    )
    @settings(max_examples=20)
    def test_valid_dimensions_accepted(self, width, height):
        """Test that valid dimensions are accepted."""
        factory = ElementFactory()
        element_data = {
            "type": "rectangle",
            "width": width,
            "height": height,
        }

        result = factory.validate_element_data(element_data)

        if width is not None:
            assert result["width"] == width
        if height is not None:
            assert result["height"] == height

    @given(
        stroke_width=st.floats(min_value=0, max_value=50, allow_nan=False, allow_infinity=False),
        opacity=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
        roughness=st.floats(min_value=0, max_value=3, allow_nan=False, allow_infinity=False),
        font_size=st.floats(min_value=8, max_value=200, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_valid_numeric_ranges_accepted(self, stroke_width, opacity, roughness, font_size):
        """Test that valid numeric ranges are accepted."""
        factory = ElementFactory()
        element_data = {
            "type": "text",
            "strokeWidth": stroke_width,
            "opacity": opacity,
            "roughness": roughness,
            "fontSize": font_size,
        }

        result = factory.validate_element_data(element_data)

        assert result["strokeWidth"] == stroke_width
        assert result["opacity"] == opacity
        assert result["roughness"] == roughness
        assert result["fontSize"] == font_size


class TestPropertyBasedElementIdGeneration:
    """Property-based tests for element ID generation."""

    @given(
        element_type=st.sampled_from([
            "rectangle", "ellipse", "diamond", "text", "line", "arrow",
            "draw", "image", "frame", "embeddable"
        ]),
    )
    @settings(max_examples=10)
    def test_elements_have_unique_ids(self, element_type):
        """Test that created elements have unique IDs."""
        factory = ElementFactory()
        elements = [
            factory.create_element({"type": element_type})
            for _ in range(10)
        ]

        ids = [elem["id"] for elem in elements]
        assert len(ids) == len(set(ids)), "All element IDs should be unique"

    @given(
        element_type=st.sampled_from([
            "rectangle", "ellipse", "diamond", "text", "line", "arrow",
            "draw", "image", "frame", "embeddable"
        ]),
    )
    @settings(max_examples=10)
    def test_elements_have_timestamps(self, element_type):
        """Test that created elements have timestamps."""
        factory = ElementFactory()
        element = factory.create_element({"type": element_type})

        assert "createdAt" in element
        assert "updatedAt" in element
        assert element["createdAt"] == element["updatedAt"]

        # Check ISO format with Z suffix
        assert element["createdAt"].endswith("Z")
        assert "T" in element["createdAt"]


class TestPropertyBasedOptionalFloats:
    """Property-based tests for _get_optional_float method."""

    @given(
        value=st.one_of(
            st.integers(min_value=-1000, max_value=1000),
            st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
            st.none(),
        ),
    )
    @settings(max_examples=20)
    def test_optional_float_conversion(self, value):
        """Test that optional float conversion works correctly."""
        factory = ElementFactory()
        data = {"value": value}

        if value is None:
            result = factory._get_optional_float(data, "value")
            assert result is None
        else:
            result = factory._get_optional_float(data, "value")
            assert isinstance(result, float)
            assert result == float(value)

    @given(
        value=st.one_of(
            st.integers(min_value=-1000, max_value=1000),
            st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        ),
        default=st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_optional_float_with_default(self, value, default):
        """Test that optional float with default works correctly."""
        factory = ElementFactory()
        data = {"value": value}

        result = factory._get_optional_float(data, "value", default=default)
        assert result == float(value)

    @given(
        default=st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_optional_float_missing_key_uses_default(self, default):
        """Test that missing key returns default."""
        factory = ElementFactory()
        result = factory._get_optional_float({}, "missing_key", default=default)
        assert result == default
