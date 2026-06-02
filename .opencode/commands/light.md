# Light Commands

## light add
Add a light to the scene.
```bash
cli-anything-blender light add <light_type> [options]
```
**Light Types:** point, sun, spot, area

**Options:**
- `--name`, `-n`: Light name
- `--location`, `-l`: Location x,y,z
- `--rotation`, `-r`: Rotation x,y,z (degrees)
- `--color`, `-c`: Color R,G,B (0.0-1.0)
- `--power`, `-w`: Power/energy

**Examples:**
```bash
cli-anything-blender light add sun --name "SunLight" --power 2.0
cli-anything-blender light add spot --location 5,5,10 --color 1,1,0.9
cli-anything-blender light add area --name "FillLight" --power 100
```

## light set
Set a light property.
```bash
cli-anything-blender light set <index> <prop> <value>
```
**Properties:** name, location, rotation, color, power, type

## light list
List all lights.
```bash
cli-anything-blender light list
```
