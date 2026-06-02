# Preview Commands

## preview recipes
List available preview recipes.
```bash
cli-anything-blender preview recipes
```

## preview capture
Capture a preview bundle for the active scene.
```bash
cli-anything-blender preview capture [options]
```
**Options:**
- `--recipe`: Preview recipe name (default: "quick")
- `--force`: Bypass preview cache
- `--root-dir`: Override preview bundle root directory

## preview latest
Show the latest preview bundle manifest.
```bash
cli-anything-blender preview latest [options]
```
**Options:**
- `--recipe`: Filter by recipe name
- `--root-dir`: Override preview bundle root directory

## preview live start
Start a live preview session.
```bash
cli-anything-blender preview live start [options]
```
**Options:**
- `--recipe`: Preview recipe name (default: "quick")
- `--force`: Bypass preview cache
- `--root-dir`: Override preview root directory
- `--poll-ms`: Suggested viewer polling interval (default: 1500)
- `--mode`: Live preview mode - poll, manual (default: poll)
- `--source-poll-ms`: Source polling interval (default: 500)
- `--open`: Launch cli-hub live viewer

## preview live push
Publish a fresh bundle into the live preview session.
```bash
cli-anything-blender preview live push [options]
```

## preview live status
Show live preview session metadata.
```bash
cli-anything-blender preview live status [options]
```

## preview live stop
Stop the live preview session.
```bash
cli-anything-blender preview live stop [options]
```
