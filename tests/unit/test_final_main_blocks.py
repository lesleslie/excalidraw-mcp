"""Test to cover the final missing lines in __main__.py and server.py"""



def test_main_blocks_execute():
    """Test that main blocks in modules execute without error."""
    # Test __main__.py by directly importing and verifying the main function exists
    # The if __name__ == "__main__": guard is tested by importing the module
    import excalidraw_mcp.__main__ as main_module

    # Verify main() function exists and is callable
    assert hasattr(main_module, 'main')
    assert callable(main_module.main)

    # Test that we can call main() with proper mocking to avoid actual server startup
    from unittest.mock import Mock, patch

    # Mock all the dependencies that would start actual services
    with patch('excalidraw_mcp.__main__.MCPServerCLIFactory') as mock_factory:
        mock_instance = Mock()
        mock_app = Mock()
        mock_factory.create_server_cli.return_value = mock_instance
        mock_instance.create_app.return_value = lambda: mock_app()

        # Call main - it should complete without hanging
        main_module.main()

        # Verify the CLI factory was called correctly
        mock_factory.create_server_cli.assert_called_once_with(
            server_class=main_module.ExcalidrawMCPServer,
            config_class=main_module.ExcalidrawConfig,
            name="excalidraw-mcp",
        )
        mock_instance.create_app.assert_called_once()
        mock_app.assert_called_once()

    # Test server.py main() function with proper mocking
    with patch('excalidraw_mcp.server.mcp') as mock_mcp, \
         patch('excalidraw_mcp.server.init_background_services'), \
         patch('excalidraw_mcp.server.SERVERPANELS_AVAILABLE', False):

        # Mock the run method to prevent server startup
        mock_mcp.run = Mock()

        # Import and call main()
        from excalidraw_mcp.server import main
        main()

        # Verify mcp.run was called
        mock_mcp.run.assert_called_once()
