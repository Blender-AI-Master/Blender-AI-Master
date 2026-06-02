# Object Commands

## object add
Add a 3D primitive object.
```bash
cli-anything-blender object add <mesh_type> [options]
```
**Mesh Types:** cube, sphere, cylinder, cone, plane, torus, monkey, empty

**Options:**
- `--name`, `-n`: Object name
- `--location`, `-l`: Location x,y,z
- `--rotation`, `-r`: Rotation x,y,z (degrees)
- `--scale`, `-s`: Scale x,y,z
- `--param`, `-p`: Mesh parameter (key=value)
- `--collection`, `-c`: Target collection

**Examples:**
```bash
cli-anything-blender object add cube --name "Box" --location 0,0,0
cli-anything-blender object add sphere --name "Ball" --param "radius=2.0"
cli-anything-blender object add torus --name "Ring" --rotation 0,45,0
```

## object remove
Remove an object by index.
```bash
cli-anything-blender object remove <index>
```

## object duplicate
Duplicate an object.
```bash
cli-anything-blender object duplicate <index>
```

## object transform
Transform an object (translate, rotate, scale).
```bash
cli-anything-blender object transform <index> [options]
```
**Options:**
- `--translate`, `-t`: Translate dx,dy,dz
- `--rotate`, `-r`: Rotate rx,ry,rz (degrees)
- `--scale`, `-s`: Scale sx,sy,sz (multiplier)

## object set
Set an object property.
```bash
cli-anything-blender object set <index> <prop> <value>
```
**Properties:** name, visible, location, rotation, scale, parent

## object list
List all objects.
```bash
cli-anything-blender object list
```

## object get
Get detailed info about an object.
```bash
cli-anything-blender object get <index>
```
