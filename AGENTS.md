# AI Agents Guide for Excalidraw MCP

This document describes how AI agents (like Claude, GPT, etc.) can interact with the Excalidraw MCP server to create visual diagrams and manipulations in real-time.

## Overview

The Excalidraw MCP server acts as a bridge between AI agents and the Excalidraw canvas, allowing agents to:

- Create visual diagrams through MCP tool calls
- Manipulate existing elements on the canvas
- Build complex visual representations of concepts, processes, and data
- Provide real-time visual feedback during conversations

## Agent Capabilities

### 1. Visual Diagram Creation

AI agents can create various types of visual elements:

**Basic Shapes:**

- Rectangles for processes, containers, or entities
- Ellipses for start/end points or organic concepts
- Diamonds for decision points
- Text elements for labels and descriptions

**Connectors:**

- Arrows for process flow and relationships
- Lines for connections and boundaries

**Advanced Elements:**

- Grouped elements for complex structures
- Aligned and distributed layouts
- Locked elements for template preservation

### 2. Real-time Collaboration

**Live Canvas Integration:**

- Elements appear instantly on the web canvas at `http://localhost:3031`
- Multiple users can view diagrams as agents create them
- WebSocket-based real-time synchronization

**Interactive Feedback:**

- Agents can query existing elements
- Modify diagrams based on user feedback
- Clear canvas for fresh starts

### 3. Common Use Cases for AI Agents

**Process Diagrams:**

```
Start → Process → Decision → End
```

**System Architecture:**

```
Frontend ↔ API ↔ Database
```

**Flowcharts:**

```
Input → Validation → Processing → Output
```

**Mind Maps:**

```
Central Concept with branching ideas
```

**Data Visualization:**

```
Charts, graphs, and data relationships
```

## MCP Tools Reference

### Element Creation Tools

#### `create_element`

Create individual diagram elements with full control over positioning, styling, and content.

**Supported Element Types:**

- `rectangle` - Rectangular shapes for processes, entities
- `ellipse` - Oval shapes for start/end points
- `diamond` - Diamond shapes for decisions
- `arrow` - Directional arrows for flow
- `line` - Simple lines for connections
- `text` - Text labels and descriptions

**Key Parameters:**

- Position: `x`, `y` coordinates
- Size: `width`, `height`
- Styling: `backgroundColor`, `strokeColor`, `strokeWidth`
- Content: `text` for text elements

#### `batch_create_elements`

Create multiple elements in a single operation for complex diagrams.

**Benefits:**

- Atomic operation - all elements created together
- Better performance for complex diagrams
- Maintains relationships between elements

### Element Management Tools

#### `update_element`

Modify existing elements on the canvas.

**Use Cases:**

- Update text content
- Change styling or colors
- Resize or reposition elements
- Modify element properties

#### `delete_element`

Remove elements from the canvas.

#### `query_elements`

Search and filter existing elements on the canvas.

**Filter Options:**

- By element type
- By text content
- By position ranges
- By styling attributes

### Organization Tools

#### `group_elements` / `ungroup_elements`

Organize related elements into logical groups.

**Benefits:**

- Move multiple elements together
- Apply operations to entire groups
- Maintain visual hierarchy

#### `align_elements`

Align multiple elements for professional layouts.

**Alignment Options:**

- Horizontal: `left`, `center`, `right`
- Vertical: `top`, `middle`, `bottom`

#### `distribute_elements`

Evenly space elements for clean layouts.

**Distribution Options:**

- Horizontal distribution
- Vertical distribution

#### `lock_elements` / `unlock_elements`

Protect elements from accidental modification.

### Resource Access

#### `get_resource`

Access canvas data and metadata.

**Resource Types:**

- `scene` - Complete canvas state
- `elements` - All elements data
- `library` - Element library
- `theme` - Current theme settings

## Agent Design Patterns

### 1. Progressive Diagram Building

Build diagrams step-by-step, allowing users to provide feedback:

```python
# 1. Create main structure
create_element(type="rectangle", text="Main Process")

# 2. Add connections based on user input
create_element(type="arrow", start_binding="main_process")

# 3. Refine based on feedback
update_element(id="arrow_1", color="#ff0000")
```

### 2. Template-Based Creation

Use consistent patterns for similar diagram types:

```python
# Flowchart template
def create_flowchart_step(text, x, y):
    return {
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": 120,
        "height": 60,
        "backgroundColor": "#e3f2fd",
        "strokeColor": "#1976d2",
        "text": text,
    }
```

### 3. Interactive Refinement

Allow users to guide diagram evolution:

```python
# Query existing elements
elements = query_elements(type="rectangle")

# Modify based on user feedback
for element in elements:
    if "process" in element.text.lower():
        update_element(element.id, backgroundColor="#fff3e0")
```

## Best Practices for AI Agents

### 1. Visual Hierarchy

- Use consistent colors for element types
- Maintain proper spacing and alignment
- Group related elements visually

### 2. Clear Labeling

- Use descriptive text for all elements
- Keep labels concise but informative
- Consider text size and readability

### 3. Logical Flow

- Follow conventional flow directions (left-to-right, top-to-bottom)
- Use appropriate connectors (arrows for process flow)
- Maintain consistent spacing

### 4. User Interaction

- Explain what diagram is being created
- Ask for feedback on layout and content
- Offer to modify or extend diagrams

### 5. Error Handling

- Check canvas server availability
- Handle element creation failures gracefully
- Provide fallback options if visual creation fails

## Example Agent Implementations

### Process Flow Agent

Specializes in creating business process diagrams:

```python
def create_process_flow(steps):
    x_start = 100
    y_pos = 200

    elements = []
    for i, step in enumerate(steps):
        # Create process box
        elements.append(
            {
                "type": "rectangle",
                "x": x_start + (i * 200),
                "y": y_pos,
                "text": step,
                "backgroundColor": "#e3f2fd",
            }
        )

        # Add arrow (except for last step)
        if i < len(steps) - 1:
            elements.append(
                {
                    "type": "arrow",
                    "x": x_start + (i * 200) + 120,
                    "y": y_pos + 30,
                    "width": 80,
                    "height": 0,
                }
            )

    batch_create_elements(elements)
```

### System Architecture Agent

Creates technical architecture diagrams:

```python
def create_architecture_diagram(components):
    layers = {
        "frontend": {"y": 100, "color": "#e8f5e8"},
        "api": {"y": 250, "color": "#fff3e0"},
        "database": {"y": 400, "color": "#fce4ec"},
    }

    elements = []
    for component in components:
        layer_config = layers[component["layer"]]
        elements.append(
            {
                "type": "rectangle",
                "x": component["x"],
                "y": layer_config["y"],
                "text": component["name"],
                "backgroundColor": layer_config["color"],
            }
        )

    batch_create_elements(elements)
```

## Integration Examples

### Claude Code Integration

When using with Claude Code, agents can:

1. **Explain Code Visually**: Create diagrams showing code structure
1. **Design System Architecture**: Visualize proposed system designs
1. **Process Documentation**: Convert text processes into visual flows
1. **Debug Assistance**: Create visual representations of data flow

### Multi-Agent Workflows

Multiple specialized agents can collaborate:

1. **Planning Agent**: Creates high-level structure
1. **Detail Agent**: Adds specific elements and styling
1. **Review Agent**: Checks layout and suggests improvements
1. **User Interface Agent**: Handles user feedback and modifications

## Troubleshooting

### Common Issues

**Elements Not Appearing:**

- Check canvas server is running (`http://localhost:3031`)
- Verify MCP server connection
- Check console for WebSocket errors

**Layout Problems:**

- Use `align_elements` for consistent positioning
- Check element dimensions and spacing
- Consider using `distribute_elements` for even spacing

**Performance Issues:**

- Use `batch_create_elements` for multiple elements
- Avoid excessive individual element operations
- Clear canvas periodically with complex diagrams

### Debugging Tips

- Use `query_elements` to inspect current canvas state
- Check element IDs for update/delete operations
- Monitor WebSocket connection status in browser console

## Future Enhancements

The Excalidraw MCP server continues to evolve with new capabilities:

- Enhanced element types and styling options
- Advanced layout algorithms
- Collaborative editing features
- Export capabilities for diagrams
- Integration with other visualization tools

______________________________________________________________________

For technical implementation details, see the main [README.md](README.md) and [CLAUDE.md](CLAUDE.md) files.
