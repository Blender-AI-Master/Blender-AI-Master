"""Blender-AI Playground 统一 API 客户端.

所有 AI 调用(3D 生成、LLM 对话)都通过 blender-ai.com 代理,
用户使用单个 KEY 鉴权,扣费由后端按调用次数结算到用户的
https://www.blender-ai.com/dashboard/settings?section=account 账户。

后端合约:见 docs/BACKEND_API.md
"""

import base64
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import APIResponse, APIStatus


# ============================================================
# 可调参数 (与后端对齐后,只需改这里)
# ============================================================
PRODUCTION_BASE_URL = "https://www.blender-ai.com:8443"
LOCAL_BASE_URL = "http://localhost:3000"
API_VERSION = "v1"

REQUEST_TIMEOUT = 30          # 通用请求超时(秒)
DOWNLOAD_TIMEOUT = 600        # 模型下载超时
CHAT_TIMEOUT = 600            # LLM 对话超时
POLL_INTERVAL = 5             # 任务轮询间隔
MAX_POLL_DURATION = 900       # 单次任务最长等待 (15 分钟)

PLUGIN_VERSION = "2.6.0"
USER_AGENT = f"BlenderAIAssistant/{PLUGIN_VERSION}"


# ============================================================
# 计费错误层级
# ============================================================
class BillingError(Exception):
    """所有计费相关异常的基类."""

    def __init__(self, message: str, server_message: str = ""):
        super().__init__(message)
        self.message = message
        self.server_message = server_message

    def __str__(self) -> str:
        return self.message


class InvalidKeyError(BillingError):
    """401 — KEY 无效/已过期/已停用."""


class InsufficientBalanceError(BillingError):
    """402 — 余额不足."""

    def __init__(self, message: str, server_message: str = "",
                 required: float = 0.0, balance: float = 0.0):
        super().__init__(message, server_message)
        self.required = required
        self.balance = balance


class RateLimitError(BillingError):
    """429 — 限流."""


class AccountInactiveError(BillingError):
    """403 — 账户被禁用."""


class NetworkError(BillingError):
    """网络/DNS 故障."""


# ============================================================
# 账户信息数据类
# ============================================================
@dataclass
class AccountInfo:
    email: str = ""
    plan: str = ""                # "free" | "pro" | "team"
    balance: float = 0.0
    currency: str = "USD"
    is_active: bool = False
    expires_at: str = ""
    created_at: str = ""
    lifetime_spent: float = 0.0
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_low_balance(self) -> bool:
        """余额 < $1 时算低余额,显示警告."""
        return 0 < self.balance < 1.0

    @property
    def is_empty(self) -> bool:
        return self.balance <= 0

    @property
    def display_name(self) -> str:
        return self.email or "(未知账户)"


# ============================================================
# 模型价格
# ============================================================
@dataclass
class ModelPricing:
    id: str
    display_name: str
    price_per_call: float
    currency: str = "USD"
    description: str = ""


# ============================================================
# 客户端
# ============================================================
class PlaygroundAPI:
    """统一鉴权 + 计费的 API 客户端."""

    def __init__(self, api_key: str = "", base_url: str = PRODUCTION_BASE_URL):
        self.api_key = (api_key or "").strip()
        self.base_url = base_url
        self._last_account: Optional[AccountInfo] = None

    # ---------- 内部:HTTP ----------
    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str,
                 body: Optional[Dict[str, Any]] = None,
                 timeout: int = REQUEST_TIMEOUT) -> Dict[str, Any]:
        if not self.api_key:
            raise InvalidKeyError("API Key 为空,请先在偏好设置中填写")

        url = f"{self.base_url}/{API_VERSION}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
        context = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return {}
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"_raw": raw}
        except urllib.error.HTTPError as e:
            self._raise_for_status(e)
        except urllib.error.URLError as e:
            raise NetworkError(str(e.reason), str(e))
        except BillingError:
            raise
        except Exception as e:
            raise BillingError(f"请求失败: {e}", str(e))

        return {}  # unreachable

    def _raise_for_status(self, e: urllib.error.HTTPError) -> None:
        body_text = ""
        try:
            body_text = e.read().decode("utf-8")
        except Exception:
            pass
        server_msg = body_text
        server_payload: Dict[str, Any] = {}
        if body_text:
            try:
                server_payload = json.loads(body_text)
                server_msg = server_payload.get("error", body_text)
            except Exception:
                pass
        server_msg = (server_msg or "")[:500]

        if e.code == 401:
            raise InvalidKeyError("API Key 无效或已过期", server_msg)
        if e.code == 402:
            raise InsufficientBalanceError(
                "账户余额不足,请前往 blender-ai.com 充值",
                server_msg,
                required=float(server_payload.get("required", 0) or 0),
                balance=float(server_payload.get("balance", 0) or 0),
            )
        if e.code == 403:
            raise AccountInactiveError("账户已被停用,请联系 support@blender-ai.com", server_msg)
        if e.code == 429:
            raise RateLimitError("请求过于频繁,请稍后再试", server_msg)
        raise BillingError(f"服务器错误: HTTP {e.code}", server_msg)

    # ---------- 鉴权 / 账户 ----------
    def validate_key(self) -> AccountInfo:
        """安装后第一次调用,验证 KEY 有效性,获取账户信息."""
        data = self._request("POST", "/auth/validate", {})
        info = self._parse_account(data)
        self._last_account = info
        return info

    def get_account_info(self) -> AccountInfo:
        data = self._request("GET", "/account")
        info = self._parse_account(data)
        self._last_account = info
        return info

    def get_pricing(self) -> List[ModelPricing]:
        try:
            data = self._request("GET", "/pricing")
        except BillingError:
            return self._default_pricing()
        items = data.get("models", []) if isinstance(data, dict) else data
        result: List[ModelPricing] = []
        for item in items or []:
            try:
                result.append(ModelPricing(
                    id=item.get("id", ""),
                    display_name=item.get("display_name", item.get("id", "")),
                    price_per_call=float(item.get("price_per_call", 0) or 0),
                    currency=item.get("currency", "USD"),
                    description=item.get("description", ""),
                ))
            except Exception:
                continue
        return result or self._default_pricing()

    def get_usage_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            data = self._request("GET", f"/account/usage?limit={int(limit)}")
        except BillingError:
            return []
        return data.get("usage", []) if isinstance(data, dict) else data

    # ---------- 3D 模型 ----------
    def submit_model(self, *, model: str, prompt: str = "",
                     image_path: str = "", face_count: int = 30000,
                     mode: str = "image2d") -> APIResponse:
        body: Dict[str, Any] = {
            "model": model,
            "mode": mode,
            "face_count": int(face_count),
        }
        if prompt:
            body["prompt"] = prompt
        if image_path:
            if not os.path.exists(image_path):
                return APIResponse(success=False, error=f"图片不存在: {image_path}")
            with open(image_path, "rb") as f:
                body["image_base64"] = base64.b64encode(f.read()).decode("utf-8")

        data = self._request("POST", "/models/generate", body, timeout=60)
        job_id = data.get("job_id") or data.get("jobId") or data.get("id")
        if not job_id:
            return APIResponse(success=False, error=data.get("error", "未返回 job_id"))
        return APIResponse(
            success=True,
            job_id=job_id,
            status=APIStatus.WAIT,
            data={"charged": data.get("charged"), "balance_after": data.get("balance_after")},
        )

    def query_model_job(self, job_id: str) -> APIResponse:
        data = self._request("GET", f"/models/jobs/{job_id}")
        status_str = str(data.get("status") or "WAIT").upper()
        status_map = {
            "WAIT": APIStatus.WAIT,
            "QUEUED": APIStatus.WAIT,
            "RUN": APIStatus.RUN,
            "PROCESSING": APIStatus.RUN,
            "DONE": APIStatus.DONE,
            "COMPLETED": APIStatus.DONE,
            "SUCCESS": APIStatus.DONE,
            "FAIL": APIStatus.FAIL,
            "FAILED": APIStatus.FAIL,
            "CANCELLED": APIStatus.FAIL,
        }
        status = status_map.get(status_str, APIStatus.WAIT)
        return APIResponse(
            success=(status != APIStatus.FAIL),
            job_id=job_id,
            status=status,
            data=data,
            error=data.get("error"),
        )

    def download_model(self, job_id: str, output_path: str) -> APIResponse:
        url = f"{self.base_url}/{API_VERSION}/models/jobs/{job_id}/download"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT, context=context) as resp:
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                with open(output_path, "wb") as f:
                    while True:
                        chunk = resp.read(64 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                return APIResponse(success=True, data={"file_path": output_path})
        except urllib.error.HTTPError as e:
            return APIResponse(success=False, error=f"下载失败 HTTP {e.code}")
        except Exception as e:
            return APIResponse(success=False, error=str(e))

    def wait_for_model(self, job_id: str,
                       timeout: int = MAX_POLL_DURATION,
                       poll_interval: int = POLL_INTERVAL) -> APIResponse:
        start = time.time()
        while time.time() - start < timeout:
            r = self.query_model_job(job_id)
            if not r.success:
                return r
            if r.status in (APIStatus.DONE, APIStatus.FAIL):
                return r
            time.sleep(poll_interval)
        return APIResponse(success=False, error="任务等待超时")

    # ---------- LLM 对话 (Creative Agent 代理) ----------
    def chat(self, *, messages: List[Dict[str, str]],
             model: str = "auto",
             temperature: float = 0.7,
             max_tokens: int = 4096,
             timeout: int = CHAT_TIMEOUT) -> Dict[str, Any]:
        body = {
            "model": model,
            "messages": messages,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }
        data = self._request("POST", "/chat/completions", body, timeout=timeout)
        return {
            "success": True,
            "content": (
                data.get("content")
                or data.get("text")
                or data.get("message", {}).get("content", "")
                or ""
            ),
            "model_used": data.get("model_used", ""),
            "usage": data.get("usage", {}),
            "balance_after": data.get("balance_after"),
        }

    # ---------- 工具 ----------
    @staticmethod
    def _default_pricing() -> List[ModelPricing]:
        return [
            ModelPricing(
                id="hunyuan3d",
                display_name="Hunyuan 3D",
                price_per_call=0.80,
                currency="USD",
                description="Realistic 3D model from text or image",
            ),
            ModelPricing(
                id="creative-agent",
                display_name="Creative Agent (CLI-Anything)",
                price_per_call=0.05,
                currency="USD",
                description="Natural language → Blender commands",
            ),
        ]

    @staticmethod
    def fetch_plugin_info(base_url: str = PRODUCTION_BASE_URL) -> Optional[Dict[str, Any]]:
        """获取服务器端最新插件版本信息 (无需认证).

        返回 dict 包含 version, url, size_kb, blender_min, blender_max,
        released_at, changelog。网络失败时返回 None。
        """
        url = f"{base_url}/{API_VERSION}/downloads/plugin/info"
        req = urllib.request.Request(url, method="GET", headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        })
        context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, timeout=10, context=context) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except Exception:
            return None

    def _parse_account(self, data: Dict[str, Any]) -> AccountInfo:
        return AccountInfo(
            email=str(data.get("email", "") or ""),
            plan=str(data.get("plan", "") or ""),
            balance=float(data.get("balance", 0) or 0),
            currency=str(data.get("currency", "USD") or "USD"),
            is_active=bool(data.get("is_active", True)),
            expires_at=str(data.get("expires_at", "") or ""),
            created_at=str(data.get("created_at", "") or ""),
            lifetime_spent=float(data.get("lifetime_spent", 0) or 0),
            raw=data,
        )


# ============================================================
# 便捷函数
# ============================================================
def format_billing_error(error: BillingError) -> str:
    """把异常转成给用户看的中文消息."""
    if isinstance(error, InvalidKeyError):
        return "API Key 无效或已过期,请在偏好设置中重新填写"
    if isinstance(error, InsufficientBalanceError):
        if error.required and error.balance is not None:
            return (f"账户余额不足 (需 ${error.required:.2f},"
                    f"余额 ${error.balance:.2f}),请前往 blender-ai.com 充值")
        return "账户余额不足,请前往 blender-ai.com 充值"
    if isinstance(error, RateLimitError):
        return "请求过于频繁,请稍后再试"
    if isinstance(error, AccountInactiveError):
        return "账户已被停用,请联系 support@blender-ai.com"
    if isinstance(error, NetworkError):
        return f"网络错误: {error.message}"
    return f"服务异常: {error.message}"


def check_for_update(base_url: str = PRODUCTION_BASE_URL) -> Optional[Dict[str, Any]]:
    """检查插件是否有新版本.

    对比本地 PLUGIN_VERSION 与服务器端版本,如果有新版本则返回
    plugin_info dict (含 version, url, changelog 等),否则返回 None。
    网络/解析失败也返回 None (静默失败,不影响 Blender 启动)。
    """
    info = PlaygroundAPI.fetch_plugin_info(base_url)
    if not info:
        return None
    remote_version = str(info.get("version", "")).strip()
    if not remote_version:
        return None
    if remote_version != PLUGIN_VERSION:
        return info
    return None


# 暴露给 api/__init__.py
__all__ = [
    "PRODUCTION_BASE_URL",
    "LOCAL_BASE_URL",
    "API_VERSION",
    "PLUGIN_VERSION",
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
]
