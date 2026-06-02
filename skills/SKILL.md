---
name: "cli-anything-blender-ai"
description: "Blender AI Assistant Plugin - AI-powered 3D modeling with cloud APIs via CLI-Anything framework"
---

# cli-anything-blender-ai

## Overview

This plugin provides AI-powered 3D modeling capabilities within Blender, using CLI-Anything as the core framework for stateful CLI interactions.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Model Layer                           │
│     TripoSR  │  Hunyuan3D  │  Custom APIs                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CLI-Anything Core                         │
│  Blender Harness (scene, objects, materials, etc.)          │
│  Session Manager (undo/redo)                               │
│  SKILL.md for AI Agent discovery                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Blender Interface                        │
│  UI Panel (3D View > Sidebar > AI Assistant)               │
│  Operators (Reconstruct, Generate, etc.)                    │
└─────────────────────────────────────────────────────────────┘
```

## Installation

1. Copy the `CLI-Anything-Blender` folder to Blender's addon directory:
   - Windows: `%APPDATA%\Blender\<version>\scripts\addons\`
   - Linux: `~/.config/blender/<version>/scripts/addons/`
   - macOS: `~/Library/Application Support/Blender/<version>/scripts/addons/`

2. Enable the addon in Blender:
   - Open Blender
   - Go to Edit > Preferences > Add-ons
   - Search for "AI Assistant"
   - Enable the checkbox

## Usage Modes

### Text-to-3D (文生3D)
Generate 3D models from text descriptions alone.

### Image-to-3D (图生3D)
Generate 3D models from a single reference image.

### Hybrid (混元)
Combine text description with reference image for enhanced results.

## Supported Models

| Model | Mode | Description |
|-------|------|-------------|
| TripoSR | Image-to-3D | Fast local reconstruction from image |
| Hunyuan3D | All modes | Tencent cloud API supporting text/image/both |
| Custom | User-defined | Extensible API adapter interface |

## CLI Commands

The plugin exposes the following command groups via CLI-Anything:

### Scene Commands
```bash
blender-ai scene new --name "MyScene"
blender-ai scene save --path "path/to/project.json"
blender-ai scene load --path "path/to/project.json"
```

### Object Commands
```bash
blender-ai object add cube --name "Cube"
blender-ai object add sphere --name "Sphere"
blender-ai object list
blender-ai object select --name "Cube"
```

### Material Commands
```bash
blender-ai material create --name "Red" --color "1,0,0,1"
blender-ai material assign --name "Cube" --material "Red"
```

### AI Model Commands
```bash
blender-ai ai submit --model hunyuan3d --prompt "a modern chair"
blender-ai ai query --job-id "job_xxx"
blender-ai ai download --job-id "job_xxx" --output "model.glb"
```

### Reconstruction Commands
```bash
blender-ai reconstruct triposr --image "input.png" --resolution 256
blender-ai reconstruct hunyuan3d --prompt "a wooden table" --resolution 512
```

## API Credentials

### Hunyuan3D (Tencent Cloud)
1. Sign up at https://cloud.tencent.com
2. Enable Hunyuan3D service at https://console.cloud.tencent.com/hunyuan
3. Get SecretId/SecretKey from https://console.cloud.tencent.com/cam/capi
4. Configure permissions: `QcloudAI3DFullAccess`

## Configuration

Settings are stored in Blender's scene properties:
- `scene.tsr_selected_mode`: text2d, image2d, or hybrid
- `scene.tsr_selected_model`: triposr, hunyuan3d, or custom
- `scene.tsr_resolution`: Output resolution (64-1024)
- `scene.tsr_hunyuan_secret_id`: Tencent Cloud Secret ID
- `scene.tsr_hunyuan_secret_key`: Tencent Cloud Secret Key

## AI Agent Integration

This plugin is designed for AI Agent control via CLI-Anything:

1. AI Agent discovers Blender capabilities via SKILL.md
2. AI Agent issues CLI commands through the REPL interface
3. CLI-Anything Session manager provides undo/redo safety
4. Results are imported into Blender's 3D viewport

## Development

### Adding New AI Models

1. Create API adapter in `api/` directory:
```python
from api.base import BaseAPI, APIResponse, APIStatus

class CustomModelAPI(BaseAPI):
    def submit(self, prompt="", image_path="", **kwargs) -> APIResponse:
        # Implement API submission
        pass
    
    def query(self, job_id: str) -> APIResponse:
        # Implement job status query
        pass
    
    def download(self, job_id: str, output_path: str) -> APIResponse:
        # Implement result download
        pass
```

2. Register the operator in `operators/`
3. Add UI options in `ui/panel.py`

### Directory Structure
```
CLI-Anything-Blender/
├── __init__.py           # Plugin entry point
├── cli_anything/         # CLI-Anything core (embedded)
│   └── blender/          # Blender harness
├── api/                  # AI Model API adapters
├── operators/            # Blender operators
├── ui/                   # UI panel
├── utils/                # Utilities
└── skills/               # SKILL.md for AI discovery
```

## Troubleshooting

### Import Errors
Ensure all dependencies are installed:
```bash
pip install requests pillow numpy
```

### Hunyuan3D Authentication Failed
- Verify SecretId and SecretKey are correct
- Check that the Hunyuan3D service is enabled
- Ensure QcloudAI3DFullAccess policy is attached

### Mesh Not Appearing
- Check if the model file was downloaded successfully
- Verify GLB file format compatibility
- Try reducing resolution and retrying

## License

Commercial - All rights reserved