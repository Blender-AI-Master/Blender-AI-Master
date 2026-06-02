# Modifier Commands

## IMPORTANT: Command Structure
Modifiers are added with `modifier add`, NOT `object add`.
- `object add` is for creating new objects (cube, sphere, cylinder, etc.)
- `modifier add` is for adding modifiers to existing objects

## modifier list-available
List all available modifiers.
```bash
cli-anything-blender modifier list-available [options]
```
**Options:**
- `--category`, `-c`: Filter by category (generate, deform)

## modifier info
Show details about a modifier.
```bash
cli-anything-blender modifier info <name>
```

## modifier add
Add a modifier to an object. **NOTE: --object takes an object INDEX (0-based), not a name.**
```bash
cli-anything-blender modifier add <modifier_type> [options]
```
**Options:**
- `--object`, `-o`: Object index (0-based, required)
- `--name`, `-n`: Custom modifier name
- `--param`, `-p`: Parameter (key=value, can be repeated)

**Examples:**
```bash
# Add subdivision modifier to object at index 0
cli-anything-blender modifier add subdivision --object 0 --param "levels=3"

# Add solidify modifier with multiple params
cli-anything-blender modifier add solidify --object 0 --param "thickness=0.1"

# Add bevel modifier
cli-anything-blender modifier add bevel --object 0 --param "segments=2" --param "width=0.05"
```

## modifier remove
Remove a modifier by index.
```bash
cli-anything-blender modifier remove <modifier_index> --object <object_index>
```

## modifier set
Set a modifier parameter.
```bash
cli-anything-blender modifier set <modifier_index> <param> <value> --object <object_index>
```

## modifier list
List modifiers on an object.
```bash
cli-anything-blender modifier list --object <object_index>
```
