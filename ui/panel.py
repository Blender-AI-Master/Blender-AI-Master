"""UI Panel for AI Assistant - 中文界面."""

import bpy
from bpy.props import EnumProperty, StringProperty, BoolProperty, IntProperty, FloatProperty
from bpy.types import Panel, Operator


def get_translation(text):
    lang = bpy.context.preferences.view.language if bpy.context else "zh_CN"
    translations = {
        "zh_CN": {
            "AI Assistant": "AI 助手",
            "Mode": "模式",
            "Model": "模型",
            "Image": "图片",
            "Prompt": "描述",
            "Settings": "设置",
            "API Credentials": "API 凭证",
            "Secret ID": "Secret ID",
            "Secret Key": "Secret Key",
            "Generate 3D Model": "生成 3D 模型",
            "Select Image": "选择图片",
            "Progress": "进度",
            "Status": "状态",
            "Modeling": "建模",
            "AI Modeling": "AI 建模",
            "Reference Image": "参考图片",
            "Description": "描述",
            "Browse": "浏览",
            "Generate Model": "生成模型",
            "Decimation": "减面",
            "Target": "目标",
            "Preserve Topology": "保留拓扑",
            "Apply Decimation": "应用减面",
            "Topology": "拓扑",
            "Target Face Count": "目标面数",
            "Convert to Quads": "转换为四边面",
            "Remesh": "重网格化",
            "Rigging": "绑定",
            "Bone Type": "骨骼类型",
            "Auto Weight": "自动权重",
            "Generate Rig": "生成骨骼",
            "Animation": "动画",
            "Animation Type": "动画类型",
            "Duration": "时长",
            "Duration (seconds)": "时长（秒）",
            "Generate Animation": "生成动画",
            "Text to 3D": "文生3D",
            "Image to 3D": "图生3D",
            "Hybrid (Text+Image)": "混合（文+图）",
            "TripoAI": "TripoAI",
            "Hunyuan3D": "混元3D",
            "Custom": "自定义",
            "Fast local reconstruction": "快速本地重建",
            "Tencent cloud API": "腾讯云 API",
            "User-defined model": "用户自定义模型",
            "Text description only": "仅文本描述",
            "Image only": "仅图片",
            "Both text and image": "文本和图片",
            "Basic": "基础",
            "Biped": "双足",
            "Quadruped": "四足",
            "Basic chain": "基础链",
            "Humanoid rig": "人形骨骼",
            "Four-legged rig": "四足骨骼",
            "Rotation": "旋转",
            "Scale": "缩放",
            "Location": "位移",
            "Rotate around axis": "绕轴旋转",
            "Scale in/out": "放大/缩小",
            "Move along axis": "沿轴移动",
            "Resolution": "分辨率",
            "Remove Background": "移除背景",
            "Apply Post-Processing": "应用后期处理",
            "Image Files": "图片文件",
            "File Path": "文件路径",
            "No mesh selected": "未选择网格",
            "Decimation applied": "减面已应用",
            "Remesh complete": "重网格化完成",
            "Rig generated": "骨骼已生成",
            "Animation generated": "动画已生成",
            "Generating 3D model with": "正在生成 3D 模型",
            "Please enter Hunyuan3D API credentials": "请输入混元3D API 凭证",
            "Please select an image": "请选择图片",
            "Please enter a prompt": "请输入描述",
            "Please provide image or prompt": "请提供图片或描述",
            "Model not yet implemented": "该模型尚未实现",
        },
        "en_US": {
            "AI Assistant": "AI Assistant",
            "Mode": "Mode",
            "Model": "Model",
            "Image": "Image",
            "Prompt": "Prompt",
            "Settings": "Settings",
            "API Credentials": "API Credentials",
            "Secret ID": "Secret ID",
            "Secret Key": "Secret Key",
            "Generate 3D Model": "Generate 3D Model",
            "Select Image": "Select Image",
            "Progress": "Progress",
            "Status": "Status",
            "Modeling": "Modeling",
            "AI Modeling": "AI Modeling",
            "Reference Image": "Reference Image",
            "Description": "Description",
            "Browse": "Browse",
            "Generate Model": "Generate Model",
            "Decimation": "Decimation",
            "Target": "Target",
            "Preserve Topology": "Preserve Topology",
            "Apply Decimation": "Apply Decimation",
            "Topology": "Topology",
            "Target Face Count": "Target Face Count",
            "Convert to Quads": "Convert to Quads",
            "Remesh": "Remesh",
            "Rigging": "Rigging",
            "Bone Type": "Bone Type",
            "Auto Weight": "Auto Weight",
            "Generate Rig": "Generate Rig",
            "Animation": "Animation",
            "Animation Type": "Animation Type",
            "Duration": "Duration",
            "Duration (seconds)": "Duration (seconds)",
            "Generate Animation": "Generate Animation",
            "Text to 3D": "Text to 3D",
            "Image to 3D": "Image to 3D",
            "Hybrid (Text+Image)": "Hybrid (Text+Image)",
            "TripoAI": "TripoAI",
            "Hunyuan3D": "Hunyuan3D",
            "Custom": "Custom",
            "Fast local reconstruction": "Fast local reconstruction",
            "Tencent cloud API": "Tencent cloud API",
            "User-defined model": "User-defined model",
            "Text description only": "Text description only",
            "Image only": "Image only",
            "Both text and image": "Both text and image",
            "Basic": "Basic",
            "Biped": "Biped",
            "Quadruped": "Quadruped",
            "Basic chain": "Basic chain",
            "Humanoid rig": "Humanoid rig",
            "Four-legged rig": "Four-legged rig",
            "Rotation": "Rotation",
            "Scale": "Scale",
            "Location": "Location",
            "Rotate around axis": "Rotate around axis",
            "Scale in/out": "Scale in/out",
            "Move along axis": "Move along axis",
            "Resolution": "Resolution",
            "Remove Background": "Remove Background",
            "Apply Post-Processing": "Apply Post-Processing",
            "Image Files": "Image Files",
            "File Path": "File Path",
            "No mesh selected": "No mesh selected",
            "Decimation applied": "Decimation applied",
            "Remesh complete": "Remesh complete",
            "Rig generated": "Rig generated",
            "Animation generated": "Animation generated",
            "Generating 3D model with": "Generating 3D model with",
            "Please enter Hunyuan3D API credentials": "Please enter Hunyuan3D API credentials",
            "Please select an image": "Please select an image",
            "Please enter a prompt": "Please enter a prompt",
            "Please provide image or prompt": "Please provide image or prompt",
            "Model not yet implemented": "Model not yet implemented",
        }
    }
    return translations.get(lang, translations["zh_CN"]).get(text, text)


def __(text):
    return get_translation(text)


class AIAssistantModes:
    TEXT2D = "text2d"
    IMAGE2D = "image2d"
    HYBRID = "hybrid"


class AIAssistantModels:
    TRIPOSR = "triposr"
    HUNYUAN3D = "hunyuan3d"
    CSMAI = "csamai"
    MESHGPT = "meshgpt"
    LUMAAI = "lumaai"
    CUSTOM = "custom"


class AIAI_OT_select_image(Operator):
    bl_idname = "aiai.select_image"
    bl_label = "选择图片"
    bl_options = {'REGISTER'}
    
    filter_glob: StringProperty(
        name="图片文件",
        default="*.jpg;*.jpeg;*.png;*.bmp;*.tiff",
        options={'HIDDEN'}
    )
    
    filepath: StringProperty(name="文件路径", subtype='FILE_PATH', default="")
    
    def execute(self, context):
        if self.filepath:
            context.scene.tsr_image_path = self.filepath
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class AIAI_OT_generate(Operator):
    bl_idname = "aiai.generate"
    bl_label = "生成 3D 模型"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        
        mode = scene.tsr_selected_mode
        model = scene.tsr_selected_model
        
        if model == AIAssistantModels.HUNYUAN3D:
            if not scene.tsr_hunyuan_secret_id or not scene.tsr_hunyuan_secret_key:
                self.report({'ERROR'}, __("Please enter Hunyuan3D API credentials"))
                return {'CANCELLED'}
        
        if mode == AIAssistantModes.IMAGE2D:
            if not scene.tsr_image_path:
                self.report({'ERROR'}, __("Please select an image"))
                return {'CANCELLED'}
        elif mode == AIAssistantModes.TEXT2D:
            if not scene.tsr_prompt_text:
                self.report({'ERROR'}, __("Please enter a prompt"))
                return {'CANCELLED'}
        elif mode == AIAssistantModes.HYBRID:
            if not scene.tsr_image_path and not scene.tsr_prompt_text:
                self.report({'ERROR'}, __("Please provide image or prompt"))
                return {'CANCELLED'}
        
        self.report({'INFO'}, f"{__('Generating 3D model with')} {model}...")
        
        if model == AIAssistantModels.TRIPOSR:
            bpy.ops.aiai.tripoai_reconstruct()
        elif model == AIAssistantModels.HUNYUAN3D:
            bpy.ops.aiai.hunyuan_reconstruct()
        
        return {'FINISHED'}


class AIAI_OT_modeling_generate(Operator):
    bl_idname = "aiai.modeling_generate"
    bl_label = "生成模型"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        model = scene.tsr_selected_model
        
        if model == AIAssistantModels.TRIPOSR:
            bpy.ops.aiai.tripoai_reconstruct()
        elif model == AIAssistantModels.HUNYUAN3D:
            bpy.ops.aiai.hunyuan_reconstruct()
        else:
            self.report({'INFO'}, f"{model}: {__('Model not yet implemented')}")
            return {'CANCELLED'}
        
        return {'FINISHED'}


class AIAI_OT_decimate(Operator):
    bl_idname = "aiai.decimate"
    bl_label = "应用减面"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        ratio = scene.tsr_decimation_ratio
        
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, __("No mesh selected"))
            return {'CANCELLED'}
        
        for obj in selected:
            context.view_layer.objects.active = obj
            
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.001)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
            mod.ratio = ratio
            mod.use_symmetry = False
            
            if scene.tsr_decimation_preserveTopology:
                mod.use_collapse_triangulate = True
            
            bpy.ops.object.modifier_apply(modifier="Decimate")
        
        self.report({'INFO'}, f"{__('Decimation applied')}: {ratio*100:.0f}%")
        return {'FINISHED'}


class AIAI_OT_topology_remesh(Operator):
    bl_idname = "aiai.topology_remesh"
    bl_label = "重网格化"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        target = scene.tsr_target_face_count
        
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, __("No mesh selected"))
            return {'CANCELLED'}
        
        for obj in selected:
            context.view_layer.objects.active = obj
            
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
            bpy.ops.object.mode_set(mode='OBJECT')
            
            bpy.ops.object.modifier_add(type='REMESH')
            remesh_mod = obj.modifiers[-1]
            remesh_mod.mode = 'SHARP'
            remesh_mod.scale = 0.99
            remesh_mod.use_remove_disconnected = False
            
            bpy.ops.object.modifier_apply(modifier=remesh_mod.name)
            
            if scene.tsr_quadify:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.tris_convert_to_quads(aggressive=0)
                bpy.ops.object.mode_set(mode='OBJECT')
        
        self.report({'INFO'}, f"{__('Remesh complete')}: ~{target} {__('faces')}")
        return {'FINISHED'}


class AIAI_OT_rig_generate(Operator):
    bl_idname = "aiai.rig_generate"
    bl_label = "生成骨骼"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        rig_type = scene.tsr_rig_type
        
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, __("No mesh selected"))
            return {'CANCELLED'}
        
        for obj in selected:
            context.view_layer.objects.active = obj
            
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.armature.armature_add(location=(0, 0, 0))
            armature = context.view_layer.objects.active
            armature.name = f"{obj.name}_骨骼"
            
            bpy.ops.object.mode_set(mode='OBJECT')
            
            modifier = obj.modifiers.new(name="Armature", type='ARMATURE')
            modifier.object = armature
            
            if scene.tsr_auto_weights:
                bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        
        self.report({'INFO'}, f"{__('Rig generated')} ({__(rig_type)})")
        return {'FINISHED'}


class AIAI_OT_anim_generate(Operator):
    bl_idname = "aiai.anim_generate"
    bl_label = "生成动画"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        anim_type = scene.tsr_anim_type
        duration = scene.tsr_anim_duration
        
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, __("No mesh selected"))
            return {'CANCELLED'}
        
        for obj in selected:
            if not obj.animation_data:
                obj.animation_data_create()
            
            action = bpy.data.actions.new(name=f"{obj.name}_动画")
            obj.animation_data.action = action
            
            frame_start = context.scene.frame_start
            frame_end = frame_start + int(duration * 24)
            context.scene.frame_end = frame_end
            
            if anim_type == "rotation":
                context.scene.frame_current = frame_start
                obj.rotation_euler = (0, 0, 0)
                obj.keyframe_insert(data_path="rotation_euler", frame=frame_start)
                
                context.scene.frame_current = frame_end
                obj.rotation_euler = (0, 0, 6.28)
                obj.keyframe_insert(data_path="rotation_euler", frame=frame_end)
            elif anim_type == "scale":
                context.scene.frame_current = frame_start
                obj.scale = (1, 1, 1)
                obj.keyframe_insert(data_path="scale", frame=frame_start)
                
                context.scene.frame_current = frame_end
                obj.scale = (1.2, 1.2, 1.2)
                obj.keyframe_insert(data_path="scale", frame=frame_end)
            elif anim_type == "location":
                context.scene.frame_current = frame_start
                obj.location = (0, 0, 0)
                obj.keyframe_insert(data_path="location", frame=frame_start)
                
                context.scene.frame_current = frame_end
                obj.location = (0, 0, 2)
                obj.keyframe_insert(data_path="location", frame=frame_end)
        
        self.report({'INFO'}, f"{__('Animation generated')} ({__(anim_type)}, {duration}秒)")
        return {'FINISHED'}


class AIAI_PT_panel(Panel):
    bl_label = "AI 助手"
    bl_idname = "AIAI_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI 助手"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.label(text=__("Mode")+"：", icon="SETTINGS")
        row = layout.row(align=True)
        row.prop(scene, "tsr_selected_mode", expand=True)
        
        mode = scene.tsr_selected_mode
        
        layout.separator()
        layout.label(text=__("Model")+"：", icon="SOLO_ON")
        row = layout.row(align=True)
        row.prop(scene, "tsr_selected_model", expand=True)
        
        model = scene.tsr_selected_model
        
        layout.separator()
        
        layout.label(text="=== API Keys ===", icon="KEY")
        layout.prop(scene, "tsr_hunyuan_secret_id", text="Hunyuan Secret ID")
        layout.prop(scene, "tsr_hunyuan_secret_key", text="Hunyuan Secret Key")
        layout.prop(scene, "tsr_csma_secret_id", text="CSMAI API Key")
        layout.prop(scene, "tsr_meshgpt_api_key", text="MeshGPT API Key")
        layout.prop(scene, "tsr_luma_api_key", text="LumaAI API Key")
        
        layout.separator()
        
        if mode == AIAssistantModes.IMAGE2D or mode == AIAssistantModes.HYBRID:
            layout.label(text=__("Image")+"：", icon="IMAGE_DATA")
            layout.prop(scene, "tsr_image_path", text="")
            layout.operator("aiai.select_image", text=__("Select Image"), icon="FOLDER_REDIRECT")
            layout.separator()
        
        if mode == AIAssistantModes.TEXT2D or mode == AIAssistantModes.HYBRID:
            layout.label(text=__("Prompt")+"：", icon="TEXT")
            layout.prop(scene, "tsr_prompt_text", text="", textarea=True)
        
        layout.separator()
        
        layout.label(text=__("Settings")+"：", icon="PREFERENCES")
        layout.prop(scene, "tsr_resolution")
        layout.prop(scene, "tsr_remove_background")
        layout.prop(scene, "tsr_apply_post_process")
        
        layout.separator()
        
        layout.operator("aiai.generate", text=__("Generate 3D Model"), icon="AXIS_TOP")
        
        if hasattr(scene, "tsr_progress") and scene.tsr_progress > 0:
            layout.separator()
            layout.prop(scene, "tsr_progress", text=__("Progress"))
            layout.label(text=scene.tsr_status_text or "")


class AIAI_PT_modeling_tab(Panel):
    bl_label = "建模"
    bl_idname = "AIAI_PT_modeling_tab"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI 助手"
    bl_parent_id = "AIAI_PT_panel"
    bl_label_text = "建模"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.label(text=__("AI Modeling"), icon="MESH_CUBE")
        
        layout.separator()
        layout.label(text=__("Mode")+"：")
        row = layout.row(align=True)
        row.prop(scene, "tsr_selected_mode", expand=True)
        
        mode = scene.tsr_selected_mode
        
        if mode == AIAssistantModes.IMAGE2D or mode == AIAssistantModes.HYBRID:
            layout.separator()
            layout.label(text=__("Reference Image")+"：")
            layout.prop(scene, "tsr_image_path", text="")
            layout.operator("aiai.select_image", text=__("Browse"), icon="FOLDER_REDIRECT")
        
        if mode == AIAssistantModes.TEXT2D or mode == AIAssistantModes.HYBRID:
            layout.separator()
            layout.label(text=__("Description")+"：")
            layout.prop(scene, "tsr_prompt_text", text="", textarea=True)
        
        layout.separator()
        layout.label(text=__("Model")+"：")
        row = layout.row(align=True)
        row.prop(scene, "tsr_selected_model", expand=True)
        
        layout.separator()
        layout.prop(scene, "tsr_resolution")
        
        layout.separator()
        layout.operator("aiai.modeling_generate", text=__("Generate Model"), icon="AXIS_TOP")


class AIAI_PT_decimation_tab(Panel):
    bl_label = "减面"
    bl_idname = "AIAI_PT_decimation_tab"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI 助手"
    bl_parent_id = "AIAI_PT_panel"
    bl_label_text = "减面"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        col = layout.column(align=True)
        col.label(text=__("Decimation"), icon="GROUP")
        
        col.separator()
        col.label(text=__("Target")+"：")
        col.prop(scene, "tsr_decimation_ratio")
        
        col.separator()
        col.prop(scene, "tsr_decimation_preserveTopology")
        
        col.separator()
        col.operator("aiai.decimate", text=__("Apply Decimation"), icon="GROUP")


class AIAI_PT_topology_tab(Panel):
    bl_label = "拓扑"
    bl_idname = "AIAI_PT_topology_tab"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI 助手"
    bl_parent_id = "AIAI_PT_panel"
    bl_label_text = "拓扑"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        col = layout.column(align=True)
        col.label(text=__("Topology"), icon="MESH_GRID")
        
        col.separator()
        col.label(text=__("Target Face Count")+"：")
        col.prop(scene, "tsr_target_face_count")
        
        col.separator()
        col.prop(scene, "tsr_quadify")
        
        col.separator()
        col.operator("aiai.topology_remesh", text=__("Remesh"), icon="MESH_GRID")


class AIAI_PT_rigging_tab(Panel):
    bl_label = "绑定"
    bl_idname = "AIAI_PT_rigging_tab"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI 助手"
    bl_parent_id = "AIAI_PT_panel"
    bl_label_text = "绑定"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        col = layout.column(align=True)
        col.label(text=__("Rigging"), icon="BONE_DATA")
        
        col.separator()
        col.label(text=__("Bone Type")+"：")
        col.prop(scene, "tsr_rig_type", expand=True)
        
        col.separator()
        col.prop(scene, "tsr_auto_weights")
        
        col.separator()
        col.operator("aiai.rig_generate", text=__("Generate Rig"), icon="BONE_DATA")


class AIAI_PT_animation_tab(Panel):
    bl_label = "动画"
    bl_idname = "AIAI_PT_animation_tab"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI 助手"
    bl_parent_id = "AIAI_PT_panel"
    bl_label_text = "动画"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        col = layout.column(align=True)
        col.label(text=__("Animation"), icon="ANIM")
        
        col.separator()
        col.label(text=__("Animation Type")+"：")
        col.prop(scene, "tsr_anim_type", expand=True)
        
        col.separator()
        col.prop(scene, "tsr_anim_duration")
        
        col.separator()
        col.operator("aiai.anim_generate", text=__("Generate Animation"), icon="ANIM")


def register():
    bpy.types.Scene.tsr_selected_mode = bpy.props.EnumProperty(
        name="模式",
        items=[
            (AIAssistantModes.TEXT2D, "文生3D", "文本描述生成"),
            (AIAssistantModes.IMAGE2D, "图生3D", "图片生成"),
            (AIAssistantModes.HYBRID, "混合", "文本+图片"),
        ],
        default=AIAssistantModes.IMAGE2D
    )
    
    bpy.types.Scene.tsr_selected_model = bpy.props.EnumProperty(
        name="模型",
        items=[
            (AIAssistantModels.TRIPOSR, "TripoAI", "快速本地重建"),
            (AIAssistantModels.HUNYUAN3D, "混元3D", "腾讯云 API"),
            (AIAssistantModels.CSMAI, "CSMAI", "CSM API"),
            (AIAssistantModels.MESHGPT, "MeshGPT", "MeshGPT API"),
            (AIAssistantModels.LUMAAI, "LumaAI", "LumaAI API"),
            (AIAssistantModels.CUSTOM, "自定义", "用户自定义模型"),
        ],
        default=AIAssistantModels.TRIPOSR
    )
    
    bpy.types.Scene.tsr_prompt_text = bpy.props.StringProperty(
        name="描述",
        description="3D 模型生成描述",
        default="",
        maxlen=1024
    )
    
    bpy.types.Scene.tsr_progress = bpy.props.IntProperty(
        name="进度",
        default=0,
        min=0,
        max=100,
        subtype='PERCENTAGE'
    )
    
    bpy.types.Scene.tsr_status_text = bpy.props.StringProperty(
        name="状态",
        default=""
    )
    
    bpy.types.Scene.tsr_resolution = bpy.props.IntProperty(
        name="分辨率",
        default=256,
        min=64,
        max=1024
    )
    
    bpy.types.Scene.tsr_remove_background = bpy.props.BoolProperty(
        name="移除背景",
        default=True
    )
    
    bpy.types.Scene.tsr_apply_post_process = bpy.props.BoolProperty(
        name="应用后期处理",
        default=True
    )
    
    bpy.types.Scene.tsr_hunyuan_secret_id = bpy.props.StringProperty(
        name="Secret ID",
        description="腾讯云 Secret ID",
        default="",
        maxlen=256
    )
    
    bpy.types.Scene.tsr_hunyuan_secret_key = bpy.props.StringProperty(
        name="Secret Key",
        description="腾讯云 Secret Key",
        default="",
        maxlen=256
    )
    
    bpy.types.Scene.tsr_csma_secret_id = bpy.props.StringProperty(
        name="CSMAI API Key",
        description="CSMAI API Key",
        default="",
        maxlen=256
    )
    
    bpy.types.Scene.tsr_meshgpt_api_key = bpy.props.StringProperty(
        name="MeshGPT API Key",
        description="MeshGPT API Key",
        default="",
        maxlen=256
    )
    
    bpy.types.Scene.tsr_luma_api_key = bpy.props.StringProperty(
        name="LumaAI API Key",
        description="LumaAI API Key",
        default="",
        maxlen=256
    )
    
    bpy.types.Scene.tsr_decimation_ratio = bpy.props.FloatProperty(
        name="减面比率",
        default=0.1,
        min=0.01,
        max=1.0,
        subtype='FACTOR'
    )
    
    bpy.types.Scene.tsr_decimation_preserveTopology = bpy.props.BoolProperty(
        name="保留拓扑",
        default=True
    )
    
    bpy.types.Scene.tsr_target_face_count = bpy.props.IntProperty(
        name="目标面数",
        default=1000,
        min=100,
        max=100000
    )
    
    bpy.types.Scene.tsr_quadify = bpy.props.BoolProperty(
        name="转换为四边面",
        default=True
    )
    
    bpy.types.Scene.tsr_rig_type = bpy.props.EnumProperty(
        name="骨骼类型",
        items=[
            ("basic", "基础", "基础链"),
            ("biped", "双足", "人形骨骼"),
            ("quadruped", "四足", "四足骨骼"),
        ],
        default="basic"
    )
    
    bpy.types.Scene.tsr_auto_weights = bpy.props.BoolProperty(
        name="自动权重",
        default=True
    )
    
    bpy.types.Scene.tsr_anim_type = bpy.props.EnumProperty(
        name="动画类型",
        items=[
            ("rotation", "旋转", "绕轴旋转"),
            ("scale", "缩放", "放大/缩小"),
            ("location", "位移", "沿轴移动"),
        ],
        default="rotation"
    )
    
    bpy.types.Scene.tsr_anim_duration = bpy.props.FloatProperty(
        name="时长（秒）",
        default=2.0,
        min=0.1,
        max=60.0
    )
    
    panels = [
        AIAI_PT_panel,
        AIAI_PT_modeling_tab,
        AIAI_PT_decimation_tab,
        AIAI_PT_topology_tab,
        AIAI_PT_rigging_tab,
        AIAI_PT_animation_tab,
    ]
    
    operators = [
        AIAI_OT_select_image,
        AIAI_OT_generate,
        AIAI_OT_modeling_generate,
        AIAI_OT_decimate,
        AIAI_OT_topology_remesh,
        AIAI_OT_rig_generate,
        AIAI_OT_anim_generate,
    ]
    
    for cls in panels + operators:
        bpy.utils.register_class(cls)


def unregister():
    panels = [
        AIAI_PT_animation_tab,
        AIAI_PT_rigging_tab,
        AIAI_PT_topology_tab,
        AIAI_PT_decimation_tab,
        AIAI_PT_modeling_tab,
        AIAI_PT_panel,
    ]
    
    operators = [
        AIAI_OT_anim_generate,
        AIAI_OT_rig_generate,
        AIAI_OT_topology_remesh,
        AIAI_OT_decimate,
        AIAI_OT_modeling_generate,
        AIAI_OT_generate,
        AIAI_OT_select_image,
    ]
    
    for cls in operators + panels:
        bpy.utils.unregister_class(cls)
    
    props = [
        'tsr_selected_mode',
        'tsr_selected_model',
        'tsr_prompt_text',
        'tsr_progress',
        'tsr_status_text',
        'tsr_resolution',
        'tsr_remove_background',
        'tsr_apply_post_process',
        'tsr_hunyuan_secret_id',
        'tsr_hunyuan_secret_key',
        'tsr_csma_secret_id',
        'tsr_meshgpt_api_key',
        'tsr_luma_api_key',
        'tsr_decimation_ratio',
        'tsr_decimation_preserveTopology',
        'tsr_target_face_count',
        'tsr_quadify',
        'tsr_rig_type',
        'tsr_auto_weights',
        'tsr_anim_type',
        'tsr_anim_duration',
    ]
    for prop in props:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)