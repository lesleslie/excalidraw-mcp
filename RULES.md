# Excalidraw MCP Development Rules

## Project Overview

This file establishes coding standards and development practices for the Excalidraw MCP project - a dual-language MCP server that enables AI agents to create and manipulate diagrams in real-time on a live canvas.

## Clean Code Philosophy (Foundation)

**EVERY LINE OF CODE IS A LIABILITY. The best code is no code.**

- **DRY (Don't Repeat Yourself)**: If you write it twice, you're doing it wrong
- **YAGNI (You Ain't Gonna Need It)**: Build only what's needed NOW
- **KISS (Keep It Simple, Stupid)**: Complexity is the enemy of maintainability
- **Less is More**: Prefer 10 lines that are clear over 100 that are clever
- **Code is Read 10x More Than Written**: Optimize for readability
- **Self-Documenting Code**: Code should explain itself; comments only for "why", not "what"

## Language-Specific Standards

### Python Standards (FastMCP Server)

- **Type Safety First**

  - Always include comprehensive type hints for all parameters and return types
  - Use modern typing syntax with pipe operator (`|`) for unions instead of `Optional[T]`
  - Import typing as `import typing as t` and prefix references with `t.`
  - Use built-in collection types: `list[str]`, `dict[str, int]`, `tuple[int, ...]`

- **Modern Python (3.13+)**

  - Use f-strings for all string formatting
  - Prefer `pathlib.Path` over `os.path` for file operations
  - Use `asyncio` for all async operations (not trio or other alternatives)

- **Code Organization**

  - Write modular functions with single responsibilities
  - Use protocols (`t.Protocol`) instead of abstract base classes
  - Prefer dataclasses for structured data with Pydantic for validation
  - Keep cognitive complexity under 15 per function

### TypeScript Standards (Canvas Server & Frontend)

- **Strict Type Safety**

  - Enable strict mode in tsconfig.json
  - Use explicit types for all function parameters and return values
  - Prefer interfaces over type aliases for object shapes
  - Use const assertions for immutable data

- **Modern TypeScript Features**

  - Use ES2022+ features (ES modules, optional chaining, nullish coalescing)
  - Prefer async/await over Promise chains
  - Use proper error handling with typed catch blocks

- **React Component Guidelines**

  - Use functional components with hooks exclusively
  - Implement proper TypeScript props interfaces
  - Use React.memo() for performance optimization when needed
  - Handle component cleanup in useEffect hooks

### WebSocket Communication Standards

- **Message Type Safety**

  - Define comprehensive TypeScript interfaces for all WebSocket messages
  - Use Zod for runtime validation of incoming messages
  - Implement proper error handling for connection failures
  - Use structured message formats with type discriminants

- **Real-time Synchronization**

  - Implement proper element versioning and conflict resolution
  - Use debouncing for high-frequency updates
  - Maintain connection state and implement auto-reconnection
  - Handle race conditions in element updates

## Quality Assurance Standards

### Testing Requirements

- **Python Tests (pytest)**

  - Maintain 85% minimum test coverage (enforced by pyproject.toml)
  - Use async test mode with `asyncio_mode="auto"`
  - Test all MCP tool implementations thoroughly
  - Mock external dependencies (HTTP clients, process management)

- **TypeScript Tests (Jest)**

  - Maintain 70% minimum test coverage across all components
  - Use jsdom environment for DOM testing
  - Test both canvas server APIs and React components
  - Mock WebSocket connections for unit tests

### Security Standards

- **Input Validation**

  - Validate all MCP tool parameters using Pydantic models
  - Sanitize all user inputs before processing
  - Use proper CORS configuration for development
  - Never use hardcoded temporary paths (use `tempfile` module)

- **Process Management**

  - Use secure subprocess execution without shell=True
  - Implement proper process isolation and cleanup
  - Handle process failures gracefully with auto-restart
  - Monitor resource usage to prevent DoS

## Tool Integration & Automation

### Development Tools

- **Python Ecosystem**

  - Use UV for dependency management and virtual environments
  - Run all tools through UV: `uv run pytest`, `uv run ruff`
  - Configure Ruff for linting and formatting
  - Use Bandit for security scanning

- **TypeScript Ecosystem**

  - Use npm for Node.js dependency management
  - Configure TypeScript compiler for strict checking
  - Use Vite for frontend development and building
  - Implement proper source maps for debugging

### Build and Development Workflow

- **Development Commands**

  ```bash
  # Setup
  uv sync && npm install && npm run build

  # Development mode
  npm run dev  # TypeScript watch + Vite dev server

  # Production build
  npm run build && npm run canvas

  # Testing
  pytest --cov=excalidraw_mcp  # Python tests with coverage
  npm run test:coverage        # TypeScript tests with coverage
  ```

- **Process Management**

  - Python MCP server automatically manages TypeScript canvas server
  - Implement health monitoring with auto-restart on failures
  - Use proper signal handling for graceful shutdowns
  - Log all process lifecycle events for debugging

## MCP-Specific Development Practices

### Tool Implementation Standards

- **FastMCP Integration**

  - Use Pydantic models for all tool request/response validation
  - Implement proper error handling with descriptive messages
  - Use async patterns for all HTTP communication
  - Follow MCP protocol specifications exactly

- **Element Management**

  - Implement comprehensive validation for Excalidraw element types
  - Use proper TypeScript interfaces for element definitions
  - Handle element versioning and conflict resolution
  - Support batch operations for performance

### Canvas Server Architecture

- **Express.js Server**

  - Implement RESTful API endpoints for all CRUD operations
  - Use proper HTTP status codes and error responses
  - Implement rate limiting and request validation
  - Support CORS for development environments

- **WebSocket Implementation**

  - Use structured message types for all communications
  - Implement proper connection lifecycle management
  - Support multiple concurrent clients
  - Handle message ordering and delivery guarantees

## Error Prevention Patterns

### Common Security Issues

```python
# NEVER: Hardcoded temporary paths
config_path = "/tmp/config.yaml"  # Security warning B108

# ALWAYS: Use tempfile module
import tempfile

with tempfile.NamedTemporaryFile(suffix=".yaml") as tmp:
    config_path = tmp.name
```

### Type Safety Patterns

```typescript
// PREFER: Explicit interfaces
interface ElementCreateRequest {
  type: 'rectangle' | 'ellipse' | 'diamond' | 'arrow' | 'text' | 'line';
  x: number;
  y: number;
  width?: number;
  height?: number;
}

// AVOID: Any types or loose interfaces
function createElementAny(data: any): any { ... }
```

### Async Patterns

```python
# PREFER: Proper async context management
async with httpx.AsyncClient() as client:
    response = await client.get("/health")

# AVOID: Unmanaged async resources
client = httpx.AsyncClient()
response = await client.get("/health")  # Client not closed
```

## Documentation Standards

### Code Documentation

- Use TypeScript/Python type annotations as primary documentation
- Add comments only for complex business logic explanations
- Maintain accurate README, SETUP, and CLAUDE.md files
- Document all environment variables and configuration options

### API Documentation

- Document all MCP tools with parameter descriptions
- Provide usage examples for complex operations
- Maintain up-to-date WebSocket message format documentation
- Include troubleshooting guides for common issues

## Testing Philosophy

### Test Categories

- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test MCP tool interactions with canvas server
- **Security Tests**: Test input validation and security measures
- **Performance Tests**: Test system performance under load
- **End-to-End Tests**: Test complete workflows with real canvas server

### Test Quality Standards

- Tests should be fast (< 1 second each for unit tests)
- Use proper mocking for external dependencies
- Test both success and failure scenarios
- Use descriptive test names that explain the scenario being tested
- Clean up all resources after test completion
