# Scene Commands

## scene new
Create a new scene.
```bash
cli-anything-blender scene new --name "MyScene" [options]
```
**Options:**
- `--name`, `-n`: Scene name (default: "untitled")
- `--profile`, `-p`: Scene profile
- `--resolution-x`, `-rx`: Horizontal resolution (default: 1920)
- `--resolution-y`, `-ry`: Vertical resolution (default: 1080)
- `--engine`: Render engine - CYCLES, EEVEE, or WORKBENCH (default: CYCLES)
- `--samples`: Render samples (default: 128)
- `--fps`: Frames per second (default: 24)
- `--output`, `-o`: Save path

## scene open
Open an existing scene from file.
```bash
cli-anything-blender scene open <path>
```

## scene save
Save the current scene.
```bash
cli-anything-blender scene save [path]
```

## scene info
Show scene information.
```bash
cli-anything-blender scene info
```

## scene profiles
List available scene profiles.
```bash
cli-anything-blender scene profiles
```

## scene json
Print raw scene JSON.
```bash
cli-anything-blender scene json
```
