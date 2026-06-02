# Material Commands

## material create
Create a new material.
```bash
cli-anything-blender material create [options]
```
**Options:**
- `--name`, `-n`: Material name (default: "Material")
- `--color`, `-c`: Base color R,G,B,A (0.0-1.0)
- `--metallic`: Metallic factor (0.0-1.0)
- `--roughness`: Roughness factor (0.0-1.0)
- `--specular`: Specular factor (0.0-1.0)
- `--emission-color`, `-ec`: Emission color R,G,B,A (0.0-1.0)
- `--emission-strength`, `-es`: Emission strength (0.0-1000.0)

**Examples:**
```bash
cli-anything-blender material create --name "RedMetal" --color 1,0,0,1 --metallic 0.8
cli-anything-blender material create --name "Glow" --color 0.1,0.8,1,1 --emission-color 0.1,0.8,1,1 --emission-strength 5.0
```

## material assign
Assign a material to an object. **IMPORTANT: material name comes FIRST, object name comes SECOND.**
```bash
cli-anything-blender material assign <material_name> <object_name>
cli-anything-blender material assign <material_index> <object_index>
```
**Examples:**
```bash
cli-anything-blender material assign RobotGray Body      # by name
cli-anything-blender material assign 0 1                 # by index
```

## material set
Set a material property.
```bash
cli-anything-blender material set <index> <prop> <value>
```
**Properties:** color, metallic, roughness, specular, alpha, emission, emission_color, use_backface_culling

## material list
List all materials.
```bash
cli-anything-blender material list
```

## material get
Get detailed info about a material.
```bash
cli-anything-blender material get <index>
```
