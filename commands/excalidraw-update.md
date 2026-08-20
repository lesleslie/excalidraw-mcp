---
description: Update an existing Excalidraw element (move, resize, restyle, relabel) and sync the change to the live canvas.
argument-hint: <element-id> [--x N] [--y N] [--width N] [--height N] [--text "..."] [--stroke-color "#RRGGBB"]
allowed-tools: mcp__excalidraw__update_element, mcp__excalidraw__query_elements, mcp__excalidraw__health_check
---

# /excalidraw-update

Live-update an element that already exists on the Excalidraw canvas.

## Usage

`/excalidraw-update <element-id> [--x N] [--y N] [--width N] [--height N] [--text "..."] [--stroke-color "#RRGGBB"]`

Arguments:

- `<element-id>`: id of the target element (returned by `mcp__excalidraw__query_elements` or `mcp__excalidraw__create_element`).
- `--x N`: optional new absolute canvas x coordinate.
- `--y N`: optional new absolute canvas y coordinate.
- `--width N`: optional new element width in pixels.
- `--height N`: optional new element height in pixels.
- `--text "..."`: optional new text payload.
- `--stroke-color "#RRGGBB"`: optional new stroke color in hex form.

Only the supplied fields are mutated; unspecified fields keep their current values.

## Workflow

1. Call `mcp__excalidraw__health_check` to confirm the canvas subprocess is running.
2. If the caller does not know `<element-id>`, call `mcp__excalidraw__query_elements` to discover the candidate ids.
3. Build the request payload from the supplied arguments (only the fields the caller asked to change).
4. Call `mcp__excalidraw__update_element` with the element id and the request payload.
5. Report which fields changed and the canvas sync status.

## Example

`/excalidraw-update elem_abc123 --x 240 --y 160 --stroke-color "#1f6feb"`
