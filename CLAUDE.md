# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a dual-language MCP (Model Context Protocol) server for Excalidraw that enables AI agents to create and manipulate diagrams in real-time on a live canvas. The system uses a hybrid architecture:

1. **Python FastMCP Server** (`excalidraw_mcp/server.py`) - Handles MCP protocol communication and tool registration
2. **TypeScript Canvas Server** (`src/server.ts`) - Manages canvas state, WebSocket connections, and HTTP API
3. **React Frontend** (`frontend/src/App.tsx`) - Provides the live Excalidraw canvas interface

The Python server automatically manages the TypeScript server lifecycle, including health monitoring, auto-start, and graceful shutdown.

## Architecture

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

**Data Flow Architecture:**
- **MCP Tools** (Python) → **HTTP API** (TypeScript) → **WebSocket** → **Canvas** (React)
- Canvas server maintains in-memory element storage with versioning and timestamp tracking
- Real-time synchronization via WebSocket broadcasts to all connected clients
- Python server monitors canvas server health and automatically restarts if needed
- **Type Safety**: Comprehensive TypeScript definitions in `src/types.ts` ensure type consistency across the entire stack

## Development Commands

### Setup
```bash
# Install Python dependencies
uv sync

# Install Node.js dependencies
npm install

# Build TypeScript canvas server
npm run build

# Start canvas server
npm run canvas

# MCP server runs automatically via uvx when Claude Code connects
```

### Build and Development Commands
```bash
# Build project (frontend + canvas server)
npm run build

# Build individual components
npm run build:frontend  # Vite build for React frontend
npm run build:server    # TypeScript compilation for Express server

# Development modes
npm run dev             # TypeScript watch + Vite dev server (concurrent)
npm run canvas          # Start production canvas server on port 3031
npm run production      # Full build + start canvas server

# Quality assurance
npm run type-check      # TypeScript type checking without compilation
```

### Process Management Commands
```bash
# Python MCP server (auto-manages canvas server)
uv run python excalidraw_mcp/server.py

# Manual canvas server control
npm run canvas          # Start canvas server independently
```

## Environment Configuration

Key environment variables:
- `EXPRESS_SERVER_URL`: Canvas server URL (default: `http://localhost:3031`)
- `ENABLE_CANVAS_SYNC`: Enable/disable canvas synchronization (default: `true`)
- `CANVAS_AUTO_START`: Enable/disable automatic canvas server startup (default: `true`)
- `PORT`: Canvas server port (default: `3031`)
- `HOST`: Canvas server host (default: `localhost`)

## MCP Tools Available

The system provides these MCP tools for diagram creation:

### Element Management
- `create_element`: Create rectangles, ellipses, diamonds, arrows, text, lines
- `update_element`: Modify existing elements
- `delete_element`: Remove elements
- `query_elements`: Search elements with filters

### Batch Operations
- `batch_create_elements`: Create multiple elements in one call

### Element Organization
- `group_elements` / `ungroup_elements`: Group/ungroup elements
- `align_elements`: Align elements (left, center, right, top, middle, bottom)
- `distribute_elements`: Distribute elements evenly
- `lock_elements` / `unlock_elements`: Lock/unlock elements

### Resource Access
- `get_resource`: Access scene, library, theme, or elements data

## Critical Architecture Components

### Python MCP Server (`excalidraw_mcp/server.py`)
- **FastMCP Integration**: Uses `fastmcp` library for MCP protocol handling
- **Process Management**: Automatically starts/stops/monitors canvas server via subprocess
- **Health Monitoring**: Polls canvas server `/health` endpoint with 5-second timeout
- **HTTP Client**: Uses `httpx.AsyncClient` for canvas server communication
- **Element Validation**: Pydantic models for request/response validation

### TypeScript Canvas Server (`src/server.ts`)
- **Express.js API**: REST endpoints for CRUD operations on elements
- **WebSocket Server**: Real-time broadcasting using `ws` library
- **In-Memory Storage**: `Map<string, ServerElement>` for element persistence
- **Element Versioning**: Automatic version increment and timestamp tracking
- **CORS Enabled**: Cross-origin requests supported for development

### React Frontend (`frontend/src/App.tsx`)
- **Excalidraw Integration**: Official `@excalidraw/excalidraw` package
- **WebSocket Client**: Auto-reconnecting WebSocket for real-time updates
- **Element Conversion**: Server elements converted to Excalidraw format
- **Dual Loading**: Initial HTTP fetch + ongoing WebSocket updates

### Type System (`src/types.ts`)
- **Element Interfaces**: Complete Excalidraw element type definitions
- **WebSocket Messages**: Typed message interfaces for real-time communication
- **Server Extensions**: Additional fields for versioning and metadata
- **Zod Validation**: Runtime type validation for API requests

## Development Workflow

### Standard Development Cycle
1. **Initial Setup**: `uv sync && npm install && npm run build`
2. **Development**: `npm run dev` (starts TypeScript watch + Vite dev server)
3. **MCP Testing**: Python server runs automatically via Claude Code's `.mcp.json` configuration
4. **Canvas Access**: Navigate to `http://localhost:3031` to see live diagram updates

### Process Lifecycle Management
- **Auto-start**: Python MCP server automatically launches canvas server on first tool use
- **Health Monitoring**: Python server continuously monitors canvas server via `/health` endpoint
- **Auto-recovery**: Failed canvas server is automatically restarted by Python server
- **Graceful Shutdown**: Canvas server is terminated when Python MCP server exits
- **Process Isolation**: Canvas server runs in separate process group for clean termination

### Element Synchronization Flow
1. **MCP Tool Call** → Python server validates and processes request
2. **HTTP API Call** → Python server sends element data to TypeScript server
3. **Element Storage** → TypeScript server stores element with version/timestamp metadata
4. **WebSocket Broadcast** → All connected clients receive real-time updates
5. **Canvas Update** → React frontend converts and renders elements in Excalidraw

## Important Implementation Details

- **No Persistence**: Elements exist only in canvas server memory (restart = data loss)
- **Element Versioning**: Each element update increments version number and updates timestamp
- **Type Conversion**: Text elements automatically converted to Excalidraw's label format
- **CORS Support**: Development-friendly CORS configuration for cross-origin requests
- **Error Handling**: Failed MCP operations include detailed error messages and suggestions
- **Concurrent Safety**: In-memory storage uses JavaScript Map for thread-safe operations

## Testing and Debugging

- Canvas server health check: `GET /health`
- API endpoints: `GET /api/elements`, `POST /api/elements`, etc.
- WebSocket connection: `ws://localhost:3031`
- Debug mode: Set `DEBUG=true` environment variable
- Canvas access: `http://localhost:3031` (after running canvas server)