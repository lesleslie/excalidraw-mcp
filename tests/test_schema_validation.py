"""Schema validation tests for Pydantic models.

This module provides schema validation tests to ensure Pydantic models
properly handle extra fields from API responses (extra="ignore" or extra="allow").

Current Status:
    The excalidraw-mcp project currently uses dataclasses for configuration
    and plain dict[str, Any] for element data. No Pydantic models exist yet.

    When Pydantic models are introduced, this test file should be updated
    to include tests for each model type.

Reference:
    Models should be created in: excalidraw_mcp/models/
    Test fixtures should be added to: tests/fixtures/api_responses/

Template for adding tests when models are created:
    1. Import the model from excalidraw_mcp.models
    2. Create a test class named Test{ModelName}Validation
    3. Add test_extra_fields_ignored method
    4. Add test_model_has_extra_ignore method
    5. Add fixtures with sample API response data
"""

from __future__ import annotations

import pytest


class TestSchemaValidationStatus:
    """Document current schema validation status and provide templates."""

    def test_no_pydantic_models_currently_exist(self) -> None:
        """Verify that no Pydantic models currently exist in the project.

        This test documents the current state and should be updated or removed
        when Pydantic models are added to the project.
        """
        # Currently, the project uses dataclasses for configuration
        # and dict[str, Any] for element data.
        # When Pydantic models are added, this test should be removed
        # and replaced with model-specific tests.
        assert True, "No Pydantic models exist - test serves as documentation"


# =============================================================================
# TEMPLATE: Copy and customize when Pydantic models are added
# =============================================================================

TEMPLATE_CODE = '''
"""
Example template for Pydantic model validation tests.

When Pydantic models are created, follow this pattern for each model:
"""

from pydantic import BaseModel, ConfigDict, Field
import pytest


class SampleElementModel(BaseModel):
    """Example model - replace with actual model when created."""

    model_config = ConfigDict(extra="ignore")

    id: str
    type: str
    x: float = 0.0
    y: float = 0.0
    width: float | None = None
    height: float | None = None


class TestSampleElementModelValidation:
    """Validation tests for SampleElementModel - TEMPLATE."""

    @pytest.fixture
    def sample_api_response(self) -> dict[str, object]:
        """Sample API response with all expected fields."""
        return {
            "id": "abc123",
            "type": "rectangle",
            "x": 100.0,
            "y": 200.0,
            "width": 150.0,
            "height": 75.0,
        }

    @pytest.fixture
    def api_response_with_extra_fields(self) -> dict[str, object]:
        """API response with extra fields that should be ignored."""
        return {
            "id": "xyz789",
            "type": "ellipse",
            "x": 50.0,
            "y": 75.0,
            "width": 100.0,
            "height": 100.0,
            # Extra fields that API might return
            "version": 5,
            "createdAt": "2025-01-15T10:30:00Z",
            "updatedAt": "2025-01-16T14:45:00Z",
            "isNew": True,
            "customMetadata": {"key": "value"},
            "futureField": "not yet defined in model",
        }

    def test_model_accepts_required_fields(
        self, sample_api_response: dict[str, object]
    ) -> None:
        """Test that model accepts all required and optional fields."""
        model = SampleElementModel(**sample_api_response)

        assert model.id == "abc123"
        assert model.type == "rectangle"
        assert model.x == 100.0
        assert model.y == 200.0
        assert model.width == 150.0
        assert model.height == 75.0

    def test_extra_fields_ignored(
        self, api_response_with_extra_fields: dict[str, object]
    ) -> None:
        """Test that extra fields from API are ignored without error.

        This ensures forward compatibility when the API adds new fields
        that the current model version doesn't recognize.
        """
        # Should not raise ValidationError
        model = SampleElementModel(**api_response_with_extra_fields)

        # Core fields should be parsed correctly
        assert model.id == "xyz789"
        assert model.type == "ellipse"

        # Extra fields should not be accessible
        assert not hasattr(model, "version")
        assert not hasattr(model, "createdAt")
        assert not hasattr(model, "futureField")

    def test_model_has_extra_ignore(self) -> None:
        """Test that model_config has extra='ignore' or extra='allow'.

        Models handling external API data should use extra='ignore' to:
        - Prevent validation errors from unknown fields
        - Maintain forward compatibility with API changes
        - Avoid silently dropping data (use 'forbid' only for internal models)
        """
        config = SampleElementModel.model_config

        # Check that extra is set to ignore or allow
        extra = config.get("extra")
        assert extra in ("ignore", "allow"), (
            f"Model should have extra='ignore' or extra='allow' for API "
            f"compatibility, got extra={extra!r}"
        )

    def test_model_rejects_missing_required_fields(self) -> None:
        """Test that model rejects data missing required fields."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            SampleElementModel()  # Missing required 'id' and 'type'

        errors = exc_info.value.errors()
        error_fields = {e["loc"][0] for e in errors}
        assert "id" in error_fields
        assert "type" in error_fields
'''


class TestSchemaValidationTemplate:
    """Tests for the schema validation template itself."""

    def test_template_includes_extra_ignore_test(self) -> None:
        """Verify template includes test for extra fields ignored."""
        assert "test_extra_fields_ignored" in TEMPLATE_CODE

    def test_template_includes_config_test(self) -> None:
        """Verify template includes test for model_config extra setting."""
        assert "test_model_has_extra_ignore" in TEMPLATE_CODE

    def test_template_includes_fixtures(self) -> None:
        """Verify template includes sample API response fixtures."""
        assert "sample_api_response" in TEMPLATE_CODE
        assert "api_response_with_extra_fields" in TEMPLATE_CODE


# =============================================================================
# Expected Models (Add tests here when models are created)
# =============================================================================

# When Pydantic models are added, create test classes for each:
#
# - Element models (rectangle, ellipse, text, line, arrow, etc.)
# - Scene/Canvas models
# - API request/response models
# - WebSocket message models
# - Configuration models (if migrated from dataclasses)
#
# Model locations to check:
# - excalidraw_mcp/models/elements.py
# - excalidraw_mcp/models/scene.py
# - excalidraw_mcp/models/api.py
# - excalidraw_mcp/models/websocket.py


@pytest.mark.unit
class TestFutureModelValidation:
    """Placeholder for future Pydantic model validation tests.

    When Pydantic models are introduced:
    1. Move this class contents to separate test class per model
    2. Import actual models from excalidraw_mcp.models
    3. Add model-specific fixtures and tests
    """

    @pytest.mark.skip(reason="No Pydantic models exist yet")
    def test_element_model_extra_fields_ignored(self) -> None:
        """Test that element models ignore extra fields from API."""
        pass

    @pytest.mark.skip(reason="No Pydantic models exist yet")
    def test_scene_model_extra_fields_ignored(self) -> None:
        """Test that scene models ignore extra fields from API."""
        pass

    @pytest.mark.skip(reason="No Pydantic models exist yet")
    def test_api_response_model_extra_fields_ignored(self) -> None:
        """Test that API response models ignore extra fields."""
        pass

    @pytest.mark.skip(reason="No Pydantic models exist yet")
    def test_websocket_message_model_extra_fields_ignored(self) -> None:
        """Test that WebSocket message models ignore extra fields."""
        pass
