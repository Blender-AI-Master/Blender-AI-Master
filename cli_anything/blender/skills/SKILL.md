---
name: >-
  cli-anything-blender
description: >-
  Command-line interface for Blender - A stateful command-line interface for 3D modeling and rendering, built on Blender's Python API (bpy)...
---

# cli-anything-blender

A stateful command-line interface for 3D modeling and rendering, built on Blender's
Python API (bpy). Designed for AI agents and power users who need to create and
manipulate 3D scenes without the GUI.

## Installation

This CLI is installed as part of the cli-anything-blender package:

```bash
pip install cli-anything-blender
```

**Prerequisites:**
- Python 3.10+
- **Blender** is required for rendering. Install via your system package manager
  or download from https://blender.org

## Usage

### Basic Commands

```bash
# Show help
cli-anything-blender --help

# Start interactive REPL mode
cli-anything-blender

# Create a new scene
cli-anything-blender scene new -o project.json

# Run with JSON output (for agent consumption)
cli-anything-blender --json object list
```

### REPL Mode

When invoked without a subcommand, the CLI enters an interactive REPL session:

```bash
cli-anything-blender
# Enter commands interactively with tab-completion and history
```


## Command Groups


### Scene

Scene management commands.

| Command | Description |
|---------|-------------|
| `new` | Create a new scene |
| `open` | Open an existing scene |
| `save` | Save the current scene |
| `info` | Show scene information |
| `profiles` | List available scene profiles |
| `json` | Print raw scene JSON |


### Object

3D object management commands.

| Command | Description |
|---------|-------------|
| `add` | Add a 3D primitive object |
| `remove` | Remove an object by index |
| `duplicate` | Duplicate an object |
| `transform` | Transform an object (translate, rotate, scale) |
| `set` | Set an object property (name, visible, location, rotation, scale, parent) |
| `list` | List all objects |
| `get` | Get detailed info about an object |


### Material

Material management commands.

| Command | Description |
|---------|-------------|
| `create` | Create a new material |
| `assign` | Assign a material to an object |
| `set` | Set a material property (color, metallic, roughness, specular, alpha, etc.) |
| `list` | List all materials |
| `get` | Get detailed info about a material |


### Modifier

Modifier management commands.

| Command | Description |
|---------|-------------|
| `list-available` | List all available modifiers |
| `info` | Show details about a modifier |
| `add` | Add a modifier to an object |
| `remove` | Remove a modifier by index |
| `set` | Set a modifier parameter |
| `list` | List modifiers on an object |


### Camera

Camera management commands.

| Command | Description |
|---------|-------------|
| `add` | Add a camera to the scene |
| `set` | Set a camera property |
| `set-active` | Set the active camera |
| `list` | List all cameras |


### Light

Light management commands.

| Command | Description |
|---------|-------------|
| `add` | Add a light to the scene |
| `set` | Set a light property |
| `list` | List all lights |


### Animation

Animation and keyframe commands.

| Command | Description |
|---------|-------------|
| `keyframe` | Set a keyframe on an object |
| `remove-keyframe` | Remove a keyframe from an object |
| `frame-range` | Set the animation frame range |
| `fps` | Set the animation FPS |
| `list-keyframes` | List keyframes for an object |


### Render

Render settings and output commands.

| Command | Description |
|---------|-------------|
| `settings` | Configure render settings |
| `info` | Show current render settings |
| `presets` | List available render presets |
| `execute` | Render the scene (generates bpy script) |
| `script` | Generate bpy script without rendering |


### Preview

Preview bundle capture and inspection.

| Command | Description |
|---------|-------------|
| `recipes` | List available preview recipes |
| `capture` | Capture a preview bundle for the active scene |
| `latest` | Show the latest preview bundle manifest |
| `live start` | Start a live preview session |
| `live push` | Publish a fresh bundle into the live preview session |
| `live status` | Show live preview session metadata |
| `live stop` | Stop the live preview session |


### Session

Session management commands.

| Command | Description |
|---------|-------------|
| `status` | Show session status |
| `undo` | Undo the last operation |
| `redo` | Redo the last undone operation |
| `history` | Show undo history |



## Examples


### Create a New Scene

Create a new blender project file.

```bash
cli-anything-blender scene new --name "MyScene"
# Or with JSON output for programmatic use
cli-anything-blender --json scene new --name "MyScene"
```


### Interactive REPL Session

Start an interactive session with undo/redo support.

```bash
cli-anything-blender
# Enter commands interactively
# Use 'help' to see available commands
# Use 'undo' and 'redo' for history navigation
```


### Build a Simple 3D Scene

```bash
# Create scene
cli-anything-blender scene new --name "ChairScene"

# Add a chair (simplified medieval chair)
cli-anything-blender object add cube --name "Seat" --location 0,0,0.5 --scale 1,1,0.1
cli-anything-blender object add cube --name "Backrest" --location 0,-0.5,1.2 --scale 1,0.1,1.5
cli-anything-blender object add cylinder --name "FL" --location -0.4,0.4,0.25 --param "radius=0.05"
cli-anything-blender object add cylinder --name "FR" --location 0.4,0.4,0.25 --param "radius=0.05"
cli-anything-blender object add cylinder --name "BL" --location -0.4,-0.4,0.25 --param "radius=0.05"
cli-anything-blender object add cylinder --name "BR" --location 0.4,-0.4,0.25 --param "radius=0.05"

# Create and assign material
cli-anything-blender material create --name "Oak" --color 0.55,0.35,0.2,1 --roughness 0.6
cli-anything-blender material assign 0 0

# Add bevel modifier for realism
cli-anything-blender modifier add bevel --object 0 --param "width=0.02"

# Set up camera
cli-anything-blender camera add --name "MainCam" --location 3,3,2 --active

# Add lighting
cli-anything-blender light add sun --name "KeyLight" --power 2.0

# Save scene
cli-anything-blender scene save --path chair_scene.json

# Render
cli-anything-blender render execute output.png --overwrite
```


## State Management

The CLI maintains session state with:

- **Undo/Redo**: Up to 50 levels of history
- **Project persistence**: Save/load project state as JSON
- **Session tracking**: Track modifications and changes

## Output Formats

All commands support dual output modes:

- **Human-readable** (default): Tables, formatted text
- **Machine-readable** (`--json` flag): Structured JSON for agent consumption

```bash
# Human output
cli-anything-blender scene info

# JSON output for agents
cli-anything-blender --json scene info
```

## For AI Agents

When using this CLI programmatically:

1. **Always use `--json` flag** for parseable output
2. **Check return codes** - 0 for success, non-zero for errors
3. **Parse stderr** for error messages on failure
4. **Use absolute paths** for all file operations
5. **Verify outputs exist** after render operations
6. **Review rendered outputs** after scene changes instead of trusting saved project state alone

## More Information

- Full documentation: See README.md in the package
- Test coverage: See TEST.md in the package
- Methodology: See HARNESS.md in the cli-anything-plugin

## Version

1.0.0
