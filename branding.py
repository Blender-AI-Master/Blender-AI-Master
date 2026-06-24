"""Blender-AI Master brand assets exposed to the Blender UI.

Renders the user-supplied wordmark logo at the top of the addon
preferences panel. Falls back to text + built-in icon if the image
can't be loaded (so the panel is never broken).
"""
import os
import bpy
import bpy.utils.previews


_BRANDING_DIR = os.path.join(os.path.dirname(__file__), "resources", "branding")
_previews = None
_logo_loaded = False
_logo_path = None


def _pick_logo() -> str:
    """Pick the best available logo file. Order:
    1. logo-white.png  (user's preferred, dark theme friendly)
    2. blender-ai-wordmark-white.png
    3. blender-ai-wordmark.png
    """
    candidates = [
        "logo-white.png",
        "blender-ai-wordmark-white.png",
        "blender-ai-wordmark.png",
    ]
    for name in candidates:
        p = os.path.join(_BRANDING_DIR, name)
        if os.path.exists(p):
            return p
    return ""


def register() -> None:
    """Load the wordmark PNG into Blender's preview cache. Idempotent."""
    global _previews, _logo_loaded, _logo_path
    if _previews is not None:
        return
    try:
        _previews = bpy.utils.previews.new()
    except Exception as e:
        print(f"[branding] previews.new() failed: {e}")
        return

    _logo_path = _pick_logo()
    if not _logo_path:
        print(f"[branding] no logo found in {_BRANDING_DIR}")
        return

    try:
        _previews.load("logo", _logo_path, "IMAGE")
        _logo_loaded = True
    except Exception as e:
        print(f"[branding] failed to load {_logo_path}: {e}")
        _logo_loaded = False


def unregister() -> None:
    global _previews, _logo_loaded, _logo_path
    if _previews is not None:
        try:
            bpy.utils.previews.remove(_previews)
        except Exception:
            pass
        _previews = None
    _logo_loaded = False
    _logo_path = None


def logo_icon_id() -> int:
    """Return the icon_id for the loaded logo, or 0 if not loaded."""
    if _previews is None or not _logo_loaded:
        return 0
    try:
        return _previews["logo"].icon_id
    except KeyError:
        return 0


def draw_header(layout, scale=1.0):
    """Render the wordmark logo at the top of the preferences panel.

    Uses `row.scale_y` < 1.0 to make the row SHORTER (so a wide banner
    logo doesn't leave a huge empty area below it like the old
    scale=8.0 implementation did). The icon is rendered via
    `template_icon` at scale=1.0 (default 20-24 px), and the row
    scale controls the row's apparent height.

    The `scale` argument is kept for API compatibility and acts as a
    visual multiplier (0.5 = tiny, 1.0 = normal, 2.0 = larger).
    """
    icon_id = logo_icon_id()

    if icon_id == 0:
        # Fallback: 文字 + Blender 内置 icon
        row = layout.row()
        row.alignment = "CENTER"
        row.label(text="Blender-AI Master", icon="OUTLINER")
        return

    # 渲染 logo
    # - row.scale_y 调小 (0.5) 让行变矮,避免 326x56 banner 在正方形 icon 区域下留白
    # - alignment = "CENTER" 居中
    # - template_icon(scale=1.0) 默认 ~20x20 px icon 区
    row = layout.row()
    row.alignment = "CENTER"
    row.scale_y = 0.7  # 行高压缩
    row.template_icon(icon_value=icon_id, scale=1.0)
