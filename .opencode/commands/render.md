# Render Commands

## render settings
Configure render settings.
```bash
cli-anything-blender render settings [options]
```
**Options:**
- `--engine`: Render engine - CYCLES, EEVEE, WORKBENCH
- `--resolution-x`, `-rx`: Horizontal resolution
- `--resolution-y`, `-ry`: Vertical resolution
- `--resolution-percentage`: Resolution percentage
- `--samples`: Render samples
- `--denoising`, `--no-denoising`: Enable/disable denoising
- `--transparent`, `--no-transparent`: Enable/disable transparent film
- `--format`: Output format (PNG, JPEG, EXR, etc.)
- `--output-path`: Output path
- `--preset`: Apply render preset

**Examples:**
```bash
cli-anything-blender render settings --engine CYCLES --samples 256
cli-anything-blender render settings --transparent --format PNG
```

## render info
Show current render settings.
```bash
cli-anything-blender render info
```

## render presets
List available render presets.
```bash
cli-anything-blender render presets
```

## render execute
Render the scene (generates bpy script).
```bash
cli-anything-blender render execute <output_path> [options]
```
**Options:**
- `--frame`, `-f`: Specific frame to render
- `--animation`, `-a`: Render full animation
- `--overwrite`: Overwrite existing file

## render script
Generate bpy script without rendering.
```bash
cli-anything-blender render script <output_path> [options]
```
**Options:**
- `--frame`, `-f`: Specific frame
- `--animation`, `-a`: Generate animation script
