---
description: Create a new element on the Excalidraw canvas (rectangle, ellipse, diamond, arrow, line, text, freedraw).
argument-hint: <element-type> [--x N] [--y N] [--width N] [--height N] [--text "..."]
allowed-tools: mcp__excalidraw__create_element, mcp__excalidraw__health_check
---

# /excalidraw-create

Create a new element on the live Excalidraw canvas via the excalidraw-mcp server.

## Usage

`/excalidraw-create <element-type> [--x N] [--y N] [--width N] [--height N] [--text "..."]`

Arguments:

- `<element-type>`: one of `rectangle`, `ellipse`, `diamond`, `arrow`, `line`, `text`, `freedraw`.
- `--x N`: optional absolute canvas x coordinate. Defaults to `0`.
- `--y N`: optional absolute canvas y coordinate. Defaults to `0`.
- `--width N`: optional element width in pixels. Defaults applied by the MCP server when omitted.
- `--height N`: optional element height in pixels. Defaults applied by the MCP server when omitted.
- `--text "..."`: optional text payload (used by `text` elements and as a label for shapes/arrows).

The created element is synced to the canvas subprocess and broadcast to any WebSocket subscribers.

## Workflow

1. Call `mcp__excalidraw__health_check` to confirm the canvas subprocess is running.
2. Build the request payload from the supplied arguments.
3. Call `mcp__excalidraw__create_element` with the request payload.
4. Report the new element's id, coordinates, and canvas sync status.

## Example

`/excalidraw-create rectangle --x 200 --y 150 --width 120 --height 80 --text "Service"`
