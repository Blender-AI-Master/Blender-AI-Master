"""Minimal test panel for debugging."""

import bpy
from bpy.props import StringProperty
from bpy.types import Panel


class AIAI_OT_test_input(bpy.types.Operator):
    bl_idname = "aiai.test_input"
    bl_label = "Test"
    bl_options = {'REGISTER'}
    
    test_prop: StringProperty(name="Test Input", default="")
    
    def execute(self, context):
        self.report({'INFO'}, f"Test value: {context.scene.test_input_prop}")
        return {'FINISHED'}


class AIAI_PT_debug_panel(Panel):
    bl_label = "DEBUG Panel"
    bl_idname = "AIAI_PT_debug_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DEBUG"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.label(text="DEBUG: API Keys Section", icon="KEY")
        
        if hasattr(scene, "tsr_hunyuan_secret_id"):
            layout.prop(scene, "tsr_hunyuan_secret_id", text="Hunyuan Secret ID")
        else:
            layout.label(text="ERROR: tsr_hunyuan_secret_id not found!", icon="ERROR")
        
        if hasattr(scene, "tsr_hunyuan_secret_key"):
            layout.prop(scene, "tsr_hunyuan_secret_key", text="Hunyuan Secret Key")
        else:
            layout.label(text="ERROR: tsr_hunyuan_secret_key not found!", icon="ERROR")
        
        layout.separator()
        layout.operator("aiai.test_input", text="Test Button")


classes = [
    AIAI_OT_test_input,
    AIAI_PT_debug_panel,
]


def register():
    bpy.types.Scene.test_input_prop = bpy.props.StringProperty(
        name="Test Input",
        default="test_value_123"
    )
    
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    if hasattr(bpy.types.Scene, "test_input_prop"):
        delattr(bpy.types.Scene, "test_input_prop")


if __name__ == "__main__":
    register()
