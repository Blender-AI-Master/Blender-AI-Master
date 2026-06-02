"""Blender AI Assistant Plugin - CLI-Anything based 3D modeling with AI."""

bl_info = {
    "name": "AI Assistant for Blender",
    "author": "TripoAR Team",
    "version": (2, 5, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > AI Assistant",
    "description": "AI-powered 3D modeling assistant",
    "category": "3D View",
}

import bpy
import os
import time
import json
import hashlib
import hmac
import base64
import tempfile
from bpy.props import StringProperty, EnumProperty, BoolProperty, IntProperty, FloatProperty
from bpy.types import Panel, Operator

from .api import Hunyuan3DAPI, APIStatus, APIResponse

_last_texture_path = ""


AI_MODELS = [
    ("triposr", "TripoAI", "Fast local reconstruction"),
    ("hunyuan", "混元3D", "Tencent cloud API"),
    ("csamai", "CSMAI", "CSM API"),
    ("meshgpt", "MeshGPT", "MeshGPT API"),
    ("lumaai", "LumaAI", "LumaAI API"),
]

AI_MODES = [
    ("text2d", "文生3D", "Text description only"),
    ("image2d", "图生3D", "Image only"),
    ("hybrid", "混合", "Both text and image"),
]

LLM_PROVIDERS = [
    ("openai", "OpenAI", "gpt-4o, gpt-4.1"),
    ("anthropic", "Anthropic", "claude-3-5-sonnet"),
    ("gemini", "Google Gemini", "gemini-2.5-flash"),
    ("deepseek", "DeepSeek", "deepseek-chat"),
    ("qwen", "阿里通义", "qwen-plus"),
    ("zhipu", "智谱GLM", "glm-4-plus"),
    ("minimax", "MiniMax", "MiniMax-01"),
    ("opencode", "OpenCode", "创意多轮思考 AI"),
    ("ollama", "Ollama", "本地模型"),
]


class AIAI_OT_select_image(Operator):
    bl_idname = "aiai.select_image"
    bl_label = "选择图片"
    filter_glob: StringProperty(default="*.jpg;*.jpeg;*.png;*.bmp;*.tiff", options={'HIDDEN'})
    filepath: StringProperty(subtype='FILE_PATH', default="")
    
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
        model = scene.tsr_selected_model
        
        if model == "hunyuan":
            if not scene.tsr_hunyuan_secret_id or not scene.tsr_hunyuan_secret_key:
                self.report({'ERROR'}, "请输入混元3D API凭证")
                return {'CANCELLED'}
            
            if not scene.tsr_image_path and scene.tsr_selected_mode == "image2d":
                self.report({'ERROR'}, "请选择图片")
                return {'CANCELLED'}
            
            self.report({'INFO'}, "正在提交混元3D任务...")
            
            api = Hunyuan3DAPI(scene.tsr_hunyuan_secret_id, scene.tsr_hunyuan_secret_key)
            response = api.submit(
                prompt=scene.tsr_prompt_text,
                image_path=scene.tsr_image_path,
                resolution=scene.tsr_resolution
            )
            
            if not response.success:
                self.report({'ERROR'}, f"提交失败: {response.error}")
                return {'CANCELLED'}
            
            job_id = response.job_id
            self.report({'INFO'}, f"任务已提交 JobId={job_id}，等待处理...")
            print(f"DEBUG: Job submitted, job_id={job_id}")
            
            result = api.wait_for_completion(job_id, timeout=600, poll_interval=5)
            print(f"DEBUG: wait_for_completion result: success={result.success}, status={result.status}, error={result.error}")
            
            if not result.success:
                self.report({'ERROR'}, f"任务失败: {result.error}")
                return {'CANCELLED'}
            
            self.report({'INFO'}, "正在下载模型...")
            
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"hunyuan_{job_id}.glb")
            zip_path = os.path.join(temp_dir, f"hunyuan_{job_id}.zip")
            
            download_result = api.download(job_id, zip_path)
            
            if not download_result.success:
                self.report({'ERROR'}, f"下载失败: {download_result.error}")
                return {'CANCELLED'}
            
            self.report({'INFO'}, f"模型已下载，正在处理...")
            
            try:
                import zipfile
                
                extracted_glb = None
                extracted_obj = None
                extracted_mtl = None
                
                if zipfile.is_zipfile(zip_path):
                    with zipfile.ZipFile(zip_path, 'r') as z:
                        print(f"DEBUG: Zip contents: {z.namelist()}")
                        z.extractall(temp_dir)
                        for name in z.namelist():
                            if name.endswith('.glb') or name.endswith('.gltf'):
                                extracted_glb = os.path.join(temp_dir, name)
                            elif name.endswith('.obj'):
                                extracted_obj = os.path.join(temp_dir, name)
                            elif name.endswith('.mtl'):
                                extracted_mtl = os.path.join(temp_dir, name)
                    
                    if extracted_glb:
                        output_path = extracted_glb
                        self.report({'INFO'}, f"文件已解压(GLB): {output_path}")
                    elif extracted_obj:
                        output_path = extracted_obj
                        self.report({'INFO'}, f"文件已解压(OBJ): {output_path}")
                    else:
                        output_path = zip_path
                else:
                    output_path = zip_path
                
                print(f"DEBUG: Looking for file at: {output_path}")
                print(f"DEBUG: File exists: {os.path.exists(output_path)}")
                
                if os.path.exists(output_path):
                    with open(output_path, 'rb') as f:
                        header = f.read(4)
                        f.seek(0, 2)
                        size = f.tell()
                    print(f"DEBUG: File header: {header}, size: {size}")
                
                if not os.path.exists(output_path):
                    self.report({'ERROR'}, f"文件不存在: {output_path}")
                    return {'CANCELLED'}
                
                if extracted_obj:
                    try:
                        obj_path = extracted_obj
                        mtl_path = extracted_mtl if extracted_mtl else None
                        image_path = scene.tsr_image_path
                        
                        def get_exif_orientation(filepath):
                            try:
                                from PIL import Image
                                from PIL.ExifTags import TAGS
                                img = Image.open(filepath)
                                exif = img._getexif()
                                if exif:
                                    for tag_id, value in exif.items():
                                        tag = TAGS.get(tag_id, tag_id)
                                        if tag == 'Orientation':
                                            return value
                                img.close()
                            except:
                                pass
                            return None
                        
                        def rotate_model_by_exif(obj, filepath):
                            orientation = get_exif_orientation(filepath)
                            if orientation is None:
                                return
                            
                            rotation_degrees = {
                                1: 0,
                                2: 0,
                                3: 180,
                                4: 0,
                                5: 0,
                                6: 270,
                                7: 0,
                                8: 90,
                            }.get(orientation, 0)
                            
                            if rotation_degrees:
                                bpy.ops.object.rotation_clear()
                                bpy.context.view_layer.objects.active = obj
                                bpy.ops.transform.rotate(value=rotation_degrees * 0.0174533, orient_axis='Z')
                                bpy.ops.object.location_clear()
                        
                        verts = []
                        uvs = []
                        faces = []
                        face_uvs = []
                        mtl_dir = os.path.dirname(obj_path)
                        materials = {}
                        current_mtl = None
                        
                        if mtl_path and os.path.exists(mtl_path):
                            with open(mtl_path, 'r', encoding='utf-8', errors='ignore') as f:
                                for line in f:
                                    line = line.strip()
                                    if line.startswith('newmtl '):
                                        current_mtl = line.split()[1]
                                        materials[current_mtl] = {'diffuse': None, 'map_Kd': None}
                                    elif line.startswith('Kd ') and current_mtl:
                                        parts = line.split()
                                        materials[current_mtl]['diffuse'] = (float(parts[1]), float(parts[2]), float(parts[3]), 1.0)
                                    elif line.startswith('map_Kd ') and current_mtl:
                                        tex_name = line.split()[1]
                                        tex_path = os.path.join(mtl_dir, tex_name)
                                        if os.path.exists(tex_path):
                                            materials[current_mtl]['map_Kd'] = tex_path
                        
                        with open(obj_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith('v '):
                                    parts = line.split()
                                    verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
                                elif line.startswith('vt '):
                                    parts = line.split()
                                    uvs.append((float(parts[1]), float(parts[2])))
                                elif line.startswith('f '):
                                    parts = line.split()
                                    face = []
                                    face_uv = []
                                    for part in parts[1:]:
                                        indices = part.split('/')
                                        vi = int(indices[0]) - 1
                                        vt = int(indices[1]) - 1 if len(indices) > 1 and indices[1] else 0
                                        face.append(vi)
                                        face_uv.append(vt)
                                    if len(face) == 3:
                                        faces.append(face)
                                        face_uvs.append(face_uv)
                                    elif len(face) > 3:
                                        for i in range(1, len(face) - 1):
                                            faces.append([face[0], face[i], face[i + 1]])
                                            face_uvs.append([face_uv[0], face_uv[i], face_uv[i + 1]])
                        
                        mesh = bpy.data.meshes.new('ImportedModel')
                        mesh.from_pydata(verts, [], faces)
                        mesh.update()
                        
                        if uvs and face_uvs:
                            uv_layer = mesh.uv_layers.new(name="UVMap")
                            uv_layer.active = True
                            for poly in mesh.polygons:
                                for loop_idx in poly.loop_indices:
                                    vert_idx = mesh.loops[loop_idx].vertex_index
                                    face_idx = poly.index
                                    if face_idx < len(face_uvs):
                                        for j, v in enumerate(faces[face_idx]):
                                            if v == vert_idx:
                                                uv_idx = face_uvs[face_idx][j]
                                                if uv_idx < len(uvs):
                                                    uv_layer.data[loop_idx].uv = uvs[uv_idx]
                        
                        obj = bpy.data.objects.new('ImportedModel', mesh)
                        bpy.context.collection.objects.link(obj)
                        bpy.context.view_layer.objects.active = obj
                        
                        if image_path and os.path.exists(image_path):
                            rotate_model_by_exif(obj, image_path)
                        
                        for mtl_name, mtl_data in materials.items():
                            if mtl_data.get('map_Kd'):
                                tex_path = mtl_data['map_Kd']
                                if os.path.exists(tex_path):
                                    global _last_texture_path
                                    _last_texture_path = tex_path
                                    
                                    img = bpy.data.images.load(tex_path)
                                    img.name = os.path.basename(tex_path)
                                    
                                    mat = bpy.data.materials.new(name=mtl_name)
                                    mat.use_nodes = True
                                    mat.node_tree.nodes.clear()
                                    
                                    emission_node = mat.node_tree.nodes.new('ShaderNodeEmission')
                                    emission_node.location = (0, 0)
                                    
                                    tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                                    tex_node.image = img
                                    tex_node.location = (-300, 0)
                                    
                                    mat.node_tree.links.new(tex_node.outputs['Color'], emission_node.inputs['Color'])
                                    emission_node.inputs['Strength'].default_value = 1.0
                                    
                                    output_node = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
                                    output_node.location = (300, 0)
                                    mat.node_tree.links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])
                                    
                                    obj.data.materials.append(mat)
                                    break
                        
                        self.report({'INFO'}, f"OBJ模型已导入 ({len(faces)} 个面)")
                    except Exception as e:
                        self.report({'ERROR'}, f"OBJ导入失败: {str(e)}")
                        return {'CANCELLED'}
                else:
                    bpy.ops.import_scene.gltf(filepath=output_path)
                    self.report({'INFO'}, "模型已自动导入到场景")
            except Exception as e:
                self.report({'ERROR'}, f"导入失败: {str(e)}")
                return {'CANCELLED'}
            
            return {'FINISHED'}
        
        self.report({'INFO'}, f"Generating with {model}...")
        return {'FINISHED'}


class AIAI_OT_decimate(Operator):
    bl_idname = "aiai.decimate"
    bl_label = "应用减面"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        ratio = scene.tsr_decimation_ratio
        quadify = scene.tsr_quadify
        
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, "未选择网格")
            return {'CANCELLED'}
        
        global _last_texture_path
        temp_dir = tempfile.gettempdir()
        bake_path = os.path.join(temp_dir, f"baked_texture.png")
        has_baked_texture = os.path.exists(bake_path)
        has_original_texture = _last_texture_path and os.path.exists(_last_texture_path)
        
        texture_to_use = _last_texture_path if has_original_texture else (bake_path if has_baked_texture else None)
        
        for obj in selected:
            old_materials = list(obj.data.materials)
            
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            initial_face_count = len(obj.data.polygons)
            target_face_count = int(initial_face_count * ratio)
            
            if ratio < 1:
                mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
                mod.ratio = ratio
                mod.use_symmetry = False
                mod.use_collapse_triangulate = False
                bpy.ops.object.modifier_apply(modifier="Decimate")
            
            if quadify:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.tris_convert_to_quads()
                bpy.ops.object.mode_set(mode='OBJECT')
            
            if not texture_to_use:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.uv.project_from_view(scale_bounds=True)
                bpy.ops.uv.pack_islands(angle_threshold=3.14159)
                bpy.ops.object.mode_set(mode='OBJECT')
            
            while obj.data.materials:
                obj.data.materials.pop(index=0)
            
            if texture_to_use:
                img = bpy.data.images.load(texture_to_use)
                img.name = os.path.basename(texture_to_use)
                
                mat = bpy.data.materials.new(name="DecimatedMaterial")
                mat.use_nodes = True
                mat.node_tree.nodes.clear()
                
                emission_node = mat.node_tree.nodes.new('ShaderNodeEmission')
                emission_node.location = (0, 0)
                
                tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                tex_node.image = img
                tex_node.location = (-300, 0)
                
                mat.node_tree.links.new(tex_node.outputs['Color'], emission_node.inputs['Color'])
                emission_node.inputs['Strength'].default_value = 1.0
                
                output_node = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
                output_node.location = (300, 0)
                mat.node_tree.links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])
                
                obj.data.materials.append(mat)
            else:
                for mat in old_materials:
                    if mat:
                        if mat.name in bpy.data.materials:
                            obj.data.materials.append(bpy.data.materials[mat.name])
                        else:
                            obj.data.materials.append(mat)
            
            final_face_count = len(obj.data.polygons)
            msg = f"减面完成: {initial_face_count} → {final_face_count} 面"
            if quadify:
                msg += " + 四边形化"
            if texture_to_use:
                msg += " + 纹理重映射"
            self.report({'INFO'}, msg)
        
        return {'FINISHED'}


class AIAI_OT_add_loop_cuts(Operator):
    bl_idname = "aiai.add_loop_cuts"
    bl_label = "添加循环边"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, "请先选择模型")
            return {'CANCELLED'}
        
        obj = selected[0]
        context.view_layer.objects.active = obj
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.object.modifier_add(type='SUBSURF')
        subsurf = obj.modifiers[-1]
        subsurf.levels = 1
        subsurf.render_levels = 2
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.subdivide(number_cuts=1)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.object.modifier_apply(modifier=subsurf.name)
        
        self.report({'INFO'}, "循环边已添加，拓扑已优化")
        return {'FINISHED'}


class AIAI_OT_rewrap_uv(Operator):
    bl_idname = "aiai.rewrap_uv"
    bl_label = "重新UV展开"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, "请先选择模型")
            return {'CANCELLED'}
        
        obj = selected[0]
        context.view_layer.objects.active = obj
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.05)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        self.report({'INFO'}, "UV已重新展开")
        return {'FINISHED'}


class AIAI_OT_topology_remesh(Operator):
    bl_idname = "aiai.topology_remesh"
    bl_label = "目标面数减面"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        target = scene.tsr_target_face_count
        
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, "未选择网格")
            return {'CANCELLED'}
        
        for obj in selected:
            old_materials = list(obj.data.materials)
            old_uv_layers = []
            for uv_layer in obj.data.uv_layers:
                old_uv_layers.append(uv_layer.name)
            
            current_faces = len(obj.data.polygons)
            if current_faces <= target:
                self.report({'INFO'}, f"当前面数 {current_faces} 已少于目标 {target}")
                return {'FINISHED'}
            
            ratio = target / current_faces
            
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.modifier_add(type='DECIMATE')
            decimate_mod = obj.modifiers[-1]
            decimate_mod.ratio = ratio
            decimate_mod.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=decimate_mod.name)
            
            for mat in old_materials:
                if mat and mat.name in bpy.data.materials:
                    obj.data.materials.append(mat)
            
            if old_uv_layers and obj.data.uv_layers:
                try:
                    obj.data.uv_layers[0].name = old_uv_layers[0] if old_uv_layers else "UVMap"
                except:
                    pass
            
            if scene.tsr_quadify:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.tris_convert_to_quads(uvs=True, materials=True, seam=True, sharp=True)
                bpy.ops.object.mode_set(mode='OBJECT')
        
        self.report({'INFO'}, f"减面完成: ~{target} 面")
        return {'FINISHED'}


class AIAI_OT_bake_texture(Operator):
    bl_idname = "aiai.bake_texture"
    bl_label = "保存纹理"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, "请先选择模型")
            return {'CANCELLED'}
        
        obj = selected[0]
        
        global _last_texture_path
        
        if obj.data.materials:
            for mat in obj.data.materials:
                if mat and mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image and node.image.filepath:
                            _last_texture_path = node.image.filepath
                            self.report({'INFO'}, f"纹理已保存: {_last_texture_path}")
                            return {'FINISHED'}
        
        self.report({'WARNING'}, "未找到纹理")
        return {'CANCELLED'}


class AIAI_OT_rig_generate(Operator):
    bl_idname = "aiai.rig_generate"
    bl_label = "生成骨骼"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        rig_type = scene.tsr_rig_type
        
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, "未选择网格")
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
        
        self.report({'INFO'}, f"骨骼已生成 ({rig_type})")
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
            self.report({'WARNING'}, "未选择网格")
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
        
        self.report({'INFO'}, f"动画已生成 ({anim_type}, {duration}秒)")
        return {'FINISHED'}


class AIAI_OT_send_chat(Operator):
    bl_idname = "aiai.send_chat"
    bl_label = "发送"
    bl_description = "发送对话到 LLM"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        scene = context.scene
        
        if not scene.tsr_llm_api_key:
            self.report({'ERROR'}, "请输入 API Key")
            return {'CANCELLED'}
        
        user_input = scene.tsr_llm_user_input.strip()
        if not user_input:
            self.report({'WARNING'}, "请输入需求")
            return {'CANCELLED'}
        
        self.report({'INFO'}, "正在发送请求...")
        
        try:
            from .api.llm import LLMProvider, build_messages, parse_commands
            
            llm = LLMProvider(
                provider=scene.tsr_llm_provider,
                model=scene.tsr_llm_model,
                api_key=scene.tsr_llm_api_key,
                base_url=getattr(scene, 'tsr_llm_base_url', "") or ""
            )
            
            try:
                chat_history = json.loads(scene.tsr_llm_chat_history) if scene.tsr_llm_chat_history else []
            except:
                chat_history = []
            
            messages = build_messages(user_input, chat_history)
            
            if scene.tsr_llm_provider == "opencode":
                from .api.opencode_provider import build_opencode_messages
                messages = build_opencode_messages(user_input, chat_history)
            
            result = llm.chat(messages)
            
            if not result.get("success"):
                self.report({'ERROR'}, f"请求失败: {result.get('error', '未知错误')}")
                return {'CANCELLED'}
            
            response_text = result.get("content", "")
            
            chat_history.append({"role": "user", "content": user_input})
            chat_history.append({"role": "assistant", "content": response_text[:500]})
            scene.tsr_llm_chat_history = json.dumps(chat_history, ensure_ascii=False)

            commands = parse_commands(response_text)
            if commands:
                self.report({'INFO'}, f"收到 {len(commands)} 条命令，正在执行...")
                try:
                    from .core.cli_manager import get_cli_manager
                    from .core.apply_project import apply_project
                    cli = get_cli_manager()
                    for cmd in commands:
                        result = cli.execute_command(cmd)
                        if result.get("success"):
                            self.report({'INFO'}, f"执行成功: {cmd[:50]}")
                            # Auto-sync to Blender viewport
                            try:
                                project_file = cli.project_file
                                if project_file and os.path.exists(project_file):
                                    import json
                                    with open(project_file, 'r', encoding='utf-8') as f:
                                        project = json.load(f)
                                    apply_project(project)
                            except Exception as sync_err:
                                print(f"Sync error: {sync_err}")
                        else:
                            self.report({'WARNING'}, f"命令失败: {result.get('error', cmd)[:50]}")
                except Exception as e:
                    self.report({'ERROR'}, f"执行出错: {str(e)}")
            else:
                self.report({'INFO'}, "未识别到可执行命令")

            scene.tsr_llm_user_input = ""
            self.report({'INFO'}, "对话完成")
            
        except Exception as e:
            self.report({'ERROR'}, f"处理失败: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}


class AIAI_OT_clear_chat(Operator):
    bl_idname = "aiai.clear_chat"
    bl_label = "清空对话"
    bl_description = "清空对话历史"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        scene = context.scene
        scene.tsr_llm_chat_history = "[]"
        scene.tsr_llm_user_input = ""
        self.report({'INFO'}, "对话已清空")
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
        
        row = layout.row(align=True)
        row.label(text="模式:", icon="SETTINGS")
        row.prop(scene, "tsr_selected_mode", expand=True)
        
        layout.separator()
        row = layout.row(align=True)
        row.label(text="模型:", icon="SOLO_ON")
        row.prop(scene, "tsr_selected_model", text="")
        row.separator()
        row.operator("aiai.set_credentials", text="配置", icon="SETTINGS")
        
        mode = scene.tsr_selected_mode
        if mode == "image2d" or mode == "hybrid":
            layout.separator()
            layout.label(text="图片:", icon="IMAGE_DATA")
            layout.prop(scene, "tsr_image_path", text="")
            layout.operator("aiai.select_image", text="选择图片", icon="FOLDER_REDIRECT")
        
        if mode == "text2d" or mode == "hybrid":
            layout.separator()
            layout.label(text="描述:", icon="TEXT")
            layout.prop(scene, "tsr_prompt_text", text="")
        
        layout.separator()
        layout.prop(scene, "tsr_resolution")
        layout.prop(scene, "tsr_remove_background")
        layout.prop(scene, "tsr_apply_post_process")
        
        layout.separator()
        layout.operator("aiai.generate", text="生成 3D 模型", icon="AXIS_TOP")
        
        layout.separator()
        layout.label(text="AI 对话 (CLI-Anything)", icon="TEXT")
        
        try:
            chat_history = json.loads(scene.tsr_llm_chat_history) if scene.tsr_llm_chat_history else []
        except:
            chat_history = []
        if chat_history:
            chat_box = layout.box()
            chat_box.label(text="对话记录:", icon="INFO")
            for entry in chat_history[-5:]:
                role = "用户" if entry.get("role") == "user" else "助手"
                content = entry.get("content", "")[:80]
                chat_box.label(text=f"{role}: {content}...", icon="DOT" if role == "用户" else "RADIOBUT_OFF")
        
        layout.prop(scene, "tsr_llm_user_input", text="输入需求")
        
        row = layout.row(align=True)
        row.operator("aiai.send_chat", text="发送", icon="PLAY")
        row.operator("aiai.clear_chat", text="清空", icon="X")
        
        layout.separator()
        layout.label(text="功能区", icon="WINDOW")
        layout.prop(scene, "tsr_tool_tab", expand=True)
        layout.separator()
        
        if scene.tsr_tool_tab == "decimation":
            layout.label(text="减面设置", icon="GROUP")
            layout.label(text="按比例减面，优先保留纹理", icon="INFO")
            layout.prop(scene, "tsr_decimation_ratio")
            layout.prop(scene, "tsr_decimation_preserveTopology")
            layout.separator()
            layout.label(text="纹理烘焙:", icon="TEXTURE")
            layout.prop(scene, "tsr_bake_resolution")
            layout.operator("aiai.bake_texture", text="保存当前纹理", icon="RENDER_RESULT")
            layout.separator()
            layout.operator("aiai.decimate", text="按比例减面", icon="GROUP")
        elif scene.tsr_tool_tab == "topology":
            layout.label(text="目标面数减面", icon="MESH_GRID")
            layout.label(text="按目标面数减面，可转四边面", icon="INFO")
            layout.prop(scene, "tsr_target_face_count")
            layout.prop(scene, "tsr_quadify")
            if scene.tsr_quadify:
                layout.label(text="四边面化可能带来轻微贴图变化", icon="ERROR")
            layout.separator()
            layout.operator("aiai.topology_remesh", text="目标面数减面", icon="MESH_GRID")
        elif scene.tsr_tool_tab == "rigging":
            layout.label(text="骨骼绑定", icon="BONE_DATA")
            layout.label(text="基础仅生成主干，双足/四足才会生成四肢", icon="INFO")
            layout.prop(scene, "tsr_rig_type", expand=True)
            layout.label(text="生成后自动绑定到当前模型", icon="INFO")
            layout.separator()
            layout.operator("aiai.rig_generate", text="生成骨骼并绑定", icon="BONE_DATA")
        elif scene.tsr_tool_tab == "animation":
            layout.label(text="动画生成", icon="ANIM")
            layout.prop(scene, "tsr_anim_type", expand=True)
            layout.prop(scene, "tsr_anim_duration")
            layout.separator()
            layout.operator("aiai.anim_generate", text="生成动画", icon="ANIM")


class AIAI_PT_decimation_tab(Panel):
    bl_label = "减面"
    bl_idname = "AIAI_PT_decimation_tab"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI 助手"
    bl_parent_id = "AIAI_PT_panel"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.label(text="减面设置", icon="GROUP")
        layout.prop(scene, "tsr_decimation_ratio")
        layout.prop(scene, "tsr_decimation_preserveTopology")
        layout.separator()
        layout.operator("aiai.decimate", text="应用减面", icon="GROUP")


class AIAI_PT_topology_tab(Panel):
    bl_label = "拓扑"
    bl_idname = "AIAI_PT_topology_tab"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI 助手"
    bl_parent_id = "AIAI_PT_panel"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.label(text="拓扑重构", icon="MESH_GRID")
        layout.prop(scene, "tsr_target_face_count")
        layout.prop(scene, "tsr_quadify")
        layout.separator()
        layout.operator("aiai.topology_remesh", text="重网格化", icon="MESH_GRID")
        layout.separator()
        layout.operator("aiai.add_loop_cuts", text="添加循环边优化", icon="MOD_SUBSURF")
        layout.operator("aiai.rewrap_uv", text="重新UV展开", icon="UV")


class AIAI_PT_rigging_tab(Panel):
    bl_label = "绑定"
    bl_idname = "AIAI_PT_rigging_tab"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI 助手"
    bl_parent_id = "AIAI_PT_panel"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.label(text="骨骼绑定", icon="BONE_DATA")
        layout.prop(scene, "tsr_rig_type", expand=True)
        layout.prop(scene, "tsr_auto_weights")
        layout.separator()
        layout.operator("aiai.rig_generate", text="生成骨骼", icon="BONE_DATA")


class AIAI_PT_animation_tab(Panel):
    bl_label = "动画"
    bl_idname = "AIAI_PT_animation_tab"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI 助手"
    bl_parent_id = "AIAI_PT_panel"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.label(text="动画生成", icon="ANIM")
        layout.prop(scene, "tsr_anim_type", expand=True)
        layout.prop(scene, "tsr_anim_duration")
        layout.separator()
        layout.operator("aiai.anim_generate", text="生成动画", icon="ANIM")


class AIAI_OT_set_credentials(Operator):
    bl_idname = "aiai.set_credentials"
    bl_label = "API 配置"
    bl_description = "API配置"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=350)
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.label(text="混元3D API:", icon="SOLO_ON")
        layout.prop(scene, "tsr_hunyuan_secret_id", text="Secret ID")
        layout.prop(scene, "tsr_hunyuan_secret_key", text="Secret Key")
        
        layout.separator()
        layout.label(text="CSMAI API:", icon="SOLO_ON")
        layout.prop(scene, "tsr_csma_secret_id", text="API Key")
        
        layout.separator()
        layout.label(text="MeshGPT API:", icon="SOLO_ON")
        layout.prop(scene, "tsr_meshgpt_api_key", text="API Key")
        
        layout.separator()
        layout.label(text="LumaAI API:", icon="SOLO_ON")
        layout.prop(scene, "tsr_luma_api_key", text="API Key")
        
        layout.separator()
        layout.label(text="LLM 配置:", icon="TEXT")
        layout.prop(scene, "tsr_llm_provider", text="供应商")
        layout.prop(scene, "tsr_llm_model", text="模型")
        layout.prop(scene, "tsr_llm_api_key", text="API Key")
        layout.prop(scene, "tsr_llm_base_url", text="API地址")
        
        layout.separator()
        layout.operator("aiai.save_creds", text="保存配置", icon="CHECKMARK")


class AIAI_OT_save_creds(Operator):
    bl_idname = "aiai.save_creds"
    bl_label = "保存配置"
    bl_description = "保存所有配置"
    
    def execute(self, context):
        import json
        scene = context.scene
        config_dir = os.path.join(os.path.dirname(__file__), "config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "credentials.json")
        
        creds = {
            "hunyuan_secret_id": scene.tsr_hunyuan_secret_id,
            "hunyuan_secret_key": scene.tsr_hunyuan_secret_key,
            "csma_secret_id": scene.tsr_csma_secret_id,
            "meshgpt_api_key": scene.tsr_meshgpt_api_key,
            "luma_api_key": scene.tsr_luma_api_key,
            "llm_provider": scene.tsr_llm_provider,
            "llm_model": scene.tsr_llm_model,
            "llm_api_key": scene.tsr_llm_api_key,
            "llm_base_url": scene.tsr_llm_base_url,
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(creds, f, ensure_ascii=False)
        
        self.report({'INFO'}, "配置已保存")
        return {'FINISHED'}


class AIAI_UL_credential_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=0.3)
        split.label(text=item[0])
        split.label(text="*" * 20 + item[1][-10:] if len(item[1]) > 10 else "N/A")


classes = [
    AIAI_OT_select_image,
    AIAI_OT_generate,
    AIAI_OT_decimate,
    AIAI_OT_topology_remesh,
    AIAI_OT_add_loop_cuts,
    AIAI_OT_rewrap_uv,
    AIAI_OT_bake_texture,
    AIAI_OT_rig_generate,
    AIAI_OT_anim_generate,
    AIAI_OT_send_chat,
    AIAI_OT_clear_chat,
    AIAI_OT_set_credentials,
    AIAI_OT_save_creds,
    AIAI_PT_panel,
]


def load_saved_credentials():
    import json
    config_path = os.path.join(os.path.dirname(__file__), "config", "credentials.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def register():
    saved = load_saved_credentials()
    
    bpy.types.Scene.tsr_selected_mode = bpy.props.EnumProperty(name="模式", items=AI_MODES, default="image2d")
    bpy.types.Scene.tsr_selected_model = bpy.props.EnumProperty(name="模型", items=AI_MODELS, default="triposr")
    bpy.types.Scene.tsr_image_path = StringProperty(name="图片路径", subtype='FILE_PATH', default="")
    bpy.types.Scene.tsr_prompt_text = StringProperty(name="描述", default="", maxlen=1024)
    bpy.types.Scene.tsr_resolution = IntProperty(name="分辨率", default=256, min=64, max=1024)
    bpy.types.Scene.tsr_remove_background = BoolProperty(name="移除背景", default=False)
    bpy.types.Scene.tsr_apply_post_process = BoolProperty(name="应用后期处理", default=False)
    
    bpy.types.Scene.tsr_hunyuan_secret_id = bpy.props.StringProperty(name="Secret ID", default=saved.get("hunyuan_secret_id", ""))
    bpy.types.Scene.tsr_hunyuan_secret_key = bpy.props.StringProperty(name="Secret Key", default=saved.get("hunyuan_secret_key", ""))
    bpy.types.Scene.tsr_csma_secret_id = bpy.props.StringProperty(name="CSMAI Key", default=saved.get("csma_secret_id", ""))
    bpy.types.Scene.tsr_meshgpt_api_key = bpy.props.StringProperty(name="MeshGPT Key", default=saved.get("meshgpt_api_key", ""))
    bpy.types.Scene.tsr_luma_api_key = bpy.props.StringProperty(name="LumaAI Key", default=saved.get("luma_api_key", ""))
    
    bpy.types.Scene.tsr_decimation_ratio = FloatProperty(name="减面比率", default=0.1, min=0.01, max=1.0, subtype='FACTOR')
    bpy.types.Scene.tsr_decimation_preserveTopology = BoolProperty(name="保留拓扑", default=False)
    bpy.types.Scene.tsr_target_face_count = IntProperty(name="目标面数", default=1000, min=100, max=100000)
    bpy.types.Scene.tsr_quadify = BoolProperty(name="转换为四边面", default=False)
    bpy.types.Scene.tsr_tool_tab = EnumProperty(name="功能区", items=[("decimation", "减面", ""), ("topology", "拓扑", ""), ("rigging", "绑定", ""), ("animation", "动画", "")], default="decimation")
    bpy.types.Scene.tsr_rig_type = EnumProperty(name="骨骼类型", items=[("basic", "基础", ""), ("biped", "双足", ""), ("quadruped", "四足", "")], default="biped")
    bpy.types.Scene.tsr_auto_weights = BoolProperty(name="自动权重", default=False)
    bpy.types.Scene.tsr_anim_type = EnumProperty(name="动画类型", items=[("rotation", "旋转", ""), ("scale", "缩放", ""), ("location", "位移", "")], default="rotation")
    bpy.types.Scene.tsr_anim_duration = FloatProperty(name="时长（秒）", default=2.0, min=0.1, max=60.0)
    bpy.types.Scene.tsr_bake_resolution = IntProperty(name="烘焙分辨率", default=1024, min=256, max=4096)
    
    bpy.types.Scene.tsr_llm_provider = EnumProperty(name="LLM供应商", items=LLM_PROVIDERS, default=saved.get("llm_provider", "openai"))
    bpy.types.Scene.tsr_llm_model = StringProperty(name="LLM模型", default=saved.get("llm_model", "gpt-4o"))
    bpy.types.Scene.tsr_llm_api_key = StringProperty(name="LLM API Key", default=saved.get("llm_api_key", ""))
    bpy.types.Scene.tsr_llm_base_url = StringProperty(name="API地址", default=saved.get("llm_base_url", ""))
    bpy.types.Scene.tsr_llm_user_input = StringProperty(name="对话输入", default="", maxlen=2000)
    bpy.types.Scene.tsr_llm_chat_history = StringProperty(name="对话历史", default="[]")
    
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    props = [
        'tsr_selected_mode', 'tsr_selected_model', 'tsr_image_path', 'tsr_prompt_text',
        'tsr_resolution', 'tsr_remove_background', 'tsr_apply_post_process',
        'tsr_hunyuan_secret_id', 'tsr_hunyuan_secret_key', 'tsr_csma_secret_id',
        'tsr_meshgpt_api_key', 'tsr_luma_api_key',
        'tsr_decimation_ratio', 'tsr_decimation_preserveTopology', 'tsr_target_face_count',
        'tsr_quadify', 'tsr_tool_tab', 'tsr_rig_type', 'tsr_auto_weights', 'tsr_anim_type', 'tsr_anim_duration',
        'tsr_bake_resolution',
        'tsr_llm_provider', 'tsr_llm_model', 'tsr_llm_api_key', 'tsr_llm_base_url',
        'tsr_llm_user_input', 'tsr_llm_chat_history',
    ]
    for prop in props:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)


if __name__ == "__main__":
    register()