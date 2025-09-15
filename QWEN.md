# Excalidraw MCP Server - Project Context

## Project Overview

This is a dual-language MCP (Model Context Protocol) server that combines Excalidraw's powerful drawing capabilities with AI integration, enabling AI agents like Claude to create and manipulate diagrams in real-time on a live canvas.

### Key Features

- **Live Canvas**: Real-time Excalidraw canvas accessible via web browser
- **AI Integration**: MCP server allows AI agents to create visual diagrams
- **Real-time Sync**: Elements created via MCP API appear instantly on the canvas
- **WebSocket Updates**: Live synchronization across multiple connected clients
- **Production Ready**: Clean, minimal UI suitable for end users

### Architecture

The system uses a hybrid architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Agent      │───▶│   MCP Server     │───▶│  Canvas Server  │
│   (Claude)      │    │    (Python)      │    │ (Express.js)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │  Frontend       │
                                               │  (React + WS)   │
                                               └─────────────────┘
```

**Benefits:**

- **Python FastMCP**: Handles MCP protocol, tool registration, and auto-manages canvas server
- **TypeScript Canvas**: Express.js API + WebSocket for real-time canvas synchronization
- **Auto-Management**: Python server monitors and restarts canvas server as needed
- **Type Safety**: Comprehensive TypeScript definitions ensure consistency across the stack

## Project Structure

```
excalidraw-mcp/
├── excalidraw_mcp/           # Python FastMCP server
│   ├── server.py            # Main MCP server (Python)
│   ├── config.py            # Configuration management
│   ├── element_factory.py   # Element creation utilities
│   ├── http_client.py       # HTTP client for canvas server
│   └── process_manager.py   # Canvas server lifecycle management
├── frontend/                # React frontend
│   ├── src/
│   │   ├── App.tsx          # Main React component (TypeScript)
│   │   └── main.tsx         # React entry point (TypeScript)
│   └── index.html           # HTML template
├── src/                     # TypeScript canvas server
│   ├── server.ts            # Express server + WebSocket (TypeScript)
│   ├── types.ts             # Type definitions
│   └── utils/
│       └── logger.ts        # Logging utilities
├── dist/                    # Compiled TypeScript output
│   ├── server.js            # Compiled canvas server
│   ├── types.js             # Compiled type definitions
│   └── frontend/            # Built React frontend
├── tests/                   # Python test suite
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   ├── security/            # Security tests
│   └── performance/         # Performance tests
├── pyproject.toml           # Python project configuration
├── package.json             # Node.js dependencies
├── tsconfig.json            # TypeScript configuration
└── README.md                # Documentation
```

## Technology Stack

### Backend (Python)

- **FastMCP**: Python framework for building MCP servers
- **HTTPX**: Async HTTP client with HTTP/2 support
- **Pydantic**: Data validation and settings management
- **Psutil**: System and process utilities
- **PyJWT**: JSON Web Token implementation

### Frontend/Canvas Server (TypeScript)

- **Express.js**: Web framework for REST API
- **WebSocket**: Real-time communication
- **React**: Frontend UI framework
- **Excalidraw**: Official Excalidraw package for drawing
- **Zod**: TypeScript-first schema validation

## Development Setup

### Prerequisites

- Python 3.13+
- Node.js 16+
- UV package manager for Python

### Installation

```bash
# Clone and setup
git clone https://github.com/lesleslie/excalidraw-mcp.git
cd excalidraw-mcp

# Install Python dependencies
uv sync

# Install Node.js dependencies and build
npm install
npm run build
```

### Running the System

```bash
# The Python MCP server auto-starts the canvas server
uv run python excalidraw_mcp/server.py

# Or manually start canvas server (optional)
npm run canvas
```

### Development Commands

```bash
# Development mode (TypeScript watch + Vite dev server)
npm run dev

# Production mode
npm run production

# Type checking
npm run type-check

# Testing
pytest
npm test
```

## Key Components

### 1. Python MCP Server (`excalidraw_mcp/server.py`)

- Main entry point for the MCP server
- Uses FastMCP framework for MCP protocol handling
- Automatically manages the canvas server lifecycle
- Exposes tools for AI agents to create and manipulate diagrams

### 2. Canvas Server (`src/server.ts`)

- Express.js server with REST API endpoints
- WebSocket server for real-time updates
- In-memory storage for Excalidraw elements
- Serves the React frontend

### 3. React Frontend (`frontend/src/App.tsx`)

- Excalidraw canvas component
- WebSocket client for real-time synchronization
- UI controls for connection status and canvas management
- Manual sync functionality to backend

### 4. Configuration (`excalidraw_mcp/config.py`)

- Centralized configuration management
- Environment variable support
- Validation for all configuration values
- Separate sections for security, server, performance, and logging

### 5. HTTP Client (`excalidraw_mcp/http_client.py`)

- Async HTTP client with connection pooling
- Health check caching
- Retry mechanisms for failed requests
- Communication with canvas server

### 6. Process Manager (`excalidraw_mcp/process_manager.py`)

- Lifecycle management for canvas server process
- Automatic startup and health monitoring
- Graceful shutdown handling
- Process cleanup on exit

### 7. Element Factory (`excalidraw_mcp/element_factory.py`)

- Creation and validation of Excalidraw elements
- Default value handling
- Type-specific property management
- Element data validation

## MCP Tools Available

### Element Management

- `create_element` - Create any type of Excalidraw element
- `update_element` - Modify existing elements
- `delete_element` - Remove elements
- `query_elements` - Search elements with filters

### Batch Operations

- `batch_create_elements` - Create complex diagrams in one call

### Element Organization

- `group_elements` - Group multiple elements
- `ungroup_elements` - Ungroup element groups
- `align_elements` - Align elements (left, center, right, top, middle, bottom)
- `distribute_elements` - Distribute elements evenly
- `lock_elements` / `unlock_elements` - Lock/unlock elements

### Resource Access

- `get_resource` - Access scene, library, theme, or elements data

## API Endpoints

### Canvas Server REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/elements` | Get all elements |
| `POST` | `/api/elements` | Create new element |
| `PUT` | `/api/elements/:id` | Update element |
| `DELETE` | `/api/elements/:id` | Delete element |
| `POST` | `/api/elements/batch` | Create multiple elements |
| `GET` | `/health` | Server health check |

### WebSocket Events

- `initial_elements` - Sent when client connects with current elements
- `element_created` - Element created on canvas
- `element_updated` - Element updated on canvas
- `element_deleted` - Element deleted from canvas
- `elements_batch_created` - Multiple elements created
- `elements_synced` - Elements synced from frontend
- `sync_status` - Current sync status

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EXPRESS_SERVER_URL` | `http://localhost:3031` | Canvas server URL for MCP sync |
| `ENABLE_CANVAS_SYNC` | `true` | Enable/disable canvas synchronization |
| `CANVAS_AUTO_START` | `true` | Auto-start canvas server with MCP server |
| `PORT` | `3031` | Canvas server port |
| `HOST` | `localhost` | Canvas server host |
| `DEBUG` | `false` | Enable debug logging |

## Testing

### Test Structure

- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **Security Tests**: Security vulnerability testing
- **Performance Tests**: Performance benchmarking
- **End-to-End Tests**: Complete system workflow testing

### Running Tests

```bash
# Python tests with coverage
pytest --cov=excalidraw_mcp --cov-report=html

# TypeScript tests with coverage
npm run test:coverage

# Run all tests
pytest && npm test

# Specific test categories
pytest tests/unit/                  # Python unit tests
pytest tests/integration/           # Python integration tests
npm run test:unit                   # TypeScript unit tests
```

### Quality Standards

- **Coverage Requirements**: 85% minimum for Python, 70% for TypeScript
- **Type Checking**: All code must pass Pyright (Python) and TSC (TypeScript)
- **Security**: Scanning with Bandit for Python
- **Linting**: Ruff for Python, built-in TypeScript rules
- **Formatting**: Consistent formatting enforced

## Build Process

### TypeScript Compilation

```bash
# Build server only
npm run build:server

# Build frontend only
npm run build:frontend

# Build both
npm run build
```

### Development Workflow

1. **Development Server**: `npm run dev` starts both TypeScript watch and Vite dev server
1. **Type Checking**: `npm run type-check` validates TypeScript without compilation
1. **Production Build**: `npm run production` builds and starts the system

## Deployment

### Package Naming

- **Python Package**: `excalidraw_mcp` (underscore) - used in imports
- **PyPI Distribution**: `excalidraw-mcp` (hyphen) - used for `uvx excalidraw-mcp`
- **npm Package**: `excalidraw-mcp` (hyphen) - used for Node.js dependencies
- **MCP Server Name**: `excalidraw` - used in .mcp.json configuration

### Publishing

The Python package is published to PyPI as `excalidraw-mcp`:

```bash
# Install from PyPI
pip install excalidraw-mcp

# Use with uvx (recommended)
uvx excalidraw-mcp
```

## Integration with AI Tools

### Claude Code Integration

Add this configuration to your Claude Code `.mcp.json`:

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

### Other Tools

Similar configurations work for Cursor IDE, VS Code MCP Extension, and other MCP-compatible tools.

## Troubleshooting

### Canvas Not Loading

- Ensure `npm run build` completed successfully
- Verify canvas server is running on port 3031
- Python MCP server auto-starts canvas server - check console for errors

### Elements Not Syncing

- Python server automatically manages canvas server
- Check `ENABLE_CANVAS_SYNC=true` in environment
- Verify canvas server health at `http://localhost:3031/health`

### WebSocket Connection Issues

- Check browser console for WebSocket errors
- Ensure no firewall blocking WebSocket connections
- Try refreshing the browser page

### Build Errors

- Delete `node_modules` and run `npm install`
- Check Node.js version (requires 16+)
- Run `npm run type-check` to identify TypeScript issues
- Run `uv sync` to update Python dependencies

### Python Dependencies

- Use `uv sync` to install/update Python dependencies
- Ensure Python 3.13+ is installed
- Check `uv --version` to verify uv installation
