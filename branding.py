"""Blender-AI Master brand assets exposed to the Blender UI.

Renders a header at the top of the addon preferences panel.
Falls back to text if image loading fails (so the panel is never broken).
"""
import os
import bpy
import bpy.utils.previews


_BRANDING_DIR = os.path.join(os.path.dirname(__file__), "resources", "branding")
_previews = None
_wordmark_loaded = False


def register() -> None:
    """Load the wordmark PNG into Blender's preview cache. Idempotent."""
    global _previews, _wordmark_loaded
    if _previews is not None:
        return
    try:
        _previews = bpy.utils.previews.new()
    except Exception as e:
        print(f"[branding] previews.new() failed: {e}")
        return

    white_path = os.path.join(_BRANDING_DIR, "blender-ai-wordmark-white.png")
    orig_path  = os.path.join(_BRANDING_DIR, "blender-ai-wordmark.png")
    chosen = None
    if os.path.exists(white_path):
        chosen = white_path
    elif os.path.exists(orig_path):
        chosen = orig_path

    if chosen:
        try:
            _previews.load("wordmark", chosen, "IMAGE")
            _wordmark_loaded = True
        except Exception as e:
            print(f"[branding] failed to load {chosen}: {e}")
            _wordmark_loaded = False


def unregister() -> None:
    global _previews, _wordmark_loaded
    if _previews is not None:
        try:
            bpy.utils.previews.remove(_previews)
        except Exception:
            pass
        _previews = None
    _wordmark_loaded = False


def wordmark_icon_id() -> int:
    """Return the icon_id for the loaded wordmark, or 0 if not loaded."""
    if _previews is None or not _wordmark_loaded:
        return 0
    try:
        return _previews["wordmark"].icon_id
    except KeyError:
        return 0


def draw_header(layout, scale=1.0):
    """Render a header at the top of the preferences panel.

    Uses a small icon (scale=1.0) + text label as the title.
    Avoids the original problem where scale=8.0 + a wide 1067x160 PNG
    caused Blender's `template_icon` to reserve ~160px of empty space
    (icon would clip to a square and appear blank).

    The `scale` parameter is kept for API compatibility but ignored.
    """
    icon_id = wordmark_icon_id()
    row = layout.row()
    row.alignment = "CENTER"
    # 用一个小的 icon + 文字 logo,清晰可见
    if icon_id != 0:
        # icon + 文字 - icoid 跟其他 icon 一致大小,不会撑大 layout
        row.label(text="Blender-AI Master", icon_value=icon_id)
    else:
        # fallback: 纯文字 + Blender 内置 icon
        row.label(text="Blender-AI Master", icon="OUTLINER")
