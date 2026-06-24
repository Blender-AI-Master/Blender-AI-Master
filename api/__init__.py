"""AI Model API Adapters.

v2.6.0 起:所有 AI 调用统一走 blender-ai.com 代理 (api.playground.PlaygroundAPI),
用户使用单个 KEY 鉴权,扣费由后端结算到 https://www.blender-ai.com/dashboard/settings?section=account。
Hunyuan3D / OpenCode 直连实现保留为内部/调试用,不暴露给 UI。
"""

from .base import BaseAPI, APIResponse, APIStatus
from .playground import (
    PlaygroundAPI,
    AccountInfo,
    ModelPricing,
    BillingError,
    InvalidKeyError,
    InsufficientBalanceError,
    RateLimitError,
    AccountInactiveError,
    NetworkError,
    format_billing_error,
    check_for_update,
    API_VERSION,
    PLUGIN_VERSION,
)
from .hunyuan import Hunyuan3DAPI
from .opencode_provider import OpenCodeProvider

__all__ = [
    "BaseAPI",
    "APIResponse",
    "APIStatus",
    "PlaygroundAPI",
    "AccountInfo",
    "ModelPricing",
    "BillingError",
    "InvalidKeyError",
    "InsufficientBalanceError",
    "RateLimitError",
    "AccountInactiveError",
    "NetworkError",
    "format_billing_error",
    "check_for_update",
    "API_VERSION",
    "PLUGIN_VERSION",
    "Hunyuan3DAPI",
    "OpenCodeProvider",
] 