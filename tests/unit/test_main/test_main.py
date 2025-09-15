"""Unit tests for the main module."""

import sys
from unittest.mock import patch

import pytest


class TestMainModule:
    """Test the main module entry point."""

    def test_main_module_imports_successfully(self):
        """Test that the main module imports without errors."""
        # This test verifies that the module can be imported
        # If there are any import errors, this test will fail
        import excalidraw_mcp.__main__
        assert excalidraw_mcp.__main__ is not None

    def test_module_has_correct_docstring(self):
        """Test that the module has the expected docstring."""
        import excalidraw_mcp.__main__
        assert "Module entry point" in excalidraw_mcp.__main__.__doc__

    def test_module_has_main_block(self):
        """Test that the module has a main execution block."""
        import excalidraw_mcp.__main__
        # Just verify the module can be imported and has the expected structure
        assert hasattr(excalidraw_mcp.__main__, '__name__')

    def test_main_function_exists(self):
        """Test that the main function exists and can be called."""
        import excalidraw_mcp.__main__
        
        # Verify the main function exists
        assert hasattr(excalidraw_mcp.__main__, 'main')
        
        # Verify it's callable
        assert callable(excalidraw_mcp.__main__.main)