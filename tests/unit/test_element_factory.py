"""Unit tests for ElementFactory."""

import pytest

from excalidraw_mcp.element_factory import ElementFactory


class TestElementFactory:
    """Test ElementFactory functionality."""

    def test_create_basic_rectangle(self, element_factory):
        """Test creating a basic rectangle element."""
        element = element_factory("rectangle", x=100, y=200, width=150, height=100)

        assert element["type"] == "rectangle"
        assert element["x"] == 100.0
        assert element["y"] == 200.0
        assert element["width"] == 150.0
        assert element["height"] == 100.0
        assert element["version"] == 1
        assert "id" in element
        assert "createdAt" in element
        assert "updatedAt" in element
        assert element["locked"] is False

    def test_create_text_element(self, element_factory):
        """Test creating a text element with specific properties."""
        element = element_factory(
            "text", x=50, y=75, text="Hello World", fontSize=24, fontFamily="Arial"
        )

        assert element["type"] == "text"
        assert element["text"] == "Hello World"
        assert element["fontSize"] == 24.0
        assert element["fontFamily"] == "Arial"

    def test_create_line_element(self, element_factory):
        """Test creating a line element."""
        element = element_factory("line", x=0, y=0, width=100, height=0)

        assert element["type"] == "line"
        assert element["backgroundColor"] == "transparent"
        assert element["width"] == 100.0
        assert element["height"] == 0.0

    def test_element_validation_success(self):
        """Test successful element validation."""
        factory = ElementFactory()
        valid_data = {
            "type": "rectangle",
            "x": 100,
            "y": 200,
            "width": 150,
            "height": 100,
            "strokeColor": "#ff0000",
            "backgroundColor": "#ffffff",
        }

        # Should not raise any exception
        result = factory.validate_element_data(valid_data)
        assert result == valid_data

    def test_element_validation_missing_type(self):
        """Test validation fails when type is missing."""
        factory = ElementFactory()
        invalid_data = {"x": 100, "y": 200}

        with pytest.raises(ValueError, match="Element type is required"):
            factory.validate_element_data(invalid_data)

    def test_element_validation_invalid_type(self):
        """Test validation fails with invalid element type."""
        factory = ElementFactory()
        invalid_data = {"type": "invalid_type", "x": 100, "y": 200}

        with pytest.raises(ValueError, match="Invalid element type"):
            factory.validate_element_data(invalid_data)

    def test_element_validation_invalid_coordinates(self):
        """Test validation fails with non-numeric coordinates."""
        factory = ElementFactory()
        invalid_data = {"type": "rectangle", "x": "not_a_number", "y": 200}

        with pytest.raises(ValueError, match="Invalid x coordinate"):
            factory.validate_element_data(invalid_data)

    def test_element_validation_negative_dimensions(self):
        """Test validation fails with negative dimensions."""
        factory = ElementFactory()
        invalid_data = {
            "type": "rectangle",
            "x": 100,
            "y": 200,
            "width": -50,
            "height": 100,
        }

        with pytest.raises(ValueError, match="Invalid width: must be non-negative"):
            factory.validate_element_data(invalid_data)

    def test_element_validation_invalid_color(self):
        """Test validation fails with invalid color format."""
        factory = ElementFactory()
        invalid_data = {
            "type": "rectangle",
            "x": 100,
            "y": 200,
            "strokeColor": "invalid_color",
        }

        with pytest.raises(ValueError, match="Invalid strokeColor"):
            factory.validate_element_data(invalid_data)

    def test_element_validation_stroke_width_range(self):
        """Test validation of stroke width range."""
        factory = ElementFactory()

        # Valid stroke width
        valid_data = {"type": "rectangle", "strokeWidth": 5}
        factory.validate_element_data(valid_data)

        # Invalid stroke width (too high)
        invalid_data = {"type": "rectangle", "strokeWidth": 100}
        with pytest.raises(ValueError, match="strokeWidth must be between 0 and 50"):
            factory.validate_element_data(invalid_data)

    def test_element_validation_opacity_range(self):
        """Test validation of opacity range."""
        factory = ElementFactory()

        # Valid opacity
        valid_data = {"type": "rectangle", "opacity": 50}
        factory.validate_element_data(valid_data)

        # Invalid opacity (too high)
        invalid_data = {"type": "rectangle", "opacity": 150}
        with pytest.raises(ValueError, match="opacity must be between 0 and 100"):
            factory.validate_element_data(invalid_data)

    def test_prepare_update_data(self):
        """Test preparing element data for updates."""
        factory = ElementFactory()
        update_data = {
            "id": "test-123",
            "x": 150,
            "y": 250,
            "strokeColor": "#ff0000",
            "version": 1,  # Should be ignored
            "createdAt": "2025-01-01T00:00:00.000Z",  # Should be ignored
        }

        result = factory.prepare_update_data(update_data)

        assert result["id"] == "test-123"
        assert result["x"] == 150.0
        assert result["y"] == 250.0
        assert result["strokeColor"] == "#ff0000"
        assert "version" not in result  # Protected field
        assert "createdAt" not in result  # Protected field
        assert "updatedAt" in result

    def test_prepare_update_data_missing_id(self):
        """Test that prepare_update_data fails without ID."""
        factory = ElementFactory()
        update_data = {"x": 150, "y": 250}

        with pytest.raises(ValueError, match="Element ID is required for updates"):
            factory.prepare_update_data(update_data)

    def test_color_validation_hex(self):
        """Test hex color validation."""
        factory = ElementFactory()

        # Valid hex colors
        assert factory._is_valid_color("#ffffff")
        assert factory._is_valid_color("#000000")
        assert factory._is_valid_color("#ff0000")
        assert factory._is_valid_color("transparent")

        # Invalid hex colors
        assert not factory._is_valid_color("ffffff")  # Missing #
        assert not factory._is_valid_color("#fffff")  # Wrong length
        assert not factory._is_valid_color("#gggggg")  # Invalid hex chars
        assert not factory._is_valid_color(123)  # Not a string

    def test_optional_float_conversion(self):
        """Test optional float conversion utility."""
        factory = ElementFactory()

        # Valid conversions
        assert factory._get_optional_float({"key": "123.5"}, "key") == 123.5
        assert factory._get_optional_float({"key": 100}, "key") == 100.0
        assert factory._get_optional_float({"key": None}, "key") is None
        assert factory._get_optional_float({}, "key") is None
        assert factory._get_optional_float({}, "key", 50.0) == 50.0

        # Invalid conversions (should return default)
        assert factory._get_optional_float({"key": "invalid"}, "key", 25.0) == 25.0
        assert factory._get_optional_float({"key": []}, "key", 10.0) == 10.0

    @pytest.mark.performance
    def test_element_creation_performance(self, performance_monitor):
        """Test element creation performance."""
        factory = ElementFactory()

        # Create 1000 elements
        for i in range(1000):
            element = factory.create_element(
                {"type": "rectangle", "x": i, "y": i * 2, "width": 100, "height": 50}
            )
            assert "id" in element

        # Performance should be reasonable (handled by performance_monitor fixture)
