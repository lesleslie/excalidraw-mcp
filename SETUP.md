# Excalidraw MCP Server Setup

This project provides a dual-language MCP server for Claude Code integration with a live Excalidraw canvas interface.

## Architecture

- **Python FastMCP Server** (`excalidraw_mcp/server.py`): Handles MCP protocol and tool registration
- **TypeScript Canvas Server** (`src/server.ts`): Express.js server with WebSocket for canvas management
- **React Frontend** (`frontend/src/App.tsx`): Live Excalidraw canvas interface
- **Auto-Management**: Python server automatically manages TypeScript server lifecycle

## Quick Start

### Setup Dependencies
```bash
# Install Python dependencies
uv sync

# Install Node.js dependencies
npm install

# Build TypeScript canvas server
npm run build
```

### Development Mode
```bash
# Start development servers (TypeScript watch + Vite dev)
npm run dev

# Or build and start canvas server
npm run production
```

### Individual Services
```bash
# Canvas server only (port 3031)
npm run canvas

# Python MCP server (auto-manages canvas server)
uv run python excalidraw_mcp/server.py
```

## Claude Code Integration

### Option A: Published Package (Recommended)
```json
{
  "excalidraw": {
    "command": "uvx",
    "args": ["excalidraw-mcp"],
    "env": {
      "EXPRESS_SERVER_URL": "http://localhost:3031",
      "ENABLE_CANVAS_SYNC": "true"
    }
  }
}
```

### Option B: Local Development Configuration
```json
{
  "excalidraw": {
    "command": "uv",
    "args": ["run", "python", "excalidraw_mcp/server.py"],
    "cwd": "/path/to/excalidraw-mcp"
  }
}
```

**Setup Steps:**
1. **Canvas Server**: The Python MCP server automatically starts the canvas server on first tool use
2. **Environment**: Default connection to `http://localhost:3031` with auto-start enabled
3. **Health Monitoring**: Python server continuously monitors and restarts canvas server if needed

## Available MCP Tools

- `create_element`: Create shapes, text, lines, etc.
- `update_element`: Modify existing elements
- `delete_element`: Remove elements
- `query_elements`: Search and filter elements
- `batch_create_elements`: Create multiple elements efficiently
- `group_elements`/`ungroup_elements`: Manage element groups
- `align_elements`/`distribute_elements`: Layout operations
- `lock_elements`/`unlock_elements`: Element protection
- `get_resource`: Access scene, elements, library data

## URLs

- **Canvas Frontend**: http://localhost:3031
- **Health Check**: http://localhost:3031/health
- **REST API**: http://localhost:3031/api/elements
- **WebSocket**: ws://localhost:3031

## Configuration

Environment variables:
```bash
# Canvas server configuration
PORT=3031
HOST=localhost
EXPRESS_SERVER_URL=http://localhost:3031
ENABLE_CANVAS_SYNC=true
CANVAS_AUTO_START=true

# Development settings
DEBUG=false
```

## Testing & Quality Assurance

### Coverage Requirements
- **Python**: 85% minimum coverage (enforced by pyproject.toml)
- **TypeScript**: 70% minimum coverage (enforced by jest.config.cjs)

### Python Testing Commands

```bash
# Run all Python tests
pytest

# Run with coverage report
pytest --cov=excalidraw_mcp --cov-report=html
pytest --cov=excalidraw_mcp --cov-report=term-missing

# Test categories
pytest tests/unit/                  # Unit tests only
pytest tests/integration/           # Integration tests only
pytest tests/security/              # Security-focused tests
pytest tests/performance/           # Performance benchmarks

# Test markers
pytest -m "not slow"               # Skip slow performance tests
pytest -m security                 # Run only security tests
pytest -m performance              # Run only performance tests

# Specific test file
pytest tests/test_config.py -v     # Verbose output for single file

# Debug failing test
pytest tests/test_http_client.py::test_specific_function -v -s
```

### TypeScript Testing Commands

```bash
# Run all TypeScript tests
npm test

# Run with coverage
npm run test:coverage

# Test categories
npm run test:unit                   # Unit tests only
npm run test:integration            # Integration tests only

# Watch mode for development
npm run test:watch

# Specific test pattern
npx jest --testNamePattern="ElementStorage"
npx jest test/unit/delta-compression.test.ts
```

### Development Commands

```bash
# Type checking and linting
npm run type-check                 # TypeScript type validation
uv run ruff check excalidraw_mcp    # Python linting

# Build commands
npm run build                      # Build frontend + canvas server
npm run build:frontend             # Build React frontend only
npm run build:server               # Build Express server only

# Development servers
npm run dev                        # TypeScript watch + Vite dev server
npm run canvas                     # Start canvas server only
```

## Debugging & Troubleshooting

### Common Issues

#### MCP Server Connection Problems

**Issue**: MCP server not connecting or tools not available in Claude Code
```bash
# Check MCP configuration
cat .mcp.json  # Verify "excalidraw" server configuration

# Test manual server startup
uv run python excalidraw_mcp/server.py

# Verify package installation
uvx excalidraw-mcp --help
```

**Solution**: Ensure `.mcp.json` contains:
```json
{
  "mcpServers": {
    "excalidraw": {
      "command": "uvx",
      "args": ["excalidraw-mcp"],
      "env": {
        "EXPRESS_SERVER_URL": "http://localhost:3031",
        "ENABLE_CANVAS_SYNC": "true"
      }
    }
  }
}
```

#### Canvas Server Issues

**Issue**: Canvas not loading or elements not syncing
```bash
# Check canvas server health
curl http://localhost:3031/health

# Manual canvas server startup
npm run canvas

# Check WebSocket connection
curl -i -N -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Version: 13" \
     -H "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
     http://localhost:3031
```

**Solution**: 
- Python MCP server automatically manages canvas server
- Check console logs for startup errors
- Verify port 3031 is not in use by other services
- Set `DEBUG=true` environment variable for detailed logging

#### Build and Development Issues

**Issue**: TypeScript compilation errors or build failures
```bash
# Clean and rebuild
rm -rf dist/ node_modules/ && npm install && npm run build

# Check TypeScript configuration
npm run type-check

# Verify all dependencies are installed
npm ls --depth=0
```

**Issue**: Python import errors or module not found
```bash
# Reinstall Python dependencies
uv sync --reinstall

# Verify Python environment
uv run python -c "import excalidraw_mcp; print('OK')"

# Check UV installation
uv --version
```

### Development Debugging

#### Python MCP Server Debugging

```bash
# Enable debug logging
DEBUG=true uv run python excalidraw_mcp/server.py

# Run with Python debugger
uv run python -m pdb excalidraw_mcp/server.py

# Check FastMCP integration
uv run python -c "
import asyncio
from excalidraw_mcp.server import main
print('MCP server imports successfully')
"
```

#### TypeScript Canvas Server Debugging

```bash
# Enable TypeScript source maps
npm run dev  # Uses --watch flag for debugging

# Debug specific test
npm run test -- --testNamePattern="specific test name" --verbose

# Check Express server startup
DEBUG=express:* npm run canvas
```

#### WebSocket Debugging

```bash
# Monitor WebSocket traffic (requires wscat)
npm install -g wscat
wscat -c ws://localhost:3031

# Test WebSocket with curl
curl --include \
     --no-buffer \
     --header "Connection: Upgrade" \
     --header "Upgrade: websocket" \
     --header "Sec-WebSocket-Version: 13" \
     --header "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
     http://localhost:3031
```

### Testing and Coverage Issues

#### Coverage Problems

```bash
# Check current coverage
pytest --cov=excalidraw_mcp --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=excalidraw_mcp --cov-report=html
open htmlcov/index.html  # View detailed coverage

# TypeScript coverage
npm run test:coverage
open coverage/lcov-report/index.html
```

#### Test Failures

```bash
# Run single failing test with full output
pytest tests/path/to/test.py::test_name -v -s --tb=long

# Run with PDB debugger on failure
pytest tests/path/to/test.py::test_name --pdb

# Skip slow tests during development
pytest -m "not slow"

# Run only fast unit tests
pytest tests/unit/ -v
```

### Environment Variables for Debugging

```bash
# Python/MCP server debugging
export DEBUG=true                    # Enable debug logging
export PYTHONPATH=$PWD               # Ensure module imports work

# Canvas server debugging  
export DEBUG=express:*               # Express.js debug logging
export NODE_ENV=development          # Enable development features

# Testing debugging
export PYTEST_CURRENT_TEST=true      # Show current test in pytest
export JEST_VERBOSE=true             # Verbose Jest output
```

### Log Analysis

#### Python MCP Server Logs
- Server startup and health check status
- HTTP client connection attempts
- MCP tool execution results
- Process management events (canvas server start/stop)

#### TypeScript Canvas Server Logs
- Express server startup on port 3031
- WebSocket connection events
- Element CRUD operations
- CORS and middleware activity

#### WebSocket Communication Logs
- Client connection/disconnection events
- Element synchronization messages
- Error handling and retry attempts
- Message queue status

## Troubleshooting Quick Reference

| Issue | Command | Solution |
|-------|---------|----------|
| Port conflicts | `lsof -i :3031` | Change `PORT` environment variable |
| MCP not connecting | Check `.mcp.json` | Verify `uvx excalidraw-mcp` configuration |
| Canvas sync issues | Check `/health` endpoint | Python server auto-starts canvas server |
| Build failures | `npm run type-check` | Fix TypeScript errors first |
| Python import errors | `uv sync` | Reinstall Python dependencies |
| Test failures | `pytest -v -s` | Run with verbose output and debugging |