"""UI module."""

from .panel import register as register_panel, unregister as unregister_panel
from . import debug_panel

def register():
    register_panel()
    debug_panel.register()

def unregister():
    debug_panel.unregister()
    unregister_panel()
