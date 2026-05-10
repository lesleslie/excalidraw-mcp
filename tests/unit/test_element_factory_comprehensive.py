"""Comprehensive tests for ElementFactory covering all validation and creation logic."""

import pytest
from datetime import datetime, UTC
from excalidraw_mcp.element_factory import ElementFactory


class TestElementFactoryCreation:
    """Test element creation with all element types."""

    @pytest.fixture
    def factory(self):
        return ElementFactory()

    def test_create_rectangle_basic(self, factory):
        """Test basic rectangle creation."""
        element_data = {"type": "rectangle", "x": 10, "y": 20, "width": 100, "height": 50}
        element = factory.create_element(element_data)

        assert element["type"] == "rectangle"
        assert element["x"] == 10.0
        assert element["y"] == 20.0
        assert element["width"] == 100.0
        assert element["height"] == 50.0
        assert "id" in element
        assert "createdAt" in element
        assert "updatedAt" in element
        assert element["version"] == 1
        assert element["locked"] is False

    def test_create_ellipse_basic(self, factory):
        """Test basic ellipse creation."""
        element_data = {"type": "ellipse", "x": 0, "y": 0, "width": 200, "height": 150}
        element = factory.create_element(element_data)

        assert element["type"] == "ellipse"
        assert element["width"] == 200.0
        assert element["height"] == 150.0

    def test_create_diamond_basic(self, factory):
        """Test basic diamond creation."""
        element_data = {"type": "diamond", "x": 50, "y": 50}
        element = factory.create_element(element_data)

        assert element["type"] == "diamond"
        # Diamonds should get default dimensions
        assert element["width"] == 100.0
        assert element["height"] == 100.0

    def test_create_text_basic(self, factory):
        """Test basic text creation."""
        element_data = {
            "type": "text",
            "text": "Hello World",
            "x": 100,
            "y": 200,
            "fontSize": 20,
        }
        element = factory.create_element(element_data)

        assert element["type"] == "text"
        assert element["text"] == "Hello World"
        assert element["fontSize"] == 20.0
        assert element["fontFamily"] == "Cascadia, Consolas"
        assert element["textAlign"] == "left"
        assert element["verticalAlign"] == "top"

    def test_create_line_basic(self, factory):
        """Test basic line creation."""
        element_data = {"type": "line", "x": 0, "y": 0, "width": 100, "height": 0}
        element = factory.create_element(element_data)

        assert element["type"] == "line"
        assert element["backgroundColor"] == "transparent"

    def test_create_arrow_basic(self, factory):
        """Test basic arrow creation."""
        element_data = {
            "type": "arrow",
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 100,
            "arrowhead": "arrow",
        }
        element = factory.create_element(element_data)

        assert element["type"] == "arrow"
        assert element["backgroundColor"] == "transparent"
        assert element["arrowhead"] == "arrow"
        assert element["endArrowhead"] == "arrow"

    def test_create_draw_with_points(self, factory):
        """Test freedraw creation with points."""
        element_data = {
            "type": "draw",
            "points": [[0, 0], [50, 50], [100, 0]],
            "isComplete": True,
        }
        element = factory.create_element(element_data)

        assert element["type"] == "draw"
        assert element["points"] == [[0, 0], [50, 50], [100, 0]]
        assert element["isComplete"] is True
        assert element["backgroundColor"] == "transparent"

    def test_create_image_with_file_id(self, factory):
        """Test image creation with file ID."""
        element_data = {
            "type": "image",
            "fileId": "img_abc123",
            "scale": 1.5,
        }
        element = factory.create_element(element_data)

        assert element["type"] == "image"
        assert element["fileId"] == "img_abc123"
        assert element["scale"] == 1.5
        assert element["status"] == "saved"
        assert element["width"] == 300.0
        assert element["height"] == 200.0

    def test_create_frame_with_name(self, factory):
        """Test frame creation with name."""
        element_data = {
            "type": "frame",
            "name": "My Frame",
            "children": ["elem1", "elem2"],
        }
        element = factory.create_element(element_data)

        assert element["type"] == "frame"
        assert element["name"] == "My Frame"
        assert element["children"] == ["elem1", "elem2"]
        assert element["backgroundColor"] == "transparent"

    def test_create_embeddable_with_seed(self, factory):
        """Test embeddable creation."""
        element_data = {
            "type": "embeddable",
            "seed": "seed123",
        }
        element = factory.create_element(element_data)

        assert element["type"] == "embeddable"
        assert element["seed"] == "seed123"
        assert element["width"] == 800.0
        assert element["height"] == 600.0

    def test_create_magicframe_becomes_embeddable(self, factory):
        """Test magicframe is converted to embeddable type."""
        element_data = {
            "type": "magicframe",
            "seed": "magic456",
        }
        element = factory.create_element(element_data)

        assert element["type"] == "embeddable"
        assert element["seed"] == "magic456"

    def test_create_element_with_visual_properties(self, factory):
        """Test element creation with custom visual properties."""
        element_data = {
            "type": "rectangle",
            "strokeColor": "#ff0000",
            "backgroundColor": "#00ff00",
            "strokeWidth": 4,
            "opacity": 80,
            "roughness": 2,
        }
        element = factory.create_element(element_data)

        assert element["strokeColor"] == "#ff0000"
        assert element["backgroundColor"] == "#00ff00"
        assert element["strokeWidth"] == 4.0
        assert element["opacity"] == 80.0
        assert element["roughness"] == 2.0

    def test_create_element_locked(self, factory):
        """Test creating a locked element."""
        element_data = {"type": "rectangle", "locked": True}
        element = factory.create_element(element_data)

        assert element["locked"] is True

    def test_create_element_with_none_dimensions(self, factory):
        """Test element with None dimensions gets defaults."""
        element_data = {"type": "rectangle", "width": None, "height": None}
        element = factory.create_element(element_data)

        assert element["width"] == 100.0
        assert element["height"] == 100.0


class TestElementFactoryUpdate:
    """Test element update preparation."""

    @pytest.fixture
    def factory(self):
        return ElementFactory()

    def test_prepare_update_data_basic(self, factory):
        """Test basic update data preparation."""
        update_data = {
            "id": "elem123",
            "x": 100,
            "y": 200,
            "width": 150,
            "height": 100,
        }
        result = factory.prepare_update_data(update_data)

        assert result["id"] == "elem123"
        assert result["x"] == 100.0
        assert result["y"] == 200.0
        assert result["width"] == 150.0
        assert result["height"] == 100.0
        assert "updatedAt" in result
        assert "id" not in update_data  # Should be popped

    def test_prepare_update_missing_id_raises(self, factory):
        """Test that missing ID raises ValueError."""
        update_data = {"x": 100, "y": 200}

        with pytest.raises(ValueError, match="Element ID is required"):
            factory.prepare_update_data(update_data)

    def test_prepare_update_protects_immutable_fields(self, factory):
        """Test that immutable fields are protected."""
        update_data = {
            "id": "elem123",
            "createdAt": "old_timestamp",
            "version": 5,
            "x": 100,
        }
        result = factory.prepare_update_data(update_data)

        assert "createdAt" not in result
        assert "version" not in result
        assert result["x"] == 100.0

    def test_prepare_update_with_visual_properties(self, factory):
        """Test update with visual properties converted to float."""
        update_data = {
            "id": "elem123",
            "strokeWidth": "4",
            "opacity": "80",
            "roughness": "2",
            "fontSize": "20",
        }
        result = factory.prepare_update_data(update_data)

        assert result["strokeWidth"] == 4.0
        assert result["opacity"] == 80.0
        assert result["roughness"] == 2.0
        assert result["fontSize"] == 20.0

    def test_prepare_update_with_none_values(self, factory):
        """Test update with None values preserved."""
        update_data = {
            "id": "elem123",
            "width": None,
            "height": None,
        }
        result = factory.prepare_update_data(update_data)

        assert result["width"] is None
        assert result["height"] is None


class TestElementFactoryValidation:
    """Test element validation logic."""

    @pytest.fixture
    def factory(self):
        return ElementFactory()

    def test_validate_valid_element(self, factory):
        """Test validation of valid element."""
        element_data = {
            "type": "rectangle",
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 100,
            "strokeColor": "#000000",
            "backgroundColor": "#ffffff",
        }
        result = factory.validate_element_data(element_data)

        assert result == element_data

    def test_validate_missing_type_raises(self, factory):
        """Test that missing type raises error."""
        element_data = {"x": 0, "y": 0}

        with pytest.raises(ValueError, match="Element type is required"):
            factory.validate_element_data(element_data)

    def test_validate_invalid_type_raises(self, factory):
        """Test that invalid type raises error."""
        element_data = {"type": "invalid_type"}

        with pytest.raises(ValueError, match="Invalid element type"):
            factory.validate_element_data(element_data)

    def test_validate_all_valid_types(self, factory):
        """Test that all valid types are accepted."""
        valid_types = [
            "rectangle",
            "ellipse",
            "diamond",
            "text",
            "line",
            "arrow",
            "draw",
            "image",
            "frame",
            "embeddable",
            "magicframe",
        ]

        for element_type in valid_types:
            element_data = {"type": element_type}
            result = factory.validate_element_data(element_data)
            assert result["type"] == element_type

    def test_validate_invalid_x_coordinate(self, factory):
        """Test that invalid x coordinate raises error."""
        element_data = {"type": "rectangle", "x": "invalid"}

        with pytest.raises(ValueError, match="Invalid x coordinate"):
            factory.validate_element_data(element_data)

    def test_validate_invalid_y_coordinate(self, factory):
        """Test that invalid y coordinate raises error."""
        element_data = {"type": "rectangle", "y": None}

        with pytest.raises(ValueError, match="Invalid y coordinate"):
            factory.validate_element_data(element_data)

    def test_validate_negative_width_raises(self, factory):
        """Test that negative width raises error."""
        element_data = {"type": "rectangle", "width": -10}

        with pytest.raises(ValueError, match="Invalid width"):
            factory.validate_element_data(element_data)

    def test_validate_negative_height_raises(self, factory):
        """Test that negative height raises error."""
        element_data = {"type": "rectangle", "height": -20}

        with pytest.raises(ValueError, match="Invalid height"):
            factory.validate_element_data(element_data)

    def test_validate_invalid_width_type(self, factory):
        """Test that invalid width type raises error."""
        element_data = {"type": "rectangle", "width": "invalid"}

        with pytest.raises(ValueError, match="Invalid width"):
            factory.validate_element_data(element_data)

    def test_validate_none_dimensions_allowed(self, factory):
        """Test that None dimensions are allowed."""
        element_data = {
            "type": "rectangle",
            "width": None,
            "height": None,
        }
        result = factory.validate_element_data(element_data)

        assert result["width"] is None
        assert result["height"] is None

    def test_validate_invalid_stroke_color(self, factory):
        """Test that invalid stroke color raises error."""
        element_data = {
            "type": "rectangle",
            "strokeColor": "invalid_color",
        }

        with pytest.raises(ValueError, match="Invalid strokeColor"):
            factory.validate_element_data(element_data)

    def test_validate_invalid_background_color(self, factory):
        """Test that invalid background color raises error."""
        element_data = {
            "type": "rectangle",
            "backgroundColor": "not_a_color",
        }

        with pytest.raises(ValueError, match="Invalid backgroundColor"):
            factory.validate_element_data(element_data)

    def test_validate_transparent_color(self, factory):
        """Test that transparent color is valid."""
        element_data = {
            "type": "rectangle",
            "backgroundColor": "transparent",
        }
        result = factory.validate_element_data(element_data)

        assert result["backgroundColor"] == "transparent"

    def test_validate_valid_hex_colors(self, factory):
        """Test various valid hex color formats."""
        valid_colors = [
            "#000000",
            "#ffffff",
            "#ff0000",
            "#00ff00",
            "#0000ff",
            "#123456",
            "#abcdef",
        ]

        for color in valid_colors:
            element_data = {
                "type": "rectangle",
                "strokeColor": color,
                "backgroundColor": color,
            }
            result = factory.validate_element_data(element_data)
            assert result["strokeColor"] == color
            assert result["backgroundColor"] == color

    def test_validate_invalid_hex_color_format(self, factory):
        """Test invalid hex color formats."""
        # Test non-string values - these should raise ValueError
        for color in [123456, None, []]:
            element_data = {
                "type": "rectangle",
                "strokeColor": color,
            }

            with pytest.raises(ValueError, match="Invalid strokeColor"):
                factory.validate_element_data(element_data)

        # Test invalid hex formats - these should also raise ValueError
        for color in ["#000", "#00000", "#0000000", "gggggg", "#ZZZZZZ", "notacolor"]:
            element_data = {
                "type": "rectangle",
                "strokeColor": color,
            }

            with pytest.raises(ValueError, match="Invalid strokeColor"):
                factory.validate_element_data(element_data)

    def test_validate_stroke_width_out_of_range(self, factory):
        """Test stroke width validation."""
        # Too low
        with pytest.raises(ValueError, match="strokeWidth must be between 0 and 50"):
            factory.validate_element_data({"type": "rectangle", "strokeWidth": -1})

        # Too high
        with pytest.raises(ValueError, match="strokeWidth must be between 0 and 50"):
            factory.validate_element_data({"type": "rectangle", "strokeWidth": 51})

    def test_validate_invalid_stroke_width_type(self, factory):
        """Test invalid stroke width type."""
        with pytest.raises(ValueError, match="strokeWidth must be a number"):
            factory.validate_element_data({"type": "rectangle", "strokeWidth": "invalid"})

    def test_validate_opacity_out_of_range(self, factory):
        """Test opacity validation."""
        # Too low
        with pytest.raises(ValueError, match="opacity must be between 0 and 100"):
            factory.validate_element_data({"type": "rectangle", "opacity": -1})

        # Too high
        with pytest.raises(ValueError, match="opacity must be between 0 and 100"):
            factory.validate_element_data({"type": "rectangle", "opacity": 101})

    def test_validate_invalid_opacity_type(self, factory):
        """Test invalid opacity type."""
        with pytest.raises(ValueError, match="opacity must be a number"):
            factory.validate_element_data({"type": "rectangle", "opacity": "invalid"})

    def test_validate_roughness_out_of_range(self, factory):
        """Test roughness validation."""
        # Too low
        with pytest.raises(ValueError, match="roughness must be between 0 and 3"):
            factory.validate_element_data({"type": "rectangle", "roughness": -0.1})

        # Too high
        with pytest.raises(ValueError, match="roughness must be between 0 and 3"):
            factory.validate_element_data({"type": "rectangle", "roughness": 3.1})

    def test_validate_invalid_roughness_type(self, factory):
        """Test invalid roughness type."""
        with pytest.raises(ValueError, match="roughness must be a number"):
            factory.validate_element_data({"type": "rectangle", "roughness": "invalid"})

    def test_validate_font_size_out_of_range(self, factory):
        """Test font size validation."""
        # Too small
        with pytest.raises(ValueError, match="fontSize must be between 8 and 200"):
            factory.validate_element_data({"type": "text", "fontSize": 7})

        # Too large
        with pytest.raises(ValueError, match="fontSize must be between 8 and 200"):
            factory.validate_element_data({"type": "text", "fontSize": 201})

    def test_validate_invalid_font_size_type(self, factory):
        """Test invalid font size type."""
        with pytest.raises(ValueError, match="fontSize must be a number"):
            factory.validate_element_data({"type": "text", "fontSize": "invalid"})

    def test_validate_multiple_errors(self, factory):
        """Test that multiple validation errors are reported."""
        element_data = {
            "type": "invalid_type",
            "x": "invalid",
            "width": -10,
            "strokeColor": "bad_color",
            "strokeWidth": 100,
        }

        with pytest.raises(ValueError) as exc_info:
            factory.validate_element_data(element_data)

        error_message = str(exc_info.value)
        assert "Invalid element type" in error_message
        assert "Invalid x coordinate" in error_message
        assert "Invalid width" in error_message


class TestOptionalFloatConversion:
    """Test _get_optional_float method."""

    @pytest.fixture
    def factory(self):
        return ElementFactory()

    def test_get_optional_float_with_int(self, factory):
        """Test conversion from int."""
        result = factory._get_optional_float({"value": 42}, "value")
        assert result == 42.0

    def test_get_optional_float_with_float(self, factory):
        """Test conversion from float."""
        result = factory._get_optional_float({"value": 3.14}, "value")
        assert result == 3.14

    def test_get_optional_float_with_string_float(self, factory):
        """Test conversion from string."""
        result = factory._get_optional_float({"value": "2.718"}, "value")
        assert result == 2.718

    def test_get_optional_float_with_invalid_string(self, factory):
        """Test invalid string returns default."""
        result = factory._get_optional_float({"value": "invalid"}, "value", default=10.0)
        assert result == 10.0

    def test_get_optional_float_with_none(self, factory):
        """Test None value."""
        result = factory._get_optional_float({"value": None}, "value")
        assert result is None

    def test_get_optional_float_missing_key(self, factory):
        """Test missing key returns default."""
        result = factory._get_optional_float({}, "value", default=5.0)
        assert result == 5.0

    def test_get_optional_float_no_default_returns_none(self, factory):
        """Test missing key with no default returns None."""
        result = factory._get_optional_float({}, "value")
        assert result is None


class TestColorValidation:
    """Test _is_valid_color method."""

    @pytest.fixture
    def factory(self):
        return ElementFactory()

    def test_is_valid_color_with_transparent(self, factory):
        """Test transparent is valid."""
        assert factory._is_valid_color("transparent") is True

    def test_is_valid_color_case_insensitive(self, factory):
        """Test transparent check is case-insensitive."""
        assert factory._is_valid_color("TRANSPARENT") is True
        assert factory._is_valid_color("Transparent") is True

    def test_is_valid_color_with_valid_hex(self, factory):
        """Test valid hex colors."""
        assert factory._is_valid_color("#000000") is True
        assert factory._is_valid_color("#ffffff") is True
        assert factory._is_valid_color("#FF0000") is True
        assert factory._is_valid_color("#123abc") is True

    def test_is_valid_color_with_invalid_hex(self, factory):
        """Test invalid hex colors."""
        assert factory._is_valid_color("#000") is False
        assert factory._is_valid_color("#00000") is False
        assert factory._is_valid_color("#0000000") is False
        assert factory._is_valid_color("#gggggg") is False
        assert factory._is_valid_color("abcdef") is False  # Missing #

    def test_is_valid_color_with_non_string(self, factory):
        """Test non-string types return False."""
        assert factory._is_valid_color(123456) is False
        assert factory._is_valid_color(None) is False
        assert factory._is_valid_color([]) is False
        assert factory._is_valid_color({}) is False
