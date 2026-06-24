"""Blender AI Assistant Plugin - CLI-Anything based 3D modeling with AI.

使用 blender_manifest.toml (Blender 4.2+ 扩展格式) — 见同名 manifest 文件
"""

# 兼容层:Blender 5.1 会扫描 scripts/addons/ 中的 bl_info 来判断 addons 元数据
# 我们的 manifest 是扩展格式,但保留 bl_info 可避免被归入 Missing Add-ons
bl_info = {
    "name": "AI Assistant for Blender",
    "author": "TripoAR Team",
    "version": (2, 6, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > AI Assistant",
    "description": "AI-powered 3D modeling assistant. Sign in with your blender-ai.com API key to start.",
    "category": "3D View",
    "website": "https://www.blender-ai.com/",
}

import bpy
import os
import re
import time
import json
import tempfile
from bpy.props import StringProperty, EnumProperty, BoolProperty, IntProperty, FloatProperty, CollectionProperty
from bpy.types import Panel, Operator, AddonPreferences

# 插件 addons 目录名,AddOnPreferences.bl_idname 必须与之一致
# 必须是合法 Python 标识符(下划线),匹配 manifest.id
_ADDON_NAME = "cli_anything_blender"


class AIAI_AddonPreferences(AddonPreferences):
    """偏好设置页面 (模仿 fal.ai 风格):
    Edit > Preferences > Extensions > AI Assistant for Blender"""
    bl_idname = _ADDON_NAME

    playground_api_key: StringProperty(
        name="API Key",
        description="Get your API key at https://www.blender-ai.com/dashboard/api-keys",
        subtype="PASSWORD",
        default="",
    )

    api_server: EnumProperty(
        name="API Server",
        description="新装用户默认 Local Dev (需要本机运行 dev-up.ps1);"
                    "生产部署后切到 Production",
        items=[
            ("local_dev", "Local Dev (http://localhost:3000)", "本机后端 (推荐给开发者和新用户)"),
            ("production", "Production (www.blender-ai.com:8443)", "官方线上服务"),
        ],
        default="local_dev",
    )

    def draw(self, context):
        """Preferences 页面:
        Blender 系统元信息(manifest 自动渲染) -> Preferences -> 我们的 box(logo + api key)
        Blender 会自动按 NAME -> TAGLINE -> TYPE -> MAINTAINER -> VERSION -> FILE -> WEBSITE 顺序显示
        """
        layout = self.layout
        # 单一大 box 包住 LOGO + API Key + 警告 (模仿 fal.ai 截图布局)
        main_box = layout.box()
        # LOGO 上下空间距离缩小 4/5 (保留 1/5):前后各加 factor=0.2 的小间隔
        main_box.separator(factor=0.2)
        # LOGO 居中显示 (scale=8.0)
        _branding.draw_header(main_box, scale=8.0)
        main_box.separator(factor=0.2)
        # API Key 标签 + 输入框
        main_box.label(text="API Key:")
        main_box.prop(self, "playground_api_key", text="")
        main_box.separator()
        # API Server 选择器
        main_box.label(text="API Server:")
        main_box.prop(self, "api_server", expand=True)
        from .core import billing as _billing_draw
        _server_url = _billing_draw.get_base_url()
        main_box.label(text=f"→ {_server_url}", icon="URL")
        main_box.separator()
        # 测试 / 登录按钮 (就地验证 KEY 并刷新账户)
        if self.playground_api_key:
            row = main_box.row(align=True)
            row.operator("aiai.sign_in", text=i18n._("测试 & 登录"), icon="PLAY")
            row.operator("aiai.open_billing",
                         text=i18n._("账户 & 充值"), icon="FUND")
        # 已缓存的账户信息 (登录后显示)
        cached = _billing.get_cached_account()
        if cached:
            info_box = main_box.box()
            sym = "$" if cached.currency.upper() == "USD" else cached.currency + " "
            info_box.label(
                text=i18n._("账户: %s") % cached.display_name, icon="USER")
            info_box.label(
                text=i18n._("余额: %s%.2f (%s)") % (sym, cached.balance, cached.plan),
                icon="FUND")
        # 警告 (仅在未填 Key 时显示,模仿截图)
        if not self.playground_api_key:
            warn = main_box.box()
            warn.label(text=i18n._("No API key set!"), icon="ERROR")
            warn.label(text=i18n._("Set above, or visit blender-ai.com to get one"))
        # Get a key 按钮 (模仿 fal.ai 截图底部整行按钮)
        op2 = layout.operator(
            "wm.url_open",
            text=i18n._("Get a key at blender-ai"),
        )
        op2.url = "https://www.blender-ai.com/dashboard/api-keys"

# Always use development directory for core modules
from .api import (
    PlaygroundAPI,
    APIStatus,
    APIResponse,
    AccountInfo,
    BillingError,
    InvalidKeyError,
    InsufficientBalanceError,
    format_billing_error,
    check_for_update,
)
from .core import billing as _billing
from . import i18n
from . import branding as _branding

_last_texture_path = ""

# ============================================================
# 版本检查 — 启动时后台线程检测, 有新版本时在面板顶部显示提醒
# ============================================================
_update_info = None  # None = 未检测或已最新; dict = 有新版本可用


def _start_update_check():
    """在后台线程中检查插件版本更新 (非阻塞, 超时 5s)."""
    import threading

    def _worker():
        global _update_info
        try:
            base_url = _billing.get_base_url()
            result = check_for_update(base_url)
            _update_info = result
        except Exception:
            _update_info = None

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def _fix_imported_orientation():
    """Rotate newly-imported AI models so the longest axis is vertical (Z-up),
    and shift them so the lowest point sits at Z=0 (sitting on the ground).

    Works regardless of whether the source model is Y-up, Z-up, or arbitrary:
    just computes the world-axis-aligned bounding box of the most recently
    selected objects and re-orients them by mapping the longest box edge to +Z.
    """
    import math
    import bpy
    import mathutils

    objs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not objs:
        return

    # Combine all imported meshes' world-space corners.
    all_min = mathutils.Vector((float('inf'),) * 3)
    all_max = mathutils.Vector((float('-inf'),) * 3)
    for o in objs:
        for corner in o.bound_box:
            wc = o.matrix_world @ mathutils.Vector(corner)
            for i in range(3):
                if wc[i] < all_min[i]:
                    all_min[i] = wc[i]
                if wc[i] > all_max[i]:
                    all_max[i] = wc[i]

    size = all_max - all_min
    # Pick the longest world axis to be "up" (most AI-generated characters
    # and objects are taller than they are wide or deep).
    longest_axis = max(range(3), key=lambda i: size[i])
    # Rotation that maps the chosen axis to +Z. Use a 90° rotation around
    # the other axis when needed.
    if longest_axis == 0:  # +X longest → rotate -90° around Y
        rot = mathutils.Euler((0, 0, math.radians(-90)), 'XYZ')
    elif longest_axis == 1:  # +Y longest → rotate +90° around X
        rot = mathutils.Euler((math.radians(90), 0, 0), 'XYZ')
    else:  # +Z longest → no rotation
        rot = mathutils.Euler((0, 0, 0), 'XYZ')

    if abs(rot.x) + abs(rot.y) + abs(rot.z) > 1e-6:
        for o in objs:
            o.rotation_euler = rot
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    # Recompute bbox and shift so the lowest point sits at Z=0.
    all_min = mathutils.Vector((float('inf'),) * 3)
    for o in objs:
        for corner in o.bound_box:
            wc = o.matrix_world @ mathutils.Vector(corner)
            if wc.z < all_min.z:
                all_min.z = wc.z
    if all_min.z < 0 or all_min.z > 0:
        for o in objs:
            o.location.z -= all_min.z


AI_MODELS = [
    ("hunyuan3d", "混元3D", "Tencent cloud API"),
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
    ("opencode", "OpenCode", "Creative multi-round AI"),
    ("ollama", "Ollama", "Local model"),
]


# 任务记录 (Active Jobs 面板) — 每个生成任务的元数据
class AIAI_PG_job_record(bpy.types.PropertyGroup):
    job_id: StringProperty(name="Job ID", default="")
    start_time: FloatProperty(name="Start Time", default=0.0, description="Epoch seconds")
    end_time: FloatProperty(name="End Time", default=0.0, description="0 = still running")
    status: EnumProperty(name="Status", items=[
        ("WAIT", "Waiting", "等待中"),
        ("RUN", "Running", "生成中"),
        ("DONE", "Done", "完成"),
        ("FAIL", "Failed", "失败"),
    ], default="WAIT")
    prompt_preview: StringProperty(name="Prompt", default="")
    face_count: IntProperty(name="Face Count", default=0)
    elapsed_text: StringProperty(name="Elapsed", default="-")
    error_msg: StringProperty(name="Error", default="")


class AIAI_OT_select_image(Operator):
    bl_idname = "aiai.select_image"
    bl_label = i18n._("选择图片")
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
    bl_label = i18n._("生成 3D 模型")
    bl_options = {'REGISTER', 'UNDO'}

    @_billing.require_key
    def execute(self, context):
        scene = context.scene
        model = scene.tsr_selected_model
        mode = scene.tsr_selected_mode

        # === Active Jobs 记录: 创建任务条目 (任何 model 通用) ===
        import time as _time
        _job_start = _time.time()
        _job = scene.tsr_active_jobs.add()
        _job.job_id = ""
        _job.start_time = _job_start
        _job.end_time = 0.0
        _job.status = "RUN"
        _job.prompt_preview = (scene.tsr_prompt_text or scene.tsr_image_path or "-")[:30]
        _job.face_count = scene.tsr_face_count
        _job.elapsed_text = "..."
        _job.error_msg = ""
        # 上限 10 条,超出丢弃最早
        _MAX_JOBS = 10
        while len(scene.tsr_active_jobs) > _MAX_JOBS:
            scene.tsr_active_jobs.remove(0)

        def _finalize_job(status, error_msg=""):
            """在每个退出点调用,更新任务状态"""
            _job.end_time = _time.time()
            _job.status = status
            _job.error_msg = error_msg or ""
            _secs = int(_job.end_time - _job.start_time)
            _m, _s = divmod(_secs, 60)
            _job.elapsed_text = f"{_m:02d}:{_s:02d}"

        if (mode == "image2d" and not scene.tsr_image_path):
            _finalize_job("FAIL", "缺少图片")
            self.report({'ERROR'}, i18n._("请选择图片"))
            return {'CANCELLED'}

        self.report({'INFO'}, i18n._("正在提交 3D 生成任务..."))

        # === 调 blender-ai.com 代理 ===
        try:
            api = _billing.get_api()
            response = api.submit_model(
                model=model or "hunyuan3d",
                prompt=scene.tsr_prompt_text or "",
                image_path=scene.tsr_image_path or "",
                face_count=scene.tsr_face_count,
                mode=mode,
            )
        except InvalidKeyError as e:
            _finalize_job("FAIL", "KEY 无效")
            _billing.reset_account_cache()
            _billing.report_billing_error(self, e)
            return {'CANCELLED'}
        except InsufficientBalanceError as e:
            _finalize_job("FAIL", "余额不足")
            _billing.report_billing_error(self, e)
            return {'CANCELLED'}
        except BillingError as e:
            _finalize_job("FAIL", str(e))
            _billing.report_billing_error(self, e)
            return {'CANCELLED'}

        if not response.success:
            _finalize_job("FAIL", response.error or "提交失败")
            self.report({'ERROR'}, i18n._("提交失败: %s") % (response.error or "未知错误"))
            return {'CANCELLED'}

        job_id = response.job_id
        _job.job_id = job_id or ""
        charged = (response.data or {}).get("charged")
        if charged is not None:
            self.report({'INFO'},
                        i18n._("任务已提交 (扣费 $%.2f),等待处理...") % float(charged))
        else:
            self.report({'INFO'}, i18n._("任务已提交 JobId=%s,等待处理...") % job_id)

        # 提交成功后主动刷新一次账户余额(后台)
        try:
            _billing.set_cached_account(api.get_account_info())
        except BillingError:
            pass  # 余额刷新失败不阻塞主流程

        try:
            result = api.wait_for_model(job_id, timeout=600, poll_interval=5)
        except BillingError as e:
            _finalize_job("FAIL", f"wait exception: {e}")
            _billing.report_billing_error(self, e)
            return {'CANCELLED'}

        if not result.success:
            _finalize_job("FAIL", result.error or "任务失败")
            self.report({'ERROR'}, i18n._("任务失败: %s") % (result.error or "未知错误"))
            return {'CANCELLED'}

        self.report({'INFO'}, i18n._("正在下载模型..."))

        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"aiai_{job_id}.glb")
        zip_path = os.path.join(temp_dir, f"aiai_{job_id}.zip")

        download_result = api.download_model(job_id, zip_path)

        if not download_result.success:
            _finalize_job("FAIL", download_result.error or "下载失败")
            self.report({'ERROR'}, i18n._("下载失败: %s") % (download_result.error or "未知错误"))
            return {'CANCELLED'}

        self.report({'INFO'}, i18n._("模型已下载,正在处理..."))

        try:
            import zipfile

            extracted_glb = None
            extracted_obj = None
            extracted_mtl = None

            if zipfile.is_zipfile(zip_path):
                with zipfile.ZipFile(zip_path, 'r') as z:
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
                    self.report({'INFO'}, i18n._("文件已解压(GLB): %s") % output_path)
                elif extracted_obj:
                    output_path = extracted_obj
                    self.report({'INFO'}, i18n._("文件已解压(OBJ): %s") % output_path)
                else:
                    output_path = zip_path
            else:
                output_path = zip_path

            if not os.path.exists(output_path):
                _finalize_job("FAIL", f"文件不存在: {output_path}")
                self.report({'ERROR'}, i18n._("文件不存在: %s") % output_path)
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
                        except Exception:
                            pass
                        return None

                    def rotate_model_by_exif(obj, filepath):
                        import math
                        orientation = get_exif_orientation(filepath)
                        if orientation is None:
                            return

                        rotation_degrees = {
                            1: 0, 2: 0, 3: 180, 4: 0,
                            5: 0, 6: 270, 7: 0, 8: 90,
                        }.get(orientation, 0)

                        if rotation_degrees:
                            obj.rotation_euler[2] = math.radians(rotation_degrees)
                            bpy.context.view_layer.objects.active = obj
                            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

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
                                verts.append((float(parts[1]), -float(parts[3]), float(parts[2])))
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

                    self.report({'INFO'}, i18n._("OBJ模型已导入 (%s 个面)") % len(faces))
                except Exception as e:
                    self.report({'ERROR'}, i18n._("OBJ导入失败: %s") % str(e))
                    return {'CANCELLED'}
            else:
                bpy.ops.import_scene.gltf(filepath=output_path, axis_forward='-Z', axis_up='Y')
                self.report({'INFO'}, i18n._("模型已自动导入到场景"))
                _fix_imported_orientation()
        except Exception as e:
            _finalize_job("FAIL", f"导入失败: {e}")
            self.report({'ERROR'}, i18n._("导入失败: %s") % str(e))
            return {'CANCELLED'}

        _finalize_job("DONE")
        return {'FINISHED'}


class AIAI_OT_decimate(Operator):
    bl_idname = "aiai.decimate"
    bl_label = i18n._("应用减面")
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        ratio = scene.tsr_decimation_ratio
        quadify = scene.tsr_quadify
        
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, i18n._("未选择网格"))
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
            msg = i18n._("减面完成: %s → %s 面") % (initial_face_count, final_face_count)
            if quadify:
                msg += " + " + i18n._("四边形化")
            if texture_to_use:
                msg += " + " + i18n._("纹理重映射")
            self.report({'INFO'}, msg)
        
        return {'FINISHED'}


class AIAI_OT_add_loop_cuts(Operator):
    bl_idname = "aiai.add_loop_cuts"
    bl_label = i18n._("添加循环边")
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, i18n._("请先选择模型"))
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
        
        self.report({'INFO'}, i18n._("循环边已添加，拓扑已优化"))
        return {'FINISHED'}


class AIAI_OT_rewrap_uv(Operator):
    bl_idname = "aiai.rewrap_uv"
    bl_label = i18n._("重新UV展开")
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, i18n._("请先选择模型"))
            return {'CANCELLED'}
        
        obj = selected[0]
        context.view_layer.objects.active = obj
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.05)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        self.report({'INFO'}, i18n._("UV已重新展开"))
        return {'FINISHED'}


class AIAI_OT_topology_remesh(Operator):
    bl_idname = "aiai.topology_remesh"
    bl_label = i18n._("目标面数减面")
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        target = scene.tsr_target_face_count
        
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, i18n._("未选择网格"))
            return {'CANCELLED'}
        
        for obj in selected:
            old_materials = list(obj.data.materials)
            old_uv_layers = []
            for uv_layer in obj.data.uv_layers:
                old_uv_layers.append(uv_layer.name)
            
            current_faces = len(obj.data.polygons)
            if current_faces <= target:
                self.report({'INFO'}, i18n._("当前面数 %s 已少于目标 %s") % (current_faces, target))
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
        
        self.report({'INFO'}, i18n._("减面完成: ~%s 面") % target)
        return {'FINISHED'}


class AIAI_OT_bake_texture(Operator):
    bl_idname = "aiai.bake_texture"
    bl_label = i18n._("保存纹理")
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, i18n._("请先选择模型"))
            return {'CANCELLED'}
        
        obj = selected[0]
        
        global _last_texture_path
        
        if obj.data.materials:
            for mat in obj.data.materials:
                if mat and mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image and node.image.filepath:
                            _last_texture_path = node.image.filepath
                            self.report({'INFO'}, i18n._("纹理已保存: %s") % _last_texture_path)
                            return {'FINISHED'}
        
        self.report({'WARNING'}, i18n._("未找到纹理"))
        return {'CANCELLED'}


class AIAI_OT_rig_generate(Operator):
    bl_idname = "aiai.rig_generate"
    bl_label = i18n._("生成骨骼")
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        rig_type = scene.tsr_rig_type
        
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, i18n._("未选择网格"))
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
        
        self.report({'INFO'}, i18n._("骨骼已生成 (%s)") % rig_type)
        return {'FINISHED'}


class AIAI_OT_anim_generate(Operator):
    bl_idname = "aiai.anim_generate"
    bl_label = i18n._("生成动画")
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        anim_type = scene.tsr_anim_type
        duration = scene.tsr_anim_duration
        
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, i18n._("未选择网格"))
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
        
        self.report({'INFO'}, i18n._("动画已生成 (%s, %s秒)") % (anim_type, duration))
        return {'FINISHED'}


class AIAI_OT_send_chat(Operator):
    bl_idname = "aiai.send_chat"
    bl_label = i18n._("发送")
    bl_description = i18n._("发送对话到 LLM (由 blender-ai.com 代理)")
    bl_options = {'REGISTER'}

    @_billing.require_key
    def execute(self, context):
        scene = context.scene

        user_input = (scene.tsr_llm_user_input or "").strip()
        if not user_input:
            self.report({'WARNING'}, i18n._("请输入需求"))
            return {'CANCELLED'}

        self.report({'INFO'}, i18n._("正在发送请求..."))

        try:
            from .api.llm import build_messages, parse_commands

            try:
                chat_history = json.loads(scene.tsr_llm_chat_history) if scene.tsr_llm_chat_history else []
            except Exception:
                chat_history = []

            messages = build_messages(user_input, chat_history)

            api = _billing.get_api()
            result = api.chat(messages=messages, model="auto", timeout=600)

            if not result.get("success"):
                self.report({'ERROR'},
                            i18n._("请求失败: %s") % (result.get("error") or i18n._("未知错误")))
                return {'CANCELLED'}

            response_text = result.get("content", "")

            chat_history.append({"role": "user", "content": user_input})
            chat_history.append({"role": "assistant", "content": (response_text or "")[:500]})
            scene.tsr_llm_chat_history = json.dumps(chat_history, ensure_ascii=False)

            commands = parse_commands(response_text)
            if commands:
                self.report({'INFO'}, i18n._("收到 %s 条命令,正在执行...") % len(commands))
                try:
                    from .core.cli_manager import get_cli_manager
                    from .core.apply_project import apply_project
                    cli = get_cli_manager()
                    for cmd in commands:
                        result = cli.execute_command(cmd)
                        if result.get("success"):
                            self.report({'INFO'}, i18n._("执行成功: %s") % cmd[:50])
                            try:
                                project_file = cli.project_file
                                if project_file and os.path.exists(project_file):
                                    with open(project_file, 'r', encoding='utf-8') as f:
                                        project = json.load(f)
                                    apply_project(project)
                            except Exception as sync_err:
                                print(f"Sync error: {sync_err}")
                        else:
                            self.report({'WARNING'},
                                        i18n._("命令失败: %s") % result.get('error', cmd)[:50])
                except Exception as e:
                    self.report({'ERROR'}, i18n._("执行出错: %s") % str(e))
            else:
                self.report({'INFO'}, i18n._("未识别到可执行命令"))

            # 刷新余额(显示扣费后余额)
            try:
                _billing.set_cached_account(api.get_account_info())
            except BillingError:
                pass

            scene.tsr_llm_user_input = ""
            self.report({'INFO'}, i18n._("对话完成"))

        except InvalidKeyError as e:
            _billing.reset_account_cache()
            _billing.report_billing_error(self, e)
            return {'CANCELLED'}
        except InsufficientBalanceError as e:
            _billing.report_billing_error(self, e)
            return {'CANCELLED'}
        except BillingError as e:
            _billing.report_billing_error(self, e)
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, i18n._("处理失败: %s") % str(e))
            return {'CANCELLED'}

        return {'FINISHED'}


class AIAI_OT_clear_chat(Operator):
    bl_idname = "aiai.clear_chat"
    bl_label = i18n._("清空对话")
    bl_description = i18n._("清空对话历史")
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        scene.tsr_llm_chat_history = "[]"
        scene.tsr_llm_user_input = ""
        self.report({'INFO'}, i18n._("对话已清空"))
        return {'FINISHED'}


class AIAI_OT_copy_chat(Operator):
    bl_idname = "aiai.copy_chat"
    bl_label = i18n._("复制对话")
    bl_description = i18n._("复制对话历史到剪贴板")
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        try:
            chat_history = json.loads(scene.tsr_llm_chat_history) if scene.tsr_llm_chat_history else []
        except:
            chat_history = []
        
        if not chat_history:
            self.report({'INFO'}, i18n._("无对话记录"))
            return {'FINISHED'}
        
        text_lines = []
        for entry in chat_history:
            role = i18n._("用户") if entry.get("role") == "user" else i18n._("助手")
            content = entry.get("content", "")
            text_lines.append(f"{role}: {content}")
        
        text = "\n".join(text_lines)
        
        try:
            bpy.context.window_manager.clipboard = text
            self.report({'INFO'}, i18n._("对话已复制"))
        except Exception as e:
            self.report({'ERROR'}, i18n._("复制失败: %s") % str(e))
        return {'FINISHED'}


class AIAI_OT_toggle_features(Operator):
    bl_idname = "aiai.toggle_features"
    bl_label = i18n._("切换功能区")
    bl_description = i18n._("展开或折叠功能区")
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.tsr_features_expanded = not context.scene.tsr_features_expanded
        return {'FINISHED'}


class AIAI_OT_open_playground(Operator):
    bl_idname = "aiai.open_playground"
    bl_label = i18n._("打开游乐场")
    bl_description = i18n._("在浏览器中打开游乐场,查看/管理你的模型")
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            bpy.ops.wm.url_open(url="https://www.blender-ai.com/dashboard/models")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, i18n._("无法打开链接: %s") % str(e))
            return {'CANCELLED'}


class AIAI_OT_open_download(Operator):
    """在浏览器中打开插件下载页面."""
    bl_idname = "aiai.open_download"
    bl_label = i18n._("下载新版本")
    bl_description = i18n._("打开 blender-ai.com 下载页面获取最新版本")
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            bpy.ops.wm.url_open(url="https://www.blender-ai.com/download")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, i18n._("无法打开链接: %s") % str(e))
            return {'CANCELLED'}


class AIAI_OT_clear_jobs(Operator):
    bl_idname = "aiai.clear_jobs"
    bl_label = i18n._("清空任务记录")
    bl_description = i18n._("清空所有生成任务历史")
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.tsr_active_jobs.clear()
        self.report({'INFO'}, i18n._("任务记录已清空"))
        return {'FINISHED'}


# ============================================================
# 鉴权 / 账户 Operators (v2.6.0+ KEY 登录模式)
# ============================================================
class AIAI_OT_sign_in(Operator):
    """用 AddonPreferences 中的 KEY 登录,验证并拉取账户信息."""
    bl_idname = "aiai.sign_in"
    bl_label = i18n._("登录")
    bl_description = i18n._("验证 API Key 并加载账户余额")
    bl_options = {'REGISTER'}

    def execute(self, context):
        if not _billing.has_key():
            self.report({'ERROR'},
                        i18n._("请先在偏好设置 (Edit > Preferences > Extensions) "
                               "> AI Assistant 中填写 API Key"))
            try:
                bpy.ops.preferences.addon_show(module=_ADDON_NAME)
            except Exception:
                pass
            return {'CANCELLED'}

        try:
            info = _billing.get_api().validate_key()
        except InvalidKeyError as e:
            _billing.reset_account_cache()
            _billing.report_billing_error(self, e)
            return {'CANCELLED'}
        except BillingError as e:
            _billing.report_billing_error(self, e)
            return {'CANCELLED'}

        _billing.set_cached_account(info)
        self.report({'INFO'},
                    i18n._("登录成功: %s (余额 $%.2f)") % (info.display_name, info.balance))
        return {'FINISHED'}


class AIAI_OT_sign_out(Operator):
    """退出登录:清空 KEY 缓存与账户信息 (不删除偏好中的 KEY,用户可一键重新登录)."""
    bl_idname = "aiai.sign_out"
    bl_label = i18n._("退出")
    bl_description = i18n._("退出登录并清空账户缓存")
    bl_options = {'REGISTER'}

    def execute(self, context):
        _billing.reset_account_cache()
        self.report({'INFO'}, i18n._("已退出登录"))
        return {'FINISHED'}


class AIAI_OT_refresh_account(Operator):
    """重新拉取余额/套餐信息."""
    bl_idname = "aiai.refresh_account"
    bl_label = i18n._("刷新")
    bl_description = i18n._("从 blender-ai.com 重新拉取账户信息")
    bl_options = {'REGISTER'}

    def execute(self, context):
        if not _billing.has_key():
            self.report({'ERROR'}, i18n._("请先填写 API Key"))
            return {'CANCELLED'}
        try:
            info = _billing.get_api().get_account_info()
        except InvalidKeyError as e:
            _billing.reset_account_cache()
            _billing.report_billing_error(self, e)
            return {'CANCELLED'}
        except BillingError as e:
            _billing.report_billing_error(self, e)
            return {'CANCELLED'}
        _billing.set_cached_account(info)
        self.report({'INFO'},
                    i18n._("余额已刷新: $%.2f") % info.balance)
        return {'FINISHED'}


class AIAI_OT_open_billing(Operator):
    """打开账户/充值页面."""
    bl_idname = "aiai.open_billing"
    bl_label = i18n._("充值")
    bl_description = i18n._("在浏览器中打开账户/充值页面")
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            bpy.ops.wm.url_open(
                url="https://www.blender-ai.com/dashboard/settings?section=account")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, i18n._("无法打开链接: %s") % str(e))
            return {'CANCELLED'}


class AIAI_OT_open_get_key(Operator):
    """打开获取 KEY 页面."""
    bl_idname = "aiai.open_get_key"
    bl_label = i18n._("获取 Key")
    bl_description = i18n._("在浏览器中打开获取 API Key 页面")
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            bpy.ops.wm.url_open(url="https://www.blender-ai.com/dashboard/api-keys")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, i18n._("无法打开链接: %s") % str(e))
            return {'CANCELLED'}


class AIAI_OT_open_preferences(Operator):
    """在偏好设置中显示本插件页面 (用于填 KEY)."""
    bl_idname = "aiai.open_preferences"
    bl_label = i18n._("设置")
    bl_description = i18n._("打开插件偏好设置 (填 API Key)")
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            bpy.ops.preferences.addon_show(module=_ADDON_NAME)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, i18n._("无法打开偏好设置: %s") % str(e))
            return {'CANCELLED'}


class AIAI_PT_panel(Panel):
    bl_label = i18n._("AI 助手")
    bl_idname = "AIAI_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = i18n._("AI 助手")

    def draw(self, context):
        self.bl_label = i18n._("AI 助手")
        layout = self.layout
        scene = context.scene

        # ============================================================
        # 0) 版本更新提醒 (面板顶部, 仅在检测到新版本时显示)
        # ============================================================
        global _update_info
        if _update_info:
            new_ver = _update_info.get("version", "?")
            update_box = layout.box()
            update_box.alert = True
            update_box.label(
                text=i18n._("新版本 %s 可用") % new_ver,
                icon="ERROR",
            )
            update_box.operator(
                "aiai.open_download",
                text=i18n._("前往下载页面"),
                icon="URL",
            )

        # ============================================================
        # 1) 账户状态卡 (顶部)
        # ============================================================
        self._draw_account_box(layout)

        # ============================================================
        # 2) 模型生成区 (无 KEY 时按钮会自动置灰,因为 operator 装饰器会取消)
        # ============================================================
        row = layout.row(align=True)
        row.label(text=i18n._("模式") + ":", icon="SETTINGS")
        row.prop(scene, "tsr_selected_mode", expand=True)

        layout.separator()
        row = layout.row(align=True)
        row.label(text=i18n._("模型") + ":", icon="SOLO_ON")
        row.prop(scene, "tsr_selected_model", text="")

        mode = scene.tsr_selected_mode
        if mode == "image2d" or mode == "hybrid":
            layout.separator()
            layout.label(text=i18n._("图片") + ":", icon="IMAGE_DATA")
            layout.prop(scene, "tsr_image_path", text="")
            layout.operator("aiai.select_image", text=i18n._("选择图片"), icon="FOLDER_REDIRECT")

        if mode == "text2d" or mode == "hybrid":
            layout.separator()
            layout.label(text=i18n._("描述") + ":", icon="TEXT")
            layout.prop(scene, "tsr_prompt_text", text="")

        layout.separator()
        layout.prop(scene, "tsr_face_count")

        # 游乐场信息卡片 (设计稿 A: box 卡片 + 2 行说明 + 整行大按钮)
        _pg_box = layout.box()
        _pg_box.label(text=i18n._("所选模型生成逼真且直接使用的3D模型"), icon="INFO")
        _pg_box.label(text=i18n._("每次生成费用为0.8美元"), icon="INFO")
        _pg_box.separator()
        _pg_box.operator(
            "aiai.open_playground",
            text=i18n._("打开游乐场"),
            icon="URL",
        )

        # Active Jobs 面板 (始终展开,不折叠)
        _jobs_box = layout.box()
        _jobs_box.label(text=i18n._("Active Jobs"), icon="TIME")
        _jobs_count = len(scene.tsr_active_jobs)
        if _jobs_count == 0:
            _jobs_box.label(text=i18n._("No active jobs"), icon="INFO")
        else:
            _status_icons = {
                "WAIT": "TIME",
                "RUN": "SORTTIME",
                "DONE": "CHECKMARK",
                "FAIL": "ERROR",
            }
            _status_names = {
                "WAIT": i18n._("等待中"),
                "RUN": i18n._("生成中"),
                "DONE": i18n._("完成"),
                "FAIL": i18n._("失败"),
            }
            for _j in scene.tsr_active_jobs:
                _jid_short = (_j.job_id[-6:] if _j.job_id else "-")
                _row1 = _jobs_box.row(align=True)
                _row1.label(
                    text=f"#{_jid_short}  {_j.prompt_preview}",
                    icon=_status_icons.get(_j.status, "DOT"),
                )
                _row1.label(text=_j.elapsed_text)
                _row2 = _jobs_box.row(align=True)
                _face_str = f"{_j.face_count:,}" if _j.face_count else "-"
                _row2.label(text=f"   {_face_str} faces | {_status_names.get(_j.status, _j.status)}")
                if _j.status == "FAIL" and _j.error_msg:
                    _jobs_box.label(text=f"   {_j.error_msg}", icon="ERROR")
        if _jobs_count > 0:
            _jobs_box.separator()
            _jobs_box.operator("aiai.clear_jobs", text=i18n._("清空记录"), icon="TRASH")

        layout.separator()
        layout.operator("aiai.generate", text=i18n._("生成 3D 模型"), icon="AXIS_TOP")
        
        layout.separator()
        # 面板标题：去掉括号及其内容 (例如 "AI 对话 (CLI-Anything)" -> "AI 对话")
        _chat_panel_title = re.sub(r"\s*\(.*?\)\s*", "", i18n._("AI 对话 (CLI-Anything)")).strip()
        # Blender 5.1 中 'CHAT' 图标已移除，使用 'CONSOLE' (终端) 替代
        layout.label(text=_chat_panel_title, icon="CONSOLE")
        
        try:
            chat_history = json.loads(scene.tsr_llm_chat_history) if scene.tsr_llm_chat_history else []
        except:
            chat_history = []
        if chat_history:
            chat_box = layout.box()
            chat_box.label(text=i18n._("对话记录") + ":", icon="INFO")
            for entry in chat_history[-5:]:
                role = i18n._("用户") if entry.get("role") == "user" else i18n._("助手")
                content = entry.get("content", "")
                chat_box.label(text=f"{role}: {content[:40]}..." if len(content) > 40 else f"{role}: {content}", icon="DOT" if role == i18n._("用户") else "RADIOBUT_OFF")
        
        # 输入框：Blender 5.1 不支持 subtype='MULTI_LINE'，所以使用单行 StringProperty
        # 但通过 column().scale_y(2.0) + scale_x 横向撑开 让输入框视觉上更大
        input_col = layout.column(align=True)
        input_col.scale_y = 2.0
        input_col.label(
            text=i18n._("输入需求") + ":  " + i18n._("在此输入您要发送给 AI 的需求 (例如：'创建一个低多边形风格的山地')"),
            icon="TEXT",
        )
        input_col.prop(scene, "tsr_llm_user_input", text="")
        
        row = layout.row(align=True)
        row.operator("aiai.send_chat", text=i18n._("发送"), icon="PLAY")
        row.operator("aiai.clear_chat", text=i18n._("清空"), icon="X")
        row.operator("aiai.copy_chat", text=i18n._("复制"), icon="COPYDOWN")
        
        layout.separator()
        # 功能区：可点击折叠/展开 (整行可点击,左侧三角图标指示状态)
        _feat_expanded = scene.tsr_features_expanded
        _feat_row = layout.row(align=True)
        _feat_row.operator(
            "aiai.toggle_features",
            text=i18n._("功能区"),
            icon="TRIA_DOWN" if _feat_expanded else "TRIA_RIGHT",
            emboss=False,
        )
        if _feat_expanded:
            layout.prop(scene, "tsr_tool_tab", expand=True)
            layout.separator()

            if scene.tsr_tool_tab == "decimation":
                layout.label(text=i18n._("减面设置"), icon="GROUP")
                layout.label(text=i18n._("按比例减面，优先保留纹理"), icon="INFO")
                layout.prop(scene, "tsr_decimation_ratio")
                layout.prop(scene, "tsr_decimation_preserveTopology")
                layout.separator()
                layout.label(text=i18n._("纹理烘焙") + ":", icon="TEXTURE")
                layout.prop(scene, "tsr_bake_resolution")
                layout.operator("aiai.bake_texture", text=i18n._("保存当前纹理"), icon="RENDER_RESULT")
                layout.separator()
                layout.operator("aiai.decimate", text=i18n._("按比例减面"), icon="GROUP")
            elif scene.tsr_tool_tab == "topology":
                layout.label(text=i18n._("目标面数减面"), icon="MESH_GRID")
                layout.label(text=i18n._("按目标面数减面，可转四边面"), icon="INFO")
                layout.prop(scene, "tsr_target_face_count")
                layout.prop(scene, "tsr_quadify")
                if scene.tsr_quadify:
                    layout.label(text=i18n._("四边面化可能带来轻微贴图变化"), icon="ERROR")
                layout.separator()
                layout.operator("aiai.topology_remesh", text=i18n._("目标面数减面"), icon="MESH_GRID")
            elif scene.tsr_tool_tab == "rigging":
                layout.label(text=i18n._("骨骼绑定"), icon="BONE_DATA")
                layout.label(text=i18n._("基础仅生成主干，双足/四足才会生成四肢"), icon="INFO")
                layout.prop(scene, "tsr_rig_type", expand=True)
                layout.label(text=i18n._("生成后自动绑定到当前模型"), icon="INFO")
                layout.separator()
                layout.operator("aiai.rig_generate", text=i18n._("生成骨骼并绑定"), icon="BONE_DATA")
            elif scene.tsr_tool_tab == "animation":
                layout.label(text=i18n._("动画生成"), icon="ANIM")
                layout.prop(scene, "tsr_anim_type", expand=True)
                layout.prop(scene, "tsr_anim_duration")
                layout.separator()
                layout.operator("aiai.anim_generate", text=i18n._("生成动画"), icon="ANIM")

    # ----------------------------------------------------------------
    # 账户状态卡 (v2.6.0+ KEY 登录模式)
    # ----------------------------------------------------------------
    def _draw_account_box(self, layout):
        """顶部账户状态卡,根据 KEY/缓存状态展示不同 UI."""
        box = layout.box()

        # 未填 KEY 时不再展示提示卡 (v2.6.x UI 简化)
        info = _billing.get_cached_account()

        if info is None:
            # --- 有 KEY 但未验证过:UI 不再显示等待验证卡 (v2.6.x UI 简化) ---
            return

        if not info.is_active:
            # --- 账户被停用 ---
            box.label(text=i18n._("账户已停用"), icon="CANCEL")
            box.label(text=info.display_name, icon="USER")
            box.operator("aiai.open_billing",
                         text=i18n._("联系客服"), icon="URL")
            return

        # --- 正常登录状态 ---
        sym = "$" if info.currency.upper() == "USD" else info.currency + " "
        _row1 = box.row(align=True)
        _row1.label(text=i18n._("✓ 已登录"), icon="CHECKMARK")
        _row1.label(text=info.display_name, icon="USER")

        _row2 = box.row(align=True)
        _row2.label(text=i18n._("余额: %s%.2f") % (sym, info.balance), icon="FUND")
        if info.plan:
            _row2.label(text=info.plan, icon="TAG")

        if info.is_low_balance:
            warn = box.box()
            warn.label(text=i18n._("⚠ 余额较低,请尽快充值"), icon="ERROR")
        elif info.is_empty:
            warn = box.box()
            warn.label(text=i18n._("✗ 余额为 0,无法继续生成"), icon="CANCEL")

        # 操作按钮行
        _btn_row = box.row(align=True)
        _btn_row.operator("aiai.refresh_account",
                          text=i18n._("刷新"), icon="FILE_REFRESH")
        _btn_row.operator("aiai.open_billing",
                          text=i18n._("充值"), icon="FUND")
        _btn_row.operator("aiai.open_preferences",
                          text=i18n._("Key"), icon="PREFERENCES")
        _btn_row.operator("aiai.sign_out",
                          text=i18n._("退出"), icon="X")


classes = [
    AIAI_AddonPreferences,
    AIAI_PG_job_record,
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
    AIAI_OT_copy_chat,
    AIAI_OT_toggle_features,
    AIAI_OT_open_playground,
    AIAI_OT_open_download,
    AIAI_OT_clear_jobs,
    # v2.6.0+ KEY 鉴权
    AIAI_OT_sign_in,
    AIAI_OT_sign_out,
    AIAI_OT_refresh_account,
    AIAI_OT_open_billing,
    AIAI_OT_open_get_key,
    AIAI_OT_open_preferences,
    AIAI_PT_panel,
]


def load_saved_credentials():
    """Deprecated — always returns empty dict. Credentials must be entered by each user."""
    return {}


def register():
    saved = load_saved_credentials()

    # 启动时清空账户缓存,首次登录由用户手动点 "登录" 触发
    _billing.reset_account_cache()

    def get_name(name_zh):
        return i18n._(name_zh)

    AI_MODES_TRANSLATED = [
        ("text2d", get_name("文生3D"), "Text description only"),
        ("image2d", get_name("图生3D"), "Image only"),
        ("hybrid", get_name("混合"), "Both text and image"),
    ]

    AI_MODELS_TRANSLATED = [
        ("hunyuan3d", get_name("混元3D"), "Tencent cloud API"),
    ]

    bpy.types.Scene.tsr_selected_mode = bpy.props.EnumProperty(name=get_name("模式"), items=AI_MODES_TRANSLATED, default="image2d")
    bpy.types.Scene.tsr_selected_model = bpy.props.EnumProperty(name=get_name("模型"), items=AI_MODELS_TRANSLATED, default="hunyuan3d")
    bpy.types.Scene.tsr_image_path = StringProperty(name=get_name("图片路径"), subtype='FILE_PATH', default="")
    bpy.types.Scene.tsr_prompt_text = StringProperty(name=get_name("描述"), default="", maxlen=1024)
    # 目标面数 (生成 3D 模型时传给 API, Hunyuan3D 接受范围 10000~1000000 整千递增)
    bpy.types.Scene.tsr_face_count = IntProperty(name=get_name("目标面数"), default=30000, min=10000, max=1000000, step=1000)
    # 注: tsr_remove_background 和 tsr_apply_post_process 已移除 — 它们是死参数,
    # Hunyuan3D API 的 submit() 不识别这两个字段,对生成结果无任何影响,
    # 继续暴露在 UI 上会误导用户。
    
    bpy.types.Scene.tsr_hunyuan_secret_id = bpy.props.StringProperty(name=get_name("Secret ID"), default=saved.get("hunyuan_secret_id", ""))
    bpy.types.Scene.tsr_hunyuan_secret_key = bpy.props.StringProperty(name=get_name("Secret Key"), default=saved.get("hunyuan_secret_key", ""))
    bpy.types.Scene.tsr_csma_secret_id = bpy.props.StringProperty(name=get_name("CSMAI Key"), default=saved.get("csma_secret_id", ""))
    bpy.types.Scene.tsr_meshgpt_api_key = bpy.props.StringProperty(name=get_name("MeshGPT Key"), default=saved.get("meshgpt_api_key", ""))
    bpy.types.Scene.tsr_luma_api_key = bpy.props.StringProperty(name=get_name("LumaAI Key"), default=saved.get("luma_api_key", ""))
    
    bpy.types.Scene.tsr_decimation_ratio = FloatProperty(name=get_name("减面比率"), default=0.1, min=0.01, max=1.0, subtype='FACTOR')
    bpy.types.Scene.tsr_decimation_preserveTopology = BoolProperty(name=get_name("保留拓扑"), default=False)
    bpy.types.Scene.tsr_target_face_count = IntProperty(name=get_name("目标面数"), default=1000, min=100, max=100000)
    bpy.types.Scene.tsr_quadify = BoolProperty(name=get_name("转换为四边面"), default=False)
    bpy.types.Scene.tsr_tool_tab = EnumProperty(name=get_name("功能区"), items=[("decimation", i18n._("减面"), ""), ("topology", i18n._("拓扑"), ""), ("rigging", i18n._("绑定"), ""), ("animation", i18n._("动画"), "")], default="decimation")
    bpy.types.Scene.tsr_rig_type = EnumProperty(name=get_name("骨骼类型"), items=[("basic", i18n._("基础"), ""), ("biped", i18n._("双足"), ""), ("quadruped", i18n._("四足"), "")], default="biped")
    bpy.types.Scene.tsr_auto_weights = BoolProperty(name=get_name("自动权重"), default=False)
    bpy.types.Scene.tsr_anim_type = EnumProperty(name=get_name("动画类型"), items=[("rotation", i18n._("旋转"), ""), ("scale", i18n._("缩放"), ""), ("location", i18n._("位移"), "")], default="rotation")
    bpy.types.Scene.tsr_anim_duration = FloatProperty(name=get_name("时长（秒）"), default=2.0, min=0.1, max=60.0)
    bpy.types.Scene.tsr_bake_resolution = IntProperty(name=get_name("烘焙分辨率"), default=1024, min=256, max=4096)
    
    bpy.types.Scene.tsr_llm_provider = EnumProperty(name=get_name("LLM供应商"), items=LLM_PROVIDERS, default=saved.get("llm_provider", "opencode"))
    bpy.types.Scene.tsr_llm_model = StringProperty(name=get_name("LLM模型"), default=saved.get("llm_model", "MiniMax-M2.7-highspeed"))
    bpy.types.Scene.tsr_llm_api_key = StringProperty(name=get_name("LLM API Key"), default=saved.get("llm_api_key", ""))
    bpy.types.Scene.tsr_llm_base_url = StringProperty(name=get_name("API地址"), default=saved.get("llm_base_url", "https://api.minimax.chat/v1"))
    # 注意：Blender 5.1 的 StringProperty 不再支持 subtype='MULTI_LINE'
    # 多行输入通过 draw() 时的 column().scale_y(2.0) + 一个显示提示行实现
    bpy.types.Scene.tsr_llm_user_input = StringProperty(
        name=get_name("对话输入"), default="", maxlen=2000
    )
    bpy.types.Scene.tsr_llm_chat_history = StringProperty(name=get_name("对话历史"), default="[]")
    bpy.types.Scene.tsr_opencode_model = StringProperty(name=get_name("OpenCode模型"), default=saved.get("opencode_model", "MiniMax-M2.7-highspeed"))
    bpy.types.Scene.tsr_opencode_api_key = StringProperty(name=get_name("OpenCode API Key"), default=saved.get("opencode_api_key", ""))
    bpy.types.Scene.tsr_opencode_base_url = StringProperty(name=get_name("OpenCode API地址"), default=saved.get("opencode_base_url", "https://api.minimax.chat/v1"))

    # 功能区折叠状态 (持久化到 .blend 文件，因为是 Scene 级别属性)
    bpy.types.Scene.tsr_features_expanded = bpy.props.BoolProperty(
        name=get_name("功能区展开"),
        default=False,
        description="Show/hide features section (saved with .blend file)"
    )

    # 加载 LOGO 等品牌资源(必须在 register_class 之前,这样 AddonPreferences.draw 能用)
    _branding.register()

    for cls in classes:
        bpy.utils.register_class(cls)

    # Active Jobs: 必须在 PropertyGroup 类注册之后再创建 CollectionProperty
    bpy.types.Scene.tsr_active_jobs = bpy.props.CollectionProperty(type=AIAI_PG_job_record)
    # tsr_jobs_expanded 已移除 — Active Jobs 区域始终展开,不再需要折叠开关

    i18n.register_translations()

    # 启动后台版本检查 (非阻塞, 不影响 Blender 启动速度)
    _start_update_check()


def unregister():
    i18n.unregister_translations()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    _billing.reset_account_cache()
    
    props = [
        'tsr_selected_mode', 'tsr_selected_model', 'tsr_image_path', 'tsr_prompt_text',
        'tsr_face_count',
        'tsr_hunyuan_secret_id', 'tsr_hunyuan_secret_key', 'tsr_csma_secret_id',
        'tsr_meshgpt_api_key', 'tsr_luma_api_key',
        'tsr_decimation_ratio', 'tsr_decimation_preserveTopology', 'tsr_target_face_count',
        'tsr_quadify', 'tsr_tool_tab', 'tsr_rig_type', 'tsr_auto_weights', 'tsr_anim_type', 'tsr_anim_duration',
        'tsr_bake_resolution',
        'tsr_llm_provider', 'tsr_llm_model', 'tsr_llm_api_key', 'tsr_llm_base_url',
        'tsr_llm_user_input', 'tsr_llm_chat_history',
        'tsr_opencode_model', 'tsr_opencode_api_key', 'tsr_opencode_base_url',
        'tsr_features_expanded',
        'tsr_active_jobs',
    ]
    for prop in props:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)

    # 释放 LOGO 等品牌资源
    _branding.unregister()


if __name__ == "__main__":
    register()