"""Internationalization module for AI Assistant plugin."""

import bpy
import sys

def get_lang():
    try:
        lang = bpy.context.preferences.view.language
        print(f"[i18n] context language: {lang}")
        if lang:
            return lang
    except Exception as e:
        print(f"[i18n] context error: {e}")

    try:
        import locale
        loc = locale.getlocale()[0] or ""
        print(f"[i18n] locale: {loc}")
        if loc.startswith("en"):
            return "en_US"
    except Exception as e:
        print(f"[i18n] locale error: {e}")

    return "zh_CN"

def register_translations():
    pass

def unregister_translations():
    pass

def tr(text):
    lang = get_lang()
    if lang and lang.startswith("en"):
        translations = {
            "AI 助手": "AI Assistant",
            "目标面数": "Target Face Count",
            "模式": "Mode",
            "模型": "Model",
            "图片": "Image",
            "图片路径": "File Path",
            "描述": "Prompt",
            "设置": "Settings",
            "配置": "Configuration",
            "API 配置": "API Configuration",
            "Secret ID": "Secret ID",
            "Secret Key": "Secret Key",
            "API Key": "API Key",
            "API地址": "Base URL",
            "供应商": "Provider",
            "文生3D": "Text to 3D",
            "图生3D": "Image to 3D",
            "混合": "Hybrid",
            "混元3D": "Hunyuan3D",
            "生成 3D 模型": "Generate 3D Model",
            "选择图片": "Select Image",
            "浏览": "Browse",
            "请选择图片": "Please select an image",
            "请输入混元3D API凭证": "Please enter Hunyuan3D API credentials",
            "减面": "Decimation",
            "拓扑": "Topology",
            "绑定": "Rigging",
            "动画": "Animation",
            "骨骼绑定": "Bone Rigging",
            "生成骨骼并绑定": "Generate Bone & Bind",
            "基础仅生成主干，双足/四足才会生成四肢": "Basic generates trunk only, biped/quadruped generates limbs",
            "动画生成": "Animation Generation",
            "生成骨骼": "Generate Bone",
            "生成动画": "Generate Animation",
            "AI 对话 (CLI-Anything)": "AI Chat (CLI-Anything)",
            "发送": "Send",
            "清空": "Clear",
            "输入需求": "Enter Request",
            "保存配置": "Save Configuration",
            "配置已保存": "Configuration saved",
            "分辨率": "Resolution",
            "功能区": "Features",
            "减面设置": "Decimation Settings",
            "按比例减面，优先保留纹理": "Decimate by ratio, preserve texture",
            "纹理烘焙:": "Texture Baking:",
            "纹理烘焙": "Texture Baking",
            "烘焙分辨率": "Bake Resolution",
            "保存当前纹理": "Save Current Texture",
            "按比例减面": "Decimate by Ratio",
            "减面完成": "Decimation complete",
            "纹理重映射": " + Texture remapped",
            "应用减面": "Apply Decimation",
            "拓扑重构": "Topology Rebuild",
            "重网格化": "Remesh",
            "减面比率": "Decimation Ratio",
            "保留拓扑": "Preserve Topology",
            "纹理已保存": "Texture saved",
            "未找到纹理": "No texture found",
            "目标面数减面": "Target Face Count",
            "按目标面数减面，可转四边面": "Decimate by target, can convert to quads",
            "目标面数": "Target Face Count",
            "转换为四边面": "Convert to Quads",
            "四边面化可能带来轻微贴图变化": "Quad conversion may cause texture changes",
            "循环边已添加，拓扑已优化": "Loop cuts added, topology optimized",
            "UV已重新展开": "UV unwrapped",
            "添加循环边优化": "Add Loop Cuts",
            "重新UV展开": "Rewrap UV",
            "骨骼类型": "Bone Type",
            "基础": "Basic",
            "双足": "Biped",
            "四足": "Quadruped",
            "自动权重": "Auto Weight",
            "生成后自动绑定到当前模型": "Auto bind to current model after generation",
            "骨骼已生成": "Bone generated",
            "动画类型": "Animation Type",
            "时长（秒）": "Duration (seconds)",
            "旋转": "Rotation",
            "缩放": "Scale",
            "位移": "Location",
            "动画已生成": "Animation generated",
            "对话记录:": "Chat History:",
            "用户": "User",
            "助手": "Assistant",
            "未选择网格": "No mesh selected",
            "请先选择模型": "Please select a model first",
            # === AI Chat (CLI-Anything) panel — fix missing keys ===
            "复制": "Copy",
            "复制对话": "Copy Chat",
            "复制对话历史到剪贴板": "Copy chat history to clipboard",
            "无对话记录": "No chat history",
            "对话已复制": "Chat copied",
            "复制失败: %s": "Copy failed: %s",
            "清空对话": "Clear Chat",
            "清空对话历史": "Clear chat history",
            "对话已清空": "Chat cleared",
            "发送": "Send",
            "发送对话到 LLM": "Send chat to LLM",
            "对话完成": "Chat complete",
            "对话输入": "Chat input",
            "对话历史": "Chat history",
            "输入需求": "Enter request",
            "在此输入您要发送给 AI 的需求 (例如：'创建一个低多边形风格的山地')": "Type your request to the AI here (e.g. 'Create a low-poly style mountain')",
            "OpenCode API地址": "OpenCode API URL",
            # === 功能区折叠 ===
            "切换功能区": "Toggle Features",
            "展开或折叠功能区": "Expand or collapse the features section",
            "功能区展开": "Features Expanded",
            # === 游乐场卡片 ===
            "所选模型生成逼真且直接使用的3D模型": "Selected model generates realistic, ready-to-use 3D models",
            "每次生成费用为0.8美元": "$0.8 per generation",
            "打开游乐场": "Open Playground",
            "在浏览器中打开游乐场,查看/管理你的模型": "Open playground in browser to view/manage your models",
            "无法打开链接: %s": "Failed to open URL: %s",
            # === 偏好设置页面 (模仿 fal.ai) ===
            "Website:": "Website:",
            "No API key set!": "No API key set!",
            "Set above, or visit blender-ai.com to get one": "Set above, or visit blender-ai.com to get one",
            "Get a key at blender-ai": "Get a key at blender-ai",
            # === Active Jobs 面板 ===
            "Active Jobs": "Active Jobs",
            "No active jobs": "No active jobs",
            "清空记录": "Clear Records",
            "清空任务记录": "Clear Job Records",
            "清空所有生成任务历史": "Clear all generation job history",
            "任务记录已清空": "Job records cleared",
            "等待中": "Waiting",
            "生成中": "Generating",
            "完成": "Done",
            "失败": "Failed",
            # === 鉴权 / 账户 (v2.6.0+) ===
            "获取 Key": "Get a Key",
            "账户已停用": "Account disabled",
            "联系客服": "Contact support",
            "✓ 已登录": "✓ Signed in",
            "余额: %s%.2f": "Balance: %s%.2f",
            "⚠ 余额较低,请尽快充值": "⚠ Low balance, please top up soon",
            "✗ 余额为 0,无法继续生成": "✗ Balance is 0, cannot generate",
            "刷新": "Refresh",
            "充值": "Top up",
            "Key": "Key",
            "退出": "Sign out",
            "测试 & 登录": "Test & Sign in",
            "账户 & 充值": "Account & Billing",
            "账户: %s": "Account: %s",
            "余额: %s%.2f (%s)": "Balance: %s%.2f (%s)",
            "Account & Billing": "Account & Billing",
            "登录成功: %s (余额 $%.2f)": "Signed in: %s (Balance $%.2f)",
            "余额已刷新: $%.2f": "Balance refreshed: $%.2f",
            "已退出登录": "Signed out",
            "请先在偏好设置 (Edit > Preferences > Extensions) 中填写 API Key": "Please set API key in Preferences first",
            "API Key 为空,请先在偏好设置中填写": "API key is empty, please set in Preferences",
        }
        return translations.get(text, text)
    return text

_ = tr
