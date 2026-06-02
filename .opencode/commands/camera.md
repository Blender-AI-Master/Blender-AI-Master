# Camera Commands

## camera add
Add a camera to the scene.
```bash
cli-anything-blender camera add [options]
```
**Options:**
- `--name`, `-n`: Camera name
- `--location`, `-l`: Location x,y,z
- `--rotation`, `-r`: Rotation x,y,z (degrees)
- `--type`: Camera type - PERSP, ORTHO, PANO (default: PERSP)
- `--focal-length`, `-f`: Focal length in mm (default: 50.0)
- `--active`: Set as active camera

**Examples:**
```bash
cli-anything-blender camera add --name "MainCam" --location 5,5,3 --active
cli-anything-blender camera add --type ORTHO --focal-length 50
```

## camera set
Set a camera property.
```bash
cli-anything-blender camera set <index> <prop> <value>
```
**Properties:** name, location, rotation, type, focal_length

## camera set-active
Set the active camera.
```bash
cli-anything-blender camera set-active <index>
```

## camera list
List all cameras.
```bash
cli-anything-blender camera list
```
