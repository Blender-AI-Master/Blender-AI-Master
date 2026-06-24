"""Settings management for the plugin."""

import bpy
from typing import Optional


class AIAssistantSettings:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_defaults()
        return cls._instance
    
    def _init_defaults(self):
        self.hunyuan_secret_id = ""
        self.hunyuan_secret_key = ""
        self.selected_model = "hunyuan"
        self.selected_mode = "text2d"
        self.resolution = 256
        self.remove_background = True
        self.apply_post_process = True
    
    @classmethod
    def get_scene_props(cls):
        return bpy.types.Scene
        
    def register(self):
        Scene = self.get_scene_props()
        
        Scene.tsr_hunyuan_secret_id = bpy.props.StringProperty(
            name="Hunyuan Secret ID",
            description="Tencent Cloud Secret ID for Hunyuan3D API",
            default="",
            maxlen=256,
            subtype='NONE'
        )
        
        Scene.tsr_hunyuan_secret_key = bpy.props.StringProperty(
            name="Hunyuan Secret Key", 
            description="Tencent Cloud Secret Key for Hunyuan3D API",
            default="",
            maxlen=256,
            subtype='PASSWORD'
        )
        
        Scene.tsr_selected_model = bpy.props.StringProperty(
            name="Selected Model",
            default="hunyuan",
            maxlen=64
        )
        
        Scene.tsr_selected_mode = bpy.props.StringProperty(
            name="Selected Mode",
            default="text2d",
            maxlen=32
        )
        
        Scene.tsr_resolution = bpy.props.IntProperty(
            name="Resolution",
            default=256,
            min=64,
            max=1024
        )
        
        Scene.tsr_remove_background = bpy.props.BoolProperty(
            name="Remove Background",
            default=True
        )
        
        Scene.tsr_apply_post_process = bpy.props.BoolProperty(
            name="Apply Post-Processing",
            default=True
        )
        
        Scene.tsr_image_path = bpy.props.StringProperty(
            name="Image Path",
            description="Path to input image for reconstruction",
            default="",
            maxlen=1024,
            subtype='FILE_PATH'
        )
    
    def unregister(self):
        Scene = self.get_scene_props()
        props = [
            'tsr_hunyuan_secret_id',
            'tsr_hunyuan_secret_key', 
            'tsr_selected_model',
            'tsr_selected_mode',
            'tsr_resolution',
            'tsr_remove_background',
            'tsr_apply_post_process',
            'tsr_image_path',
        ]
        for prop in props:
            if hasattr(Scene, prop):
                delattr(Scene, prop)
    
    @property
    def secret_id(self) -> str:
        return getattr(bpy.context.scene, 'tsr_hunyuan_secret_id', "")
    
    @secret_id.setter
    def secret_id(self, value: str):
        bpy.context.scene.tsr_hunyuan_secret_id = value
    
    @property
    def secret_key(self) -> str:
        return getattr(bpy.context.scene, 'tsr_hunyuan_secret_key', "")
    
    @secret_key.setter
    def secret_key(self, value: str):
        bpy.context.scene.tsr_hunyuan_secret_key = value


_settings_instance: Optional[AIAssistantSettings] = None


def get_settings() -> AIAssistantSettings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = AIAssistantSettings()
    return _settings_instance


def register_settings():
    get_settings().register()


def unregister_settings():
    get_settings().unregister()
    global _settings_instance
    _settings_instance = None