"""Security tests for input validation."""

import pytest

from excalidraw_mcp.element_factory import ElementFactory


class TestInputValidationSecurity:
    """Security tests for input validation and sanitization."""

    @pytest.mark.security
    def test_xss_prevention_in_text_elements(self, security_test_data):
        """Test that XSS attempts in text elements are handled safely."""
        factory = ElementFactory()

        malicious_text = security_test_data["xss_text"]
        element_data = {"type": "text", "x": 100, "y": 200, "text": malicious_text}

        # Validation should pass (we store the raw text)
        validated_data = factory.validate_element_data(element_data)
        assert validated_data["text"] == malicious_text

        # Element creation should succeed (sanitization happens at render time)
        element = factory.create_element(element_data)
        assert element["text"] == malicious_text

        # The key is that we don't execute or interpret the text as code
        # Frontend should handle XSS prevention during rendering

    @pytest.mark.security
    def test_sql_injection_prevention(self, security_test_data):
        """Test that SQL injection attempts are handled safely."""
        factory = ElementFactory()

        malicious_text = security_test_data["sql_injection"]
        element_data = {"type": "text", "x": 100, "y": 200, "text": malicious_text}

        # Should not raise any database-related errors (we don't use SQL)
        element = factory.create_element(element_data)
        assert element["text"] == malicious_text

        # Our system uses in-memory storage, not SQL, so injection is not a concern
        # But this test ensures we handle the input safely

    @pytest.mark.security
    def test_oversized_input_handling(self, security_test_data):
        """Test handling of extremely large input data."""
        factory = ElementFactory()

        oversized_text = security_test_data["oversized_data"]
        element_data = {"type": "text", "x": 100, "y": 200, "text": oversized_text}

        # Should handle large inputs without crashing
        # In production, we might want to add size limits
        element = factory.create_element(element_data)
        assert len(element["text"]) == len(oversized_text)

    @pytest.mark.security
    def test_invalid_coordinate_values(self, security_test_data):
        """Test handling of invalid coordinate values like infinity and NaN."""
        factory = ElementFactory()

        invalid_coords = security_test_data["invalid_coords"]
        element_data = {
            "type": "rectangle",
            **invalid_coords,
            "width": 100,
            "height": 100,
        }

        # Should not raise validation errors for these specific values
        # But they should be handled safely
        try:
            element = factory.create_element(element_data)
            # If creation succeeds, coordinates should be converted to float
            assert isinstance(element["x"], int | float)
            assert isinstance(element["y"], int | float)
        except (ValueError, TypeError):
            # This is acceptable - we reject invalid numeric values
            pass

    @pytest.mark.security
    def test_negative_dimensions_security(self, security_test_data):
        """Test that negative dimensions don't cause security issues."""
        factory = ElementFactory()

        negative_dims = security_test_data["negative_dimensions"]
        element_data = {"type": "rectangle", "x": 100, "y": 200, **negative_dims}

        # Should fail validation for negative dimensions
        with pytest.raises(ValueError, match="must be non-negative"):
            factory.validate_element_data(element_data)

    @pytest.mark.security
    def test_malicious_color_values(self, security_test_data):
        """Test handling of malicious color values."""
        factory = ElementFactory()

        for malicious_color in security_test_data["invalid_colors"]:
            element_data = {
                "type": "rectangle",
                "x": 100,
                "y": 200,
                "strokeColor": malicious_color,
            }

            # Should fail validation for invalid colors
            with pytest.raises(ValueError, match="Invalid.*Color"):
                factory.validate_element_data(element_data)

    @pytest.mark.security
    def test_unicode_attack_prevention(self, security_test_data):
        """Test handling of unicode-based attacks."""
        factory = ElementFactory()

        unicode_attack = security_test_data["unicode_attacks"]
        element_data = {"type": "text", "x": 100, "y": 200, "text": unicode_attack}

        # Should handle unicode text safely
        element = factory.create_element(element_data)
        assert element["text"] == unicode_attack

        # Ensure no encoding/decoding issues
        assert len(element["text"]) > 0

    @pytest.mark.security
    def test_type_confusion_attacks(self):
        """Test prevention of type confusion attacks."""
        factory = ElementFactory()

        # Try to pass unexpected data types
        attack_data = [
            {"type": ["array", "instead", "of", "string"], "x": 100, "y": 200},
            {"type": {"object": "instead of string"}, "x": 100, "y": 200},
            {"type": 12345, "x": 100, "y": 200},  # Number instead of string
            {"type": None, "x": 100, "y": 200},  # None value
        ]

        for malicious_data in attack_data:
            # Should fail validation for invalid types
            with pytest.raises((ValueError, TypeError)):
                factory.validate_element_data(malicious_data)

    @pytest.mark.security
    def test_numeric_overflow_prevention(self):
        """Test prevention of numeric overflow attacks."""
        factory = ElementFactory()

        overflow_values = [
            {"x": 10**100, "y": 200},  # Very large number
            {"x": 100, "y": -(10**100)},  # Very large negative
            {"strokeWidth": 10**50},  # Overflow in stroke width
            {"opacity": 10**20},  # Overflow in opacity
        ]

        for overflow_data in overflow_values:
            element_data = {"type": "rectangle", "x": 100, "y": 200, **overflow_data}

            # Should either handle gracefully or reject with validation error
            try:
                factory.validate_element_data(element_data)
                element = factory.create_element(element_data)
                # If it succeeds, values should be reasonable
                if "strokeWidth" in overflow_data:
                    assert element["strokeWidth"] <= 50  # Max allowed
                if "opacity" in overflow_data:
                    assert element["opacity"] <= 100  # Max allowed
            except (ValueError, OverflowError):
                # This is acceptable - we reject overflow values
                pass

    @pytest.mark.security
    def test_prototype_pollution_prevention(self):
        """Test prevention of prototype pollution attacks."""
        factory = ElementFactory()

        # Attempt prototype pollution patterns
        malicious_data = {
            "type": "rectangle",
            "x": 100,
            "y": 200,
            "__proto__": {"malicious": "value"},
            "constructor": {"prototype": {"polluted": True}},
            "prototype": {"dangerous": "property"},
        }

        # Should ignore non-element properties
        element = factory.create_element(malicious_data)

        # Ensure no prototype pollution occurred
        assert "__proto__" not in element
        assert "constructor" not in element
        assert "prototype" not in element

        # Only valid element properties should be present
        expected_keys = {
            "id",
            "type",
            "x",
            "y",
            "width",
            "height",
            "version",
            "createdAt",
            "updatedAt",
            "locked",
            "strokeColor",
            "backgroundColor",
            "strokeWidth",
            "opacity",
            "roughness",
        }
        assert set(element.keys()).issubset(expected_keys)

    @pytest.mark.security
    def test_injection_in_element_ids(self):
        """Test handling of potentially malicious element IDs in updates."""
        factory = ElementFactory()

        malicious_ids = [
            "../../../etc/passwd",
            "javascript:alert(1)",
            "<script>alert('xss')</script>",
            "'; DROP TABLE elements; --",
            "null\x00byte",
            "../../sensitive/file",
        ]

        for malicious_id in malicious_ids:
            update_data = {"id": malicious_id, "x": 150, "y": 250}

            # Should handle malicious IDs safely
            # The ID is used as-is since we don't use it for file paths or SQL
            result = factory.prepare_update_data(update_data)
            assert result["id"] == malicious_id

            # Key is that we don't use IDs for dangerous operations
            # like file access or database queries

    @pytest.mark.security
    def test_deep_nested_object_attack(self):
        """Test handling of deeply nested objects (DoS prevention)."""
        factory = ElementFactory()

        # Create deeply nested object
        deep_object = {}
        current = deep_object
        for i in range(1000):  # Very deep nesting
            current["nested"] = {}
            current = current["nested"]
        current["value"] = "deep"

        element_data = {
            "type": "rectangle",
            "x": 100,
            "y": 200,
            "malicious_nested": deep_object,
        }

        # Should handle without stack overflow or excessive processing
        # The deep_object should be ignored as it's not a valid element property
        element = factory.create_element(element_data)
        assert "malicious_nested" not in element

    @pytest.mark.security
    @pytest.mark.slow
    def test_algorithmic_complexity_attack(self):
        """Test prevention of algorithmic complexity attacks."""
        factory = ElementFactory()

        # Create element with many properties (potential DoS)
        attack_data = {"type": "rectangle", "x": 100, "y": 200}

        # Add many fake properties
        for i in range(10000):
            attack_data[f"fake_prop_{i}"] = f"value_{i}"

        # Should handle efficiently without timing attack
        import time

        start_time = time.time()

        element = factory.create_element(attack_data)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should complete reasonably quickly (under 1 second)
        assert processing_time < 1.0

        # Only valid properties should be in the element
        fake_props = [k for k in element.keys() if k.startswith("fake_prop_")]
        assert len(fake_props) == 0
