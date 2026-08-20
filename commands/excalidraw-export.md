---
description: Export the current Excalidraw canvas scene, element set, library, or theme by retrieving the live resource snapshot.
argument-hint: <scene|library|theme|elements>
allowed-tools: mcp__excalidraw__get_resource, mcp__excalidraw__health_check
---

# /excalidraw-export

Retrieve a live snapshot of the Excalidraw canvas as a resource that can be exported downstream (to SVG, PNG, JSON, or copied into another tool).

## Usage

`/excalidraw-export <scene|library|theme|elements>`

Arguments:

- `<scene>`: full canvas scene JSON (elements, app state, files). This is the canonical export payload.
- `<library>`: shared Excalidraw library (reusable elements across scenes).
- `<theme>`: active theme (light/dark + custom palette).
- `<elements>`: just the elements array, without app state.

The MCP server returns the raw resource; downstream SVG/PNG rendering is the responsibility of the calling tool (e.g. browser-side Excalidraw or a local renderer).

## Workflow

1. Call `mcp__excalidraw__health_check` to confirm the canvas subprocess is running.
2. Call `mcp__excalidraw__get_resource` with the supplied `<resource-type>`.
3. Echo the resource payload back to the caller, noting the element count or scene size so downstream tools can decide how to render it.

## Example

`/excalidraw-export scene`
