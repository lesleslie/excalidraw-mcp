# Gemini Code Assistant Context

This document provides context for the Gemini Code Assistant to understand the `excalidraw-mcp` project.

## Project Overview

`excalidraw-mcp` is a dual-language system that enables AI agents to create and manipulate Excalidraw diagrams in real-time. It consists of two main components:

1. **Python MCP Server:** A Python-based server using the Model Context Protocol (MCP) that exposes tools for AI agents to interact with the Excalidraw canvas. It's built with `fastmcp` and manages the lifecycle of the canvas server.

1. **TypeScript Canvas Server:** A Node.js server built with Express.js and WebSockets that manages the Excalidraw canvas. It provides a REST API for element management and uses WebSockets to synchronize the canvas state with connected clients in real-time. The frontend is a React application that displays the Excalidraw canvas.

The Python MCP server receives commands from an AI agent, translates them into API calls to the TypeScript canvas server, which then updates the canvas and broadcasts the changes to all connected web clients.

### Key Technologies

- **Backend (MCP Server):** Python, `fastmcp`, `httpx`, `pydantic`
- **Backend (Canvas Server):** Node.js, TypeScript, Express.js, WebSockets (`ws`), `zod`
- **Frontend:** React, TypeScript, Vite
- **Package Management:** `uv` for Python, `npm` for Node.js
- **Testing:** `pytest` for Python, `jest` for TypeScript

## Building and Running

### Prerequisites

- Python 3.13+
- Node.js 16+
- `uv` (for Python package management)

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/lesleslie/excalidraw-mcp.git
   cd excalidraw-mcp
   ```

1. **Install Python dependencies:**

   ```bash
   uv sync
   ```

1. **Install Node.js dependencies:**

   ```bash
   npm install
   ```

### Running the System

The Python MCP server is the main entry point and will automatically start the TypeScript canvas server.

```bash
uv run python excalidraw_mcp/server.py
```

Once the server is running, you can access the Excalidraw canvas at `http://localhost:3031`.

### Development Mode

To run the frontend and backend in development mode with hot-reloading:

```bash
npm run dev
```

### Running Tests

- **Python tests:**

  ```bash
  pytest
  ```

- **TypeScript tests:**

  ```bash
  npm test
  ```

## Development Conventions

- **Code Style:** The project uses `ruff` for Python linting and formatting, and `prettier` (via `vite`) for TypeScript.
- **Type-checking:** `pyright` is used for static type analysis in Python, and `tsc` for TypeScript.
- **Testing:** The project has separate unit and integration tests for both Python and TypeScript codebases. Test coverage is enforced.
- **Commits:** While not explicitly defined in the provided files, a conventional commit style is recommended given the structured nature of the project.
