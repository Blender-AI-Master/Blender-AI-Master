# CLI-Anything Commands

## Overview

CLI-Anything provides a stateful command-line interface for 3D scene editing via Blender. Commands are organized into groups.

## Command Groups

- [Scene Commands](./commands/scene.md) - Scene management
- [Object Commands](./commands/object.md) - 3D object operations
- [Material Commands](./commands/material.md) - Material management
- [Modifier Commands](./commands/modifier.md) - Geometry modifiers
- [Camera Commands](./commands/camera.md) - Camera management
- [Light Commands](./commands/light.md) - Lighting control
- [Animation Commands](./commands/animation.md) - Keyframe animation
- [Render Commands](./commands/render.md) - Render settings and output
- [Preview Commands](./commands/preview.md) - Preview bundle capture
- [Session Commands](./commands/session.md) - Undo/redo session management

## Usage

```bash
# One-shot commands
cli-anything-blender scene new --name "MyScene"
cli-anything-blender object add cube --name "Cube" --location 0,0,0
cli-anything-blender material create --name "Red" --color 1,0,0,1

# With JSON output
cli-anything-blender --json object list

# Interactive REPL
cli-anything-blender repl
```

## Common Patterns

### Vector Arguments
Many commands accept vectors as comma-separated floats:
```bash
--location 1.5,2.0,-0.5
--rotation 45,90,0
--scale 2,2,2
--color 1,0.5,0.2,1
```

### Index-Based References
Objects, materials, and modifiers are referenced by index (0-based):
```bash
cli-anything-blender object get 0
cli-anything-blender material assign 0 0  # assign mat 0 to obj 0
```

### Parameters
Some commands accept key=value parameters:
```bash
cli-anything-blender object add sphere --param "radius=2.0" --param "segments=64"
cli-anything-blender modifier add subdivision --object 0 --param "levels=3"
```
