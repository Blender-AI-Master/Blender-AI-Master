# Blender: Project-Specific Analysis & SOP

## Architecture Summary

Blender is a professional 3D creation suite built on a Python API (bpy) and a
real-time rendering engine. The Blender CLI harness uses Blender's headless mode
to execute bpy scripts for scene manipulation and rendering.

```
┌──────────────────────────────────────────────┐
│               Blender GUI                     │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │  3D View │ │ Outliner │ │  Properties │  │
│  │  (OpenGL)│ │  (Tree)  │ │  (Panels)   │  │
│  └────┬─────┘ └────┬─────┘ └──────┬──────┘  │
│       │            │               │          │
│  ┌────┴────────────┴───────────────┴───────┐ │
│  │         bpy (Python API)                │ │
│  │  Scene graph, objects, materials, etc.   │ │
│  └─────────────────┬───────────────────────┘ │
│                    │                          │
│  ┌─────────────────┴───────────────────────┐ │
│  │       Rendering Engine (Cycles/EEVEE)   │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

## CLI Strategy: bpy Scripts + Blender Headless

Unlike some software that manipulates project files directly, Blender's strength
is its Python API. Our strategy:

1. **bpy Scripts** — Python scripts that use Blender's bpy API to create scenes
2. **Blender Headless** — `blender --background --python script.py` for rendering
3. **JSON State** — Session state stored as JSON for undo/redo support

### Why bpy Scripts?

- Blender's native format (.blend) is a complex binary format
- bpy API provides full access to all Blender features
- Scripts are human-readable and debuggable
- Native execution ensures correct results

## The Project Format (.blend-cli.json)

```json
{
  "version": "1.0",
  "name": "my_scene",
  "scene": {
    "name": "Scene",
    "engine": "CYCLES",
    "resolution_x": 1920,
    "resolution_y": 1080,
    "fps": 24
  },
  "objects": [
    {
      "name": "Cube",
      "type": "cube",
      "location": [0, 0, 0],
      "rotation": [0, 0, 0],
      "scale": [1, 1, 1]
    }
  ],
  "materials": [
    {
      "name": "RedMaterial",
      "color": [1, 0, 0, 1],
      "metallic": 0.0,
      "roughness": 0.5
    }
  ],
  "modifiers": [],
  "lights": [],
  "cameras": []
}
```

## Command Map: GUI Action -> CLI Command

| GUI Action | CLI Command |
|------------|-------------|
| Scene -> New | `scene new --name NAME` |
| Scene -> Open | `scene open <path>` |
| Scene -> Save | `scene save [path]` |
| Add -> Mesh -> Cube | `object add cube --name NAME` |
| Add -> Mesh -> UV Sphere | `object add sphere --name NAME` |
| Object -> Delete | `object remove <index>` |
| Object -> Duplicate | `object duplicate <index>` |
| Transform | `object transform <index> --translate X,Y,Z --rotate X,Y,Z --scale X,Y,Z` |
| Material -> New | `material create --name NAME --color R,G,B,A` |
| Material -> Assign | `material assign <mat_index> <obj_index>` |
| Modifier -> Add | `modifier add <type> --object <index>` |
| Light -> Add | `light add <type> --name NAME` |
| Camera -> Add | `camera add --name NAME --location X,Y,Z` |
| Keyframe -> Insert | `animation keyframe <obj> <frame> <prop> <value>` |
| Render | `render execute <output>` |

## Core Operations via bpy

### Object Types
| CLI Name | bpy API |
|----------|---------|
| `cube` | `bpy.ops.mesh.primitive_cube_add()` |
| `sphere` | `bpy.ops.mesh.primitive_uv_sphere_add()` |
| `cylinder` | `bpy.ops.mesh.primitive_cylinder_add()` |
| `cone` | `bpy.ops.mesh.primitive_cone_add()` |
| `plane` | `bpy.ops.mesh.primitive_plane_add()` |
| `torus` | `bpy.ops.mesh.primitive_torus_add()` |
| `monkey` | `bpy.ops.mesh.primitive_monkey_add()` |

### Material Properties
| Property | bpy Attribute |
|----------|---------------|
| `color` | `mat.metallic_roughness.default_value` |
| `metallic` | `mat.metallic` |
| `roughness` | `mat.roughness` |
| `specular` | `mat.specular` |

### Modifier Types
| CLI Name | bpy Type |
|----------|----------|
| `subdivision` | `SUBSURF` |
| `bevel` | `BEVEL` |
| `solidify` | `SOLIDIFY` |
| `boolean` | `BOOLEAN` |
| `mirror` | `MIRROR` |
| `array` | `ARRAY` |

## Rendering Pipeline

For Blender CLI, "rendering" means generating a bpy script that creates the scene
and executes it via Blender headless.

### Pipeline Steps:
1. Build scene JSON with all objects, materials, modifiers
2. Generate bpy script from JSON state
3. Execute via `blender --background --python script.py`
4. Blender renders to specified output

### Rendering Gap Assessment: **Low**
- All operations use Blender's native bpy API
- Full access to Cycles/EEVEE rendering
- No translation layer needed

## Test Coverage Plan

1. **Unit tests** (`test_core.py`): Synthetic data, no Blender needed
   - Scene create/open/save/info
   - Object add/remove/duplicate/transform
   - Material create/assign/set
   - Modifier add/remove/set
   - Light/camera add/set
   - Session undo/redo
   - JSON state serialization/deserialization

2. **E2E tests** (`test_full_e2e.py`): Requires Blender
   - Full workflow: scene create → object add → material → render
   - Real output file verification
   - CLI subprocess invocation
