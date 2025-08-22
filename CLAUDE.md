# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server for Excalidraw that enables AI agents to create and manipulate diagrams in real-time on a live canvas. The system uses:

1. **Python FastMCP implementation** - `excalidraw_mcp/server.py` (MCP server)
2. **TypeScript Canvas Server** - `src/server.ts` (Express server + WebSocket)

The Python implementation handles MCP protocol communication while the TypeScript server manages the canvas and real-time synchronization.

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

**Key Components:**
- **MCP Server**: Python FastMCP server handling MCP protocol and element creation/management
- **Canvas Server**: TypeScript Express.js server providing REST API + WebSocket for real-time sync
- **Frontend**: React-based Excalidraw canvas with WebSocket client
- **Types System**: Comprehensive TypeScript definitions in `src/types.ts`

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

### Development Commands
```bash
# Build project (frontend + canvas server)
npm run build

# Start canvas server only
npm run canvas

# Development mode (TypeScript watch + Vite dev server)
npm run dev

# Production mode (build + start canvas)
npm run production

# Type checking without compilation
npm run type-check
```

### Development Scripts
- **`./start-both.sh`**: Starts canvas server with MCP information (port 3031)
- **`./start-canvas-only.sh`**: Starts only canvas server for npx setup

## Environment Configuration

Key environment variables:
- `EXPRESS_SERVER_URL`: Canvas server URL (default: `http://localhost:3031`)
- `ENABLE_CANVAS_SYNC`: Enable/disable canvas synchronization (default: `true`)
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

## Key Files and Structure

### Python MCP Server
- **`excalidraw_mcp/server.py`**: FastMCP server with all MCP tools
- **`pyproject.toml`**: Python project configuration with dependencies

### TypeScript Canvas Server
- **`src/server.ts`**: Express canvas server with REST API + WebSocket
- **`src/types.ts`**: Comprehensive type definitions for Excalidraw elements
- **`src/utils/logger.ts`**: Logging utility
- **`frontend/src/App.tsx`**: React frontend with Excalidraw integration

### Configuration
- **`package.json`**: Node.js dependencies and scripts
- **`tsconfig.json`**: TypeScript compiler configuration with strict settings
- **`vite.config.js`**: Frontend build configuration

## Development Workflow

1. **Setup**: Run `uv sync` for Python dependencies and `npm install && npm run build` for canvas server
2. **Canvas server**: Always run `npm run canvas` for the Express.js server
3. **MCP server**: Runs automatically via `uvx excalidraw-mcp` when Claude Code connects
4. **Real-time sync**: Elements created via MCP appear instantly on canvas via WebSocket
5. **Storage**: Elements stored in canvas server memory, MCP server communicates via HTTP API

## Important Notes

- The canvas server (Express.js) must always run for full functionality
- MCP server (Python) and canvas server (TypeScript) communicate via HTTP API
- WebSocket provides real-time updates to connected frontend clients
- Text elements are converted to Excalidraw's label format automatically
- The system uses in-memory storage (no persistent database)
- Local `.mcp.json` configures Claude Code to use `uvx excalidraw-mcp`

## Testing and Debugging

- Canvas server health check: `GET /health`
- API endpoints: `GET /api/elements`, `POST /api/elements`, etc.
- WebSocket connection: `ws://localhost:3031`
- Debug mode: Set `DEBUG=true` environment variable
- Canvas access: `http://localhost:3031` (after running canvas server)