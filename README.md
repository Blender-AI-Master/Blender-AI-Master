# Blender AI Assistant - CLI-Anything Plugin

**AI驱动的 Blender 3D 建模插件 —— 用自然语言指挥创意实现**

通过 OpenCode AI 的多轮思考能力，将"帮我做一个机器人"这样的自然语言需求，转化为精确的 CLI-Anything 命令序列，实时同步到 Blender 视口。

## Features

- **Natural Language Modeling** - OpenCode Creative Agent understands design intent and generates complete modeling commands
- **Real-time Preview** - CLI commands sync to Blender viewport immediately, no manual refresh needed
- **Incremental Updates** - Only updates changed elements, preserving manual Blender modifications
- **Stateful Commands** - JSON-based project system supports complex scene construction

## Architecture

```
User Input → OpenCode AI → CLI Commands → Blender Viewport
     ↓
Natural Language → Multi-round Thinking → Incremental Sync
```

### Key Components

| Component | Description |
|-----------|-------------|
| `AIAI_OT_send_chat` | Main operator that orchestrates the flow |
| `OpenCodeProvider` | Communicates with OpenCode AI |
| `CLIAnythingManager` | Executes CLI-Anything commands |
| `apply_project` | Syncs JSON state to Blender viewport |

## Requirements

- Blender 4.0+
- Python 3.10+
- OpenCode AI (for natural language modeling)
- CLI-Anything Blender package

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Blender-AI-Master/CLI-Anything-Blender.git
```

2. Copy the plugin folder to Blender's addons directory:
```bash
# Windows
copy CLI-Anything-Blender %APPDATA%\Blender Foundation\Blender\4.1\scripts\addons\

# macOS/Linux
cp -r CLI-Anything-Blender ~/.config/blender/4.1/scripts/addons/
```

3. Enable the plugin in Blender: Edit → Preferences → Add-ons → Search "AI Assistant" → Enable

## Usage

1. **Select OpenCode Provider** in the AI Assistant panel
2. **Enter your API key** for OpenCode
3. **Type your request** in natural language, e.g.:
   - "帮我做一个机器人"
   - "Create a detailed robot with emission materials"
   - "Add a subdivision modifier to the body"
4. **Click Send** - Watch your model appear in the viewport!

## Supported Commands

| Command | Description |
|---------|-------------|
| `scene new` | Create a new scene |
| `object add <type>` | Add primitives (cube, sphere, cylinder, etc.) |
| `material create` | Create PBR materials with emission support |
| `material assign` | Assign materials to objects |
| `modifier add` | Add modifiers (subdivision, bevel, solidify, etc.) |

## Configuration

The plugin stores configuration in Blender's scene properties:
- `tsr_llm_provider` - LLM provider selection
- `tsr_llm_api_key` - API key for selected provider
- `tsr_llm_model` - Model selection

## License

MIT License

## Acknowledgments

- [OpenCode AI](https://github.com/opencode-ai/opencode) - Multi-round thinking agent
- [CLI-Anything](https://github.com/TripoAI/cli-anything) - Statefu CLI for Blender
