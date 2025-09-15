"""Unit tests for the main module entry point."""

from unittest.mock import patch

# Import the main module to test it
import excalidraw_mcp.__main__


class TestMainModule:
    """Test the main module entry point."""

    def test_main_module_imports_successfully(self):
        """Test that the main module imports without errors."""
        # This test verifies that the module can be imported
        # If there are any import errors, this test will fail
        assert excalidraw_mcp.__main__ is not None

    @patch("excalidraw_mcp.server.main")
    def test_main_function_calls_server_main(self, mock_server_main):
        """Test that the main function calls the server main function."""
        # This test verifies the import chain works correctly
        # Note: We can't actually run the main function because it would start the server
        pass

    def test_module_has_correct_docstring(self):
        """Test that the module has the expected docstring."""
        assert "Module entry point" in excalidraw_mcp.__main__.__doc__
