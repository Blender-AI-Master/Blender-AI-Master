"""计费层 - KEY 读取 / 账户信息缓存 / 错误转换.

供所有 Operator 通过统一接口访问 KEY 与账户状态,避免每个 operator 单独
处理 bpy.context.preferences.addons[...] 这种长链。
"""

import functools
from typing import Any, Callable, Optional

import bpy

from ..api.playground import (
    PlaygroundAPI,
    AccountInfo,
    BillingError,
    InvalidKeyError,
    format_billing_error,
    PRODUCTION_BASE_URL,
    LOCAL_BASE_URL,
)


# 插件 id 必须与 blender_manifest.toml 中一致
_ADDON_NAME = "cli_anything_blender"


# 进程内账户缓存(每次 register() 时清空)
_account_cache: Optional[AccountInfo] = None
_account_checked: bool = False     # 是否至少验证过 1 次


# ============================================================
# KEY 访问
# ============================================================
def get_api_key() -> str:
    """从 AddonPreferences 读取 KEY (去除空白)."""
    try:
        addon = bpy.context.preferences.addons.get(_ADDON_NAME)
        if addon and hasattr(addon.preferences, "playground_api_key"):
            return (addon.preferences.playground_api_key or "").strip()
    except Exception:
        pass
    return ""


def get_api_server() -> str:
    """从 AddonPreferences 读取 api_server 选项 ('production' | 'local_dev')."""
    try:
        addon = bpy.context.preferences.addons.get(_ADDON_NAME)
        if addon and hasattr(addon.preferences, "api_server"):
            return addon.preferences.api_server or "production"
    except Exception:
        pass
    return "production"


def get_base_url() -> str:
    """根据 api_server 选项返回对应的 base_url."""
    return LOCAL_BASE_URL if get_api_server() == "local_dev" else PRODUCTION_BASE_URL


def get_api() -> PlaygroundAPI:
    """构造一个带 KEY 的 PlaygroundAPI 实例,base_url 根据偏好中的 api_server 选择."""
    api_key = get_api_key()
    return PlaygroundAPI(api_key=api_key, base_url=get_base_url())


def has_key() -> bool:
    return bool(get_api_key())


# ============================================================
# 账户缓存
# ============================================================
def get_cached_account() -> Optional[AccountInfo]:
    return _account_cache


def is_account_checked() -> bool:
    return _account_checked


def set_cached_account(info: Optional[AccountInfo]) -> None:
    global _account_cache, _account_checked
    _account_cache = info
    _account_checked = info is not None


def reset_account_cache() -> None:
    global _account_cache, _account_checked
    _account_cache = None
    _account_checked = False


# ============================================================
# Operator 辅助
# ============================================================
def require_key(func: Callable[..., Any]) -> Callable[..., Any]:
    """装饰器:执行 Operator 前检查 KEY,无 KEY 直接报错并取消.

    用法:
        class AIAI_OT_x(Operator):
            @require_key
            def execute(self, context):
                ...
    """
    @functools.wraps(func)
    def wrapper(self, context):
        if not has_key():
            self.report({'ERROR'},
                        "请先在偏好设置 (Edit > Preferences > Extensions) "
                        "中填写 API Key,或前往 blender-ai.com 获取")
            try:
                bpy.ops.preferences.addon_show(module=_ADDON_NAME)
            except Exception:
                pass
            return {'CANCELLED'}
        return func(self, context)
    return wrapper


def report_billing_error(op, error: BillingError) -> None:
    """在 Operator 的 report() 中展示计费错误,自动选择图标和动作建议."""
    msg = format_billing_error(error)
    op.report({'ERROR'}, msg)


# ============================================================
# 面板显示辅助
# ============================================================
def account_status_label() -> str:
    """返回面板顶部"账户状态"区域要显示的简短文字."""
    if not has_key():
        return "未登录"
    info = get_cached_account()
    if info is None:
        return "未验证"
    if not info.is_active:
        return f"账户已停用 ({info.display_name})"
    return f"已登录: {info.display_name}"


def account_balance_label() -> str:
    """返回余额显示文字."""
    info = get_cached_account()
    if info is None:
        return ""
    sym = "$" if info.currency.upper() == "USD" else info.currency + " "
    return f"余额: {sym}{info.balance:.2f}"
