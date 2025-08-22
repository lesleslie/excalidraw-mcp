# Excalidraw MCP Server Setup

This project provides both an MCP server for Claude Code integration and a visual canvas interface for Excalidraw diagrams.

## Architecture

- **MCP Server** (`dist/index.js`): Provides tools for Claude Code to create/edit diagrams
- **Express Canvas Server** (`dist/server.js`): Provides visual interface and REST API
- **WebSocket Sync**: Real-time synchronization between MCP operations and canvas

## Quick Start

### Option 1: Full Setup (Recommended)
```bash
# Start both MCP-compatible setup and canvas server
cd ~/Projects/mcp_excalidraw
npm run start-all
```

### Option 2: Canvas Only
```bash
# Just start the visual canvas server
cd ~/Projects/mcp_excalidraw
npm run production
```

### Option 3: Individual Services
```bash
# Canvas server only (port 3001)
npm run start-canvas

# MCP server only (stdio mode - for Claude Code)
npm run mcp

# Canvas server in background (returns immediately)
npm run canvas-bg
```

## Claude Code Integration

### Option A: Portable npx Configuration (Recommended)
```json
{
  "excalidraw": {
    "command": "npx",
    "args": ["-y", "mcp-excalidraw-server@1.0.5"],
    "env": {
      "EXPRESS_SERVER_URL": "http://localhost:3031"
    }
  }
}
```

### Option B: Local Development Configuration
```json
{
  "excalidraw": {
    "command": "npm",
    "args": ["run", "mcp"],
    "cwd": "~/Projects/mcp_excalidraw"
  }
}
```

**Setup Steps:**
1. **Canvas Server**: Run `npm run start-all` to start the companion canvas on port 3031
2. **Environment**: The MCP server automatically connects to `http://localhost:3031` for canvas sync

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

Environment variables (in `.env`):
```
PORT=3031
HOST=localhost
EXPRESS_SERVER_URL=http://localhost:3031
ENABLE_CANVAS_SYNC=true
```

## Troubleshooting

- **Port conflicts**: Change `PORT` in `.env`
- **MCP not connecting**: Verify `.mcp.json` has correct npm configuration with `cwd` parameter
- **Canvas sync issues**: Ensure Express server is running and `EXPRESS_SERVER_URL` is correct
- **Build issues**: Run `npm run build` to rebuild TypeScript sources
- **npm permission errors**: Ensure npm is properly installed and accessible from Claude Code
- **Path issues**: Use absolute paths in MCP configuration or ensure correct `cwd` parameter