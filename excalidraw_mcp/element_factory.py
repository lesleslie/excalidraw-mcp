"""Element factory for creating and managing Excalidraw elements."""

import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ElementFactory:
    """Factory for creating and managing Excalidraw elements."""

    def __init__(self):
        self.default_timestamp = "2025-01-01T00:00:00.000Z"

    def create_element(self, element_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new element with proper defaults and validation."""
        # Generate unique ID
        element_id = str(uuid.uuid4())

        # Get current timestamp
        current_time = datetime.utcnow().isoformat() + "Z"

        # Base element structure
        element = {
            "id": element_id,
            "type": element_data.get("type", "rectangle"),
            "x": float(element_data.get("x", 0)),
            "y": float(element_data.get("y", 0)),
            "width": self._get_optional_float(element_data, "width"),
            "height": self._get_optional_float(element_data, "height"),
            "version": 1,
            "createdAt": current_time,
            "updatedAt": current_time,
            "locked": element_data.get("locked", False),
        }

        # Add optional properties
        self._add_optional_properties(element, element_data)

        return element

    def prepare_update_data(self, update_data: dict[str, Any]) -> dict[str, Any]:
        """Prepare element data for updates."""
        # Remove ID from update data (handled separately)
        element_id = update_data.pop("id", None)
        if not element_id:
            raise ValueError("Element ID is required for updates")

        # Increment version and update timestamp
        current_time = datetime.utcnow().isoformat() + "Z"

        # Prepare update payload
        update_payload = {"id": element_id, "updatedAt": current_time}

        # Add provided updates
        for key, value in update_data.items():
            if key not in ["createdAt", "version"]:  # Protect immutable fields
                if key in [
                    "x",
                    "y",
                    "width",
                    "height",
                    "strokeWidth",
                    "opacity",
                    "roughness",
                    "fontSize",
                ]:
                    update_payload[key] = float(value) if value is not None else value
                else:
                    update_payload[key] = value

        return update_payload

    def _add_optional_properties(
        self, element: dict[str, Any], element_data: dict[str, Any]
    ) -> None:
        """Add optional properties to element based on type."""
        element_type = element["type"]

        # Text properties
        if element_type == "text" or element_data.get("text"):
            element["text"] = element_data.get("text", "")
            element["fontSize"] = self._get_optional_float(element_data, "fontSize", 16)
            element["fontFamily"] = element_data.get("fontFamily", "Cascadia, Consolas")

        # Visual properties
        self._add_visual_properties(element, element_data)

        # Shape-specific properties
        if element_type in ["rectangle", "ellipse", "diamond"]:
            self._add_shape_properties(element, element_data)
        elif element_type in ["line", "arrow"]:
            self._add_line_properties(element, element_data)

    def _add_visual_properties(
        self, element: dict[str, Any], element_data: dict[str, Any]
    ) -> None:
        """Add visual styling properties."""
        element["strokeColor"] = element_data.get("strokeColor", "#000000")
        element["backgroundColor"] = element_data.get("backgroundColor", "#ffffff")
        element["strokeWidth"] = self._get_optional_float(
            element_data, "strokeWidth", 2
        )
        element["opacity"] = self._get_optional_float(element_data, "opacity", 100)
        element["roughness"] = self._get_optional_float(element_data, "roughness", 1)

    def _add_shape_properties(
        self, element: dict[str, Any], element_data: dict[str, Any]
    ) -> None:
        """Add properties specific to shapes (rectangles, ellipses, diamonds)."""
        # Default dimensions for shapes
        if element["width"] is None:
            element["width"] = 100.0
        if element["height"] is None:
            element["height"] = 100.0

    def _add_line_properties(
        self, element: dict[str, Any], element_data: dict[str, Any]
    ) -> None:
        """Add properties specific to lines and arrows."""
        # Lines typically don't have fill
        element["backgroundColor"] = "transparent"

        # Default line endpoints (if not provided, create a simple horizontal line)
        if element["width"] is None:
            element["width"] = 100.0
        if element["height"] is None:
            element["height"] = 0.0

    def _get_optional_float(
        self, data: dict[str, Any], key: str, default: float | None = None
    ) -> float | None:
        """Get an optional float value from data."""
        value = data.get(key, default)
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid float value for {key}: {value}")
            return default

    def validate_element_data(self, element_data: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalize element data."""
        errors = []

        # Required fields
        if "type" not in element_data:
            errors.append("Element type is required")

        # Validate type
        self._validate_element_type(element_data, errors)

        # Validate coordinates
        self._validate_coordinates(element_data, errors)

        # Validate dimensions
        self._validate_dimensions(element_data, errors)

        # Validate colors
        self._validate_colors(element_data, errors)

        # Validate numeric ranges
        self._validate_numeric_ranges(element_data, errors)

        if errors:
            raise ValueError(f"Element validation failed: {'; '.join(errors)}")

        return element_data

    def _validate_element_type(
        self, element_data: dict[str, Any], errors: list
    ) -> None:
        """Validate element type."""
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
        if element_data.get("type") not in valid_types:
            errors.append(
                f"Invalid element type. Must be one of: {', '.join(valid_types)}"
            )

    def _validate_coordinates(self, element_data: dict[str, Any], errors: list) -> None:
        """Validate coordinates."""
        for coord in ["x", "y"]:
            if coord in element_data:
                try:
                    float(element_data[coord])
                except (ValueError, TypeError):
                    errors.append(f"Invalid {coord} coordinate: must be a number")

    def _validate_dimensions(self, element_data: dict[str, Any], errors: list) -> None:
        """Validate dimensions."""
        for dimension in ["width", "height"]:
            if dimension in element_data and element_data[dimension] is not None:
                try:
                    value = float(element_data[dimension])
                    if value < 0:
                        errors.append(f"Invalid {dimension}: must be non-negative")
                except (ValueError, TypeError):
                    errors.append(f"Invalid {dimension}: must be a number")

    def _is_valid_color(self, color: str) -> bool:
        """Validate hex color format."""
        if not isinstance(color, str):
            return False

        # Allow transparent
        if color.lower() == "transparent":
            return True

        # Check hex color format
        if color.startswith("#") and len(color) == 7:
            try:
                int(color[1:], 16)
                return True
            except ValueError:
                return False

        return False

    def _validate_colors(self, element_data: dict[str, Any], errors: list) -> None:
        """Validate colors."""
        for color_prop in ["strokeColor", "backgroundColor"]:
            if color_prop in element_data:
                color = element_data[color_prop]
                if color and not self._is_valid_color(color):
                    errors.append(f"Invalid {color_prop}: must be a valid hex color")

    def _validate_numeric_ranges(
        self, element_data: dict[str, Any], errors: list
    ) -> None:
        """Validate numeric properties are within acceptable ranges."""
        # Stroke width
        if "strokeWidth" in element_data:
            try:
                stroke_width = float(element_data["strokeWidth"])
                if not (0 <= stroke_width <= 50):
                    errors.append("strokeWidth must be between 0 and 50")
            except (ValueError, TypeError):
                errors.append("strokeWidth must be a number")

        # Opacity
        if "opacity" in element_data:
            try:
                opacity = float(element_data["opacity"])
                if not (0 <= opacity <= 100):
                    errors.append("opacity must be between 0 and 100")
            except (ValueError, TypeError):
                errors.append("opacity must be a number")

        # Roughness
        if "roughness" in element_data:
            try:
                roughness = float(element_data["roughness"])
                if not (0 <= roughness <= 3):
                    errors.append("roughness must be between 0 and 3")
            except (ValueError, TypeError):
                errors.append("roughness must be a number")

        # Font size
        if "fontSize" in element_data:
            try:
                font_size = float(element_data["fontSize"])
                if not (8 <= font_size <= 200):
                    errors.append("fontSize must be between 8 and 200")
            except (ValueError, TypeError):
                errors.append("fontSize must be a number")
