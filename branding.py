"""Blender-AI Master brand assets exposed to the Blender UI."""
import os
import bpy
import bpy.utils.previews

_BRANDING_DIR = os.path.join(os.path.dirname(__file__), "resources", "branding")
_previews = None


def register() -> None:
    global _previews
    if _previews is not None:
        return
    _previews = bpy.utils.previews.new()
    # 优先加载白色版(深色 Blender 主题下可见),如果不存在则用原始版本
    white_path = os.path.join(_BRANDING_DIR, "blender-ai-wordmark-white.png")
    orig_path = os.path.join(_BRANDING_DIR, "blender-ai-wordmark.png")
    if os.path.exists(white_path):
        _previews.load("wordmark", white_path, "IMAGE")
    else:
        _previews.load("wordmark", orig_path, "IMAGE")


def unregister() -> None:
    global _previews
    if _previews is not None:
        bpy.utils.previews.remove(_previews)
        _previews = None


def wordmark_icon_id() -> int:
    return _previews["wordmark"].icon_id if _previews else 0


def draw_header(layout, scale=16.0):
    """Render the wordmark image centered at the top of a panel (like fal.ai).

    LOGO 缩小一倍 (scale 32.0 -> 16.0),源图来自 C:/Users/Administrator/Desktop/jietu/15.png (1067x160, RGBA)。
    """
    if _previews is None:
        return
    row = layout.row()
    row.alignment = "CENTER"
    row.template_icon(icon_value=wordmark_icon_id(), scale=scale)
