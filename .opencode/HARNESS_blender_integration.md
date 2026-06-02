# CLI-Anything Harness for OpenCode

## Overview

This harness defines how OpenCode AI should interact with CLI-Anything to generate detailed 3D models in Blender. The workflow uses a stateful session where OpenCode generates CLI commands that modify a scene, and results are synced back to Blender's viewport.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenCode AI                               │
│         (generates CLI commands creatively)                 │
└─────────────────────────────────────────────────────────────┘
                               │
                               │ CLI Commands
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    CLI-Anything Core                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Session Manager (stateful, undo/redo)              │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Command Handlers                                    │   │
│  │  • scene    • object   • material                   │   │
│  │  • modifier • camera   • light                      │   │
│  │  • animation • render  • preview                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                               │
                               │ bpy Scripts
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Blender Viewport                         │
│              (3D view with real-time preview)               │
└─────────────────────────────────────────────────────────────┘
```

## Command Execution Flow

1. OpenCode receives a creative prompt (e.g., "create a detailed medieval chair")
2. OpenCode generates a sequence of CLI-Anything commands
3. Commands are executed via subprocess: `cli-anything-blender <command>`
4. Session state is maintained between commands
5. Final scene can be rendered or exported

## Calling CLI-Anything

### Subprocess Pattern
```python
import subprocess

result = subprocess.run(
    ["cli-anything-blender", "object", "add", "cube", "--name", "Box"],
    capture_output=True,
    text=True
)
print(result.stdout)
```

### From OpenCode Agent
When OpenCode generates commands, use the `--json` flag for machine-readable output:
```bash
cli-anything-blender --json object list
```

## Session Workflow

### 1. Initialize Scene
```bash
cli-anything-blender scene new --name "MyProject"
```

### 2. Build Scene with Multiple Objects
```bash
# Create a table with legs
cli-anything-blender object add cube --name "Tabletop" --location 0,0,1 --scale 2,1,0.1
cli-anything-blender object add cube --name "Leg1" --location -0.9,-0.4,0.5 --scale 0.1,0.1,1
cli-anything-blender object add cube --name "Leg2" --location 0.9,-0.4,0.5 --scale 0.1,0.1,1
cli-anything-blender object add cube --name "Leg3" --location -0.9,0.4,0.5 --scale 0.1,0.1,1
cli-anything-blender object add cube --name "Leg4" --location 0.9,0.4,0.5 --scale 0.1,0.1,1
```

### 3. Add Materials
```bash
cli-anything-blender material create --name "Wood" --color 0.6,0.4,0.2,1 --roughness 0.7
cli-anything-blender material create --name "Metal" --color 0.8,0.8,0.9,1 --metallic 0.9 --roughness 0.2
```

### 4. Apply Modifiers for Detail
```bash
cli-anything-blender modifier add subdivision --object 0 --param "levels=2"
cli-anything-blender modifier add bevel --object 0 --param "width=0.02"
```

### 5. Add Lighting
```bash
cli-anything-blender light add sun --name "KeyLight" --power 2.0
cli-anything-blender light add area --name "FillLight" --location -3,0,2 --power 50
```

### 6. Set Up Camera
```bash
cli-anything-blender camera add --name "MainCam" --location 5,5,3 --active
```

### 7. Save and Render
```bash
cli-anything-blender scene save --path "myproject.blend-cli.json"
cli-anything-blender render execute --output "render.png"
```

## Creative Prompt Patterns

OpenCode should use multi-step reasoning to build complex scenes:

### Pattern: Hierarchical Construction
```
1. Start with base/ground structure
2. Add main body components
3. Add secondary details (legs, handles, etc.)
4. Apply modifiers for organic shapes
5. Add materials based on physical properties
6. Set up lighting for mood
7. Configure camera for best view
```

### Example: Medieval Chair
```bash
# Step 1: Seat
cli-anything-blender object add cube --name "Seat" --location 0,0,0.5 --scale 1,1,0.1

# Step 2: Backrest
cli-anything-blender object add cube --name "Backrest" --location 0,-0.5,1.2 --scale 1,0.1,1.5

# Step 3: Legs
cli-anything-blender object add cylinder --name "FL" --location -0.4,0.4,0.25 --param "radius=0.05"
cli-anything-blender object add cylinder --name "FR" --location 0.4,0.4,0.25 --param "radius=0.05"
cli-anything-blender object add cylinder --name "BL" --location -0.4,-0.4,0.25 --param "radius=0.05"
cli-anything-blender object add cylinder --name "BR" --location 0.4,-0.4,0.25 --param "radius=0.05"

# Step 4: Armrests
cli-anything-blender object add cylinder --name "ArmL" --location -0.55,0,0.7 --rotation 0,0,90 --param "radius=0.04"
cli-anything-blender object add cylinder --name "ArmR" --location 0.55,0,0.7 --rotation 0,0,90 --param "radius=0.04"

# Step 5: Wood material
cli-anything-blender material create --name "Oak" --color 0.55,0.35,0.2,1 --roughness 0.6

# Step 6: Apply bevel for realism
cli-anything-blender modifier add bevel --object 0 --param "width=0.02" --param "segments=2"
```

## Error Handling

Check command output for errors:
```bash
cli-anything-blender --json object add cube --name "Test"
# Returns: {"error": "...", "type": "ValueError"} on failure
```

Use session undo if a command produces unexpected results:
```bash
cli-anything-blender session undo
```

## Best Practices for OpenCode

1. **Plan before executing**: Generate the full command sequence mentally before running
2. **Use descriptive names**: Makes debugging easier
3. **Build incrementally**: Test each component before adding details
4. **Use materials early**: Helps visualize the final result
5. **Leverage modifiers**: Create complex shapes from primitives
6. **Consider scale**: Use realistic proportions
7. **Add lighting last**: Once geometry and materials are finalized

## Command Reference

See [./commands/README.md](./commands/README.md) for complete command reference.

## Blender Python Equivalents

When OpenCode needs to understand what a command does in Blender:

| CLI-Anything | Blender Python |
|--------------|----------------|
| `object add cube` | `bpy.ops.mesh.primitive_cube_add()` |
| `material create` | `bpy.data.materials.new()` |
| `modifier add` | `obj.modifiers.new()` |
| `light add sun` | `bpy.ops.light.sun_add()` |

## Integration Points

- **Blender Plugin**: `AIAI_OT_send_chat` operator sends prompts to OpenCode
- **OpenCode Provider**: `api/opencode_provider.py` handles subprocess communication
- **CLI Manager**: `core/cli_manager.py` executes commands and parses results
