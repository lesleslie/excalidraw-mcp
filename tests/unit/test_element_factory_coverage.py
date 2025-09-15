"""Additional tests to cover missing lines in element_factory.py"""

import pytest

from excalidraw_mcp.element_factory import ElementFactory


def test_line_element_default_dimensions():
    """Test that line elements get default dimensions when not provided."""
    factory = ElementFactory()

    # Create a line element without width/height
    element_data = {"type": "line"}
    element = factory.create_element(element_data)

    # Should have default dimensions for lines
    assert element["width"] == 100.0
    assert element["height"] == 0.0


def test_shape_elements_default_dimensions():
    """Test that shape elements get default dimensions when not provided."""
    factory = ElementFactory()

    # Create a rectangle without width/height
    element_data = {"type": "rectangle"}
    element = factory.create_element(element_data)

    # Should have default dimensions for shapes
    assert element["width"] == 100.0
    assert element["height"] == 100.0


def test_element_validation_invalid_dimension_not_number():
    """Test validation fails with non-numeric dimensions."""
    factory = ElementFactory()
    invalid_data = {
        "type": "rectangle",
        "x": 100,
        "y": 200,
        "width": "not_a_number",  # Invalid width
        "height": 100,
    }

    with pytest.raises(ValueError, match="Invalid width: must be a number"):
        factory.validate_element_data(invalid_data)


def test_element_validation_invalid_stroke_width_not_number():
    """Test validation fails with non-numeric stroke width."""
    factory = ElementFactory()
    invalid_data = {
        "type": "rectangle",
        "strokeWidth": "not_a_number",  # Invalid stroke width
    }

    with pytest.raises(ValueError, match="strokeWidth must be a number"):
        factory.validate_element_data(invalid_data)


def test_element_validation_invalid_opacity_not_number():
    """Test validation fails with non-numeric opacity."""
    factory = ElementFactory()
    invalid_data = {
        "type": "rectangle",
        "opacity": "not_a_number",  # Invalid opacity
    }

    with pytest.raises(ValueError, match="opacity must be a number"):
        factory.validate_element_data(invalid_data)


def test_element_validation_invalid_roughness_not_number():
    """Test validation fails with non-numeric roughness."""
    factory = ElementFactory()
    invalid_data = {
        "type": "rectangle",
        "roughness": "not_a_number",  # Invalid roughness
    }

    with pytest.raises(ValueError, match="roughness must be a number"):
        factory.validate_element_data(invalid_data)


def test_element_validation_invalid_font_size_not_number():
    """Test validation fails with non-numeric font size."""
    factory = ElementFactory()
    invalid_data = {
        "type": "text",
        "fontSize": "not_a_number",  # Invalid font size
    }

    with pytest.raises(ValueError, match="fontSize must be a number"):
        factory.validate_element_data(invalid_data)


def test_optional_float_conversion_invalid_values():
    """Test optional float conversion with invalid values."""
    factory = ElementFactory()

    # Test with various invalid values
    assert factory._get_optional_float({"key": "invalid"}, "key") is None
    assert factory._get_optional_float({"key": []}, "key") is None
    assert factory._get_optional_float({"key": {}}, "key") is None
    assert factory._get_optional_float({"key": None}, "key") is None


def test_prepare_update_data_numeric_conversion():
    """Test that prepare_update_data properly converts numeric values."""
    factory = ElementFactory()
    update_data = {
        "id": "test-123",
        "x": "150",  # String that should be converted to float
        "y": "250",  # String that should be converted to float
        "width": "100.5",  # String that should be converted to float
        "strokeWidth": "2.5",  # String that should be converted to float
    }

    result = factory.prepare_update_data(update_data)

    assert result["x"] == 150.0
    assert result["y"] == 250.0
    assert result["width"] == 100.5
    assert result["strokeWidth"] == 2.5


def test_prepare_update_data_with_none_values():
    """Test that prepare_update_data handles None values correctly."""
    factory = ElementFactory()
    update_data = {
        "id": "test-123",
        "x": None,  # None value
        "width": None,  # None value
    }

    result = factory.prepare_update_data(update_data)

    # None values should remain None
    assert result["x"] is None
    assert result["width"] is None


def test_prepare_update_data_with_valid_numeric_values():
    """Test that prepare_update_data works with valid numeric values."""
    factory = ElementFactory()
    update_data = {
        "id": "test-123",
        "x": 150,  # Already numeric
        "y": 250.5,  # Already numeric float
    }

    result = factory.prepare_update_data(update_data)

    assert result["x"] == 150.0
    assert result["y"] == 250.5
