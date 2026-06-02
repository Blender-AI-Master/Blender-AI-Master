# Blender CLI

A stateful command-line interface for 3D modeling and rendering, built on Blender's
Python API (bpy). Designed for AI agents and power users who need to create and
manipulate 3D scenes without the GUI.

## Prerequisites

- Python 3.10+
- `click` (CLI framework)
- `prompt-toolkit` (REPL support)
- **Blender** (system package for rendering)

### Install Blender

```bash
# Debian/Ubuntu
apt install blender

# macOS
brew install --cask blender

# Windows
# Download from https://blender.org
```

## How to Run

All commands are run from the `cli_anything/blender/` directory or via the installed CLI.

### One-shot commands

```bash
# Show help
python3 -m cli_anything.blender.blender_cli --help

# Create a new scene
python3 -m cli_anything.blender.blender_cli scene new --name "MyScene"

# Add objects
python3 -m cli_anything.blender.blender_cli object add cube --name "Cube" --location 0,0,0

# Create materials
python3 -m cli_anything.blender.blender_cli material create --name "RedMetal" --color 1,0,0,1 --metallic 0.8

# JSON output (for agent consumption)
python3 -m cli_anything.blender.blender_cli --json object list
```

### Interactive REPL

```bash
python3 -m cli_anything.blender.blender_cli repl
python3 -m cli_anything.blender.blender_cli repl --project myproject.json
```

Inside the REPL, type `help` for all available commands.

## Command Reference

### Scene

```bash
scene new [--name NAME] [--profile PROFILE] [--resolution-x RX] [--resolution-y RY]
scene open <path>
scene save [path]
scene info
scene profiles
scene json
```

### Object

```bash
object add <cube|sphere|cylinder|cone|plane|torus|monkey|empty> [--name N] [--location X,Y,Z]
object remove <index>
object duplicate <index>
object transform <index> [--translate DX,DY,DZ] [--rotate RX,RY,RZ] [--scale SX,SY,SZ]
object set <index> <property> <value>
object list
object get <index>
```

### Material

```bash
material create [--name NAME] [--color R,G,B,A] [--metallic M] [--roughness R] [--specular S]
material assign <material_index> <object_index>
material set <index> <property> <value>
material list
material get <index>
```

### Modifier

```bash
modifier list-available [--category generate|deform]
modifier info <name>
modifier add <type> [--object INDEX] [--name NAME] [--param KEY=VALUE]
modifier remove <modifier_index> [--object INDEX]
modifier set <modifier_index> <param> <value> [--object INDEX]
modifier list [--object INDEX]
```

### Camera

```bash
camera add [--name NAME] [--location X,Y,Z] [--rotation RX,RY,RZ] [--type PERSP|ORTHO|PANO]
camera set <index> <property> <value>
camera set-active <index>
camera list
```

### Light

```bash
light add <point|sun|spot|area> [--name NAME] [--location X,Y,Z] [--color R,G,B]
light set <index> <property> <value>
light list
```

### Animation

```bash
animation keyframe <object_index> <frame> <property> <value> [--interpolation LINEAR|BEZIER]
animation remove-keyframe <object_index> <frame> [--prop PROPERTY]
animation frame-range <start> <end>
animation fps <fps>
animation list-keyframes <object_index>
```

### Render

```bash
render settings [--engine CYCLES|EEVEE|WORKBENCH] [--samples N] [--denoising]
render info
render presets
render execute <output_path> [--frame N] [--animation]
render script <output_path> [--frame N]
```

### Preview

```bash
preview recipes
preview capture [--recipe NAME]
preview latest
preview live start [--recipe NAME] [--poll-ms N]
preview live push
preview live status
preview live stop
```

### Session

```bash
session status
session undo
session redo
session history
```

## JSON Mode

Add `--json` before the subcommand for machine-readable output:

```bash
python3 -m cli_anything.blender.blender_cli --json object list
```

## Running Tests

```bash
cd cli_anything/blender
python3 -m pytest tests/test_core.py -v        # Unit tests (no Blender needed)
python3 -m pytest tests/test_full_e2e.py -v     # E2E tests (requires Blender)
python3 -m pytest tests/ -v                      # All tests
```

## Example Workflow

```bash
# Create a scene
python3 -m cli_anything.blender.blender_cli scene new --name "ChairScene"

# Add a chair (simplified)
python3 -m cli_anything.blender.blender_cli object add cube --name "Seat" --location 0,0,0.5 --scale 1,1,0.1
python3 -m cli_anything.blender.blender_cli object add cube --name "Backrest" --location 0,-0.5,1.2 --scale 1,0.1,1.5
python3 -m cli_anything.blender.blender_cli object add cylinder --name "Leg1" --location -0.4,0.4,0.25 --param "radius=0.05"
python3 -m cli_anything.blender.blender_cli object add cylinder --name "Leg2" --location 0.4,0.4,0.25 --param "radius=0.05"
python3 -m cli_anything.blender.blender_cli object add cylinder --name "Leg3" --location -0.4,-0.4,0.25 --param "radius=0.05"
python3 -m cli_anything.blender.blender_cli object add cylinder --name "Leg4" --location 0.4,-0.4,0.25 --param "radius=0.05"

# Create and assign material
python3 -m cli_anything.blender.blender_cli material create --name "Oak" --color 0.55,0.35,0.2,1 --roughness 0.6
python3 -m cli_anything.blender.blender_cli material assign 0 0

# Add bevel modifier for realism
python3 -m cli_anything.blender.blender_cli modifier add bevel --object 0 --param "width=0.02"

# Set up camera
python3 -m cli_anything.blender.blender_cli camera add --name "MainCam" --location 3,3,2 --active

# Add lighting
python3 -m cli_anything.blender.blender_cli light add sun --name "KeyLight" --power 2.0

# Save scene
python3 -m cli_anything.blender.blender_cli scene save --path chair_scene.json

# Render
python3 -m cli_anything.blender.blender_cli render execute output.png --overwrite
```

## Blender Python API

The CLI generates bpy scripts that are executed by Blender headless. Key mappings:

| CLI Command | bpy API |
|------------|---------|
| `object add cube` | `bpy.ops.mesh.primitive_cube_add()` |
| `object add sphere` | `bpy.ops.mesh.primitive_uv_sphere_add()` |
| `material create` | `bpy.data.materials.new()` |
| `modifier add` | `obj.modifiers.new()` |
| `light add sun` | `bpy.ops.light.sun_add()` |
| `render execute` | `bpy.ops.render.render()` |
