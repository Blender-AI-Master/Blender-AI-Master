# Animation Commands

## animation keyframe
Set a keyframe on an object.
```bash
cli-anything-blender animation keyframe <object_index> <frame> <prop> <value> [options]
```
**Options:**
- `--interpolation`, `-i`: Interpolation type - CONSTANT, LINEAR, BEZIER (default: BEZIER)

**Examples:**
```bash
cli-anything-blender animation keyframe 0 1 location 0,0,0
cli-anything-blender animation keyframe 0 24 location 5,0,0
cli-anything-blender animation keyframe 0 48 rotation 0,360,0 --interpolation LINEAR
```

## animation remove-keyframe
Remove a keyframe from an object.
```bash
cli-anything-blender animation remove-keyframe <object_index> <frame> [options]
```
**Options:**
- `--prop`, `-p`: Property (remove all at frame if not specified)

## animation frame-range
Set the animation frame range.
```bash
cli-anything-blender animation frame-range <start> <end>
```

## animation fps
Set the animation FPS.
```bash
cli-anything-blender animation fps <fps>
```

## animation list-keyframes
List keyframes for an object.
```bash
cli-anything-blender animation list-keyframes <object_index> [options]
```
**Options:**
- `--prop`, `-p`: Filter by property
