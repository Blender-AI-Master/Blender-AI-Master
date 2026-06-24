"""LLM API 调用模块 - 支持多种大模型."""

import json
import urllib.request
import urllib.error
from .opencode_provider import OpenCodeProvider


LLM_PROVIDERS = [
    ("openai", "OpenAI", "gpt-4o, gpt-4.1, gpt-4.1-mini"),
    ("anthropic", "Anthropic", "claude-3-5-sonnet, claude-3-7-sonnet"),
    ("gemini", "Google Gemini", "gemini-2.5-pro, gemini-2.5-flash"),
    ("deepseek", "DeepSeek", "deepseek-chat, deepseek-coder"),
    ("qwen", "阿里通义", "qwen-plus, qwen-max"),
    ("zhipu", "智谱GLM", "glm-4-plus, glm-4-air"),
    ("minimax", "MiniMax", "MiniMax-01, MiniMax-Text"),
    ("opencode", "OpenCode", "创意多轮思考 AI"),
    ("ollama", "Ollama", "本地模型"),
]

LLM_MODELS = {
    "openai": ["gpt-4o", "gpt-4.1", "gpt-4.1-mini", "gpt-4-turbo"],
    "anthropic": ["claude-3-5-sonnet-20240620", "claude-3-7-sonnet-20240620", "claude-3-opus"],
    "gemini": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    "deepseek": ["deepseek-chat", "deepseek-coder"],
    "qwen": ["qwen-plus", "qwen-max", "qwen-turbo"],
    "zhipu": ["glm-4-plus", "glm-4-air", "glm-3-turbo"],
    "minimax": ["MiniMax-01", "abab6.5s-chat"],
    "opencode": ["creative", "default"],
    "uclaw": ["minimax-m2.7", "MiniMax-M2.5", "gpt-4o", "gpt-4o-mini", "claude-3.5-sonnet"],
    "ollama": ["llama3", "llama3.1", "mistral", "codellama"],
}

DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-sonnet-20240620",
    "gemini": "gemini-2.5-flash",
    "deepseek": "deepseek-chat",
    "qwen": "qwen-plus",
    "zhipu": "glm-4-plus",
    "minimax": "MiniMax-01",
    "opencode": "creative",
    "uclaw": "MiniMax-M2.5",
    "ollama": "llama3",
}

SYSTEM_PROMPT = """你是一个专业的 Blender 3D 建模助手，名为 CLI-Anything。

你可以帮助用户：
- 创建 3D 场景（scene new/open/save/info）
- 添加和操作 3D 对象（object add/remove/duplicate/transform）
- 创建和管理材质（material create/assign/set）
- 添加和配置修改器（modifier add/remove/set）
- 设置相机和灯光（camera add/set, light add/set）
- 创建关键帧动画（animation keyframe）
- 执行渲染（render execute）

用户用自然语言描述需求时，你应该生成对应的 CLI-Anything 命令序列。

**重要**：请只输出命令，不要输出其他解释。每个命令一行。
命令格式：command subcommand --arg1 value1 --arg2 value2

例如：
用户: 创建一个红色的立方体放在原点
输出:
scene new --name MyScene
object add cube --name Cube --location 0,0,0
material create --name Red --color 1,0,0,1
object set-material --object Cube --material Red

用户: 帮我做一个机器人模型
输出:
scene new --name robot
object add capsule --name body --location 0,1,0 --scale 1,2,1
object add sphere --name head --location 0,3.5,0 --scale 0.6
material create --name metal --color 0.8,0.8,0.9,1 --metallic 1.0 --roughness 0.2
object set-material --object body --material metal
object set-material --object head --material metal

开始帮助用户："""


class LLMProvider:
    """大模型统一接口"""
    
    def __init__(self, provider: str, model: str, api_key: str, base_url: str = ""):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        default_url = self._get_default_url(provider)
        if base_url and base_url != default_url:
            if provider == "minimax" and not base_url.endswith("/text/chatcompletion_v2"):
                if base_url.endswith("/v1"):
                    base_url = base_url + "/text/chatcompletion_v2"
            self.base_url = base_url
        else:
            self.base_url = default_url
    
    def _get_default_url(self, provider: str) -> str:
        urls = {
            "openai": "https://api.openai.com/v1/chat/completions",
            "anthropic": "https://api.anthropic.com/v1/messages",
            "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
            "deepseek": "https://api.deepseek.com/v1/chat/completions",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            "minimax": "https://api.minimax.chat/v1/text/chatcompletion_v2",
            "uclaw": "https://api.uclaw.me",
            "ollama": "http://localhost:11434/api/chat",
        }
        return urls.get(provider, "")
    
    def chat(self, messages: list, timeout: int = 120) -> dict:
        """发送对话请求，返回结果"""
        if self.provider == "openai":
            return self._chat_openai(messages, timeout)
        elif self.provider == "anthropic":
            return self._chat_anthropic(messages, timeout)
        elif self.provider == "gemini":
            return self._chat_gemini(messages, timeout)
        elif self.provider in ["deepseek", "qwen", "zhipu", "minimax", "uclaw"]:
            return self._chat_openai(messages, timeout)
        elif self.provider == "ollama":
            return self._chat_ollama(messages, timeout)
        elif self.provider == "opencode":
            return self._chat_opencode(messages, 600)
        else:
            return {"success": False, "error": f"不支持的提供商: {self.provider}"}
    
    def _chat_openai(self, messages: list, timeout: int) -> dict:
        """OpenAI 兼容接口"""
        url = self.base_url
        if not any(x in url for x in ["/chat/completions", "/text/chatcompletion"]):
            if url.endswith("/v1"):
                url = url + "/chat/completions"
            elif url.endswith("/"):
                url = url + "v1/chat/completions"
            else:
                url = url + "/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
        }
        return self._send_request(url, headers, data, timeout)
    
    def _chat_anthropic(self, messages: list, timeout: int) -> dict:
        """Anthropic Claude 接口"""
        url = self.base_url
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true",
        }
        system_msg = ""
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg.get("content", "")
            else:
                filtered_messages.append(msg)
        
        data = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_msg,
            "messages": filtered_messages,
        }
        return self._send_request(url, headers, data, timeout)
    
    def _chat_gemini(self, messages: list, timeout: int) -> dict:
        """Google Gemini 接口"""
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        contents = []
        for msg in messages:
            if msg.get("role") == "user":
                contents.append({"role": "user", "parts": [{"text": msg.get("content", "")}]})
            elif msg.get("role") == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg.get("content", "")}]})
        
        data = {"contents": contents}
        return self._send_request(url, headers, data, timeout)
    
    def _chat_ollama(self, messages: list, timeout: int) -> dict:
        """Ollama 本地接口"""
        url = self.base_url
        headers = {"Content-Type": "application/json"}

        formatted_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                formatted_messages.append({"role": "system", "content": msg.get("content", "")})
            else:
                formatted_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        data = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": False,
        }
        return self._send_request(url, headers, data, timeout)

    def _chat_opencode(self, messages: list, timeout: int = 180) -> dict:
        """OpenCode 创意 AI 接口"""
        opencode = OpenCodeProvider(model=self.model, api_key=self.api_key, base_url=self.base_url)
        return opencode.chat(messages, timeout)
    
    def _send_request(self, url: str, headers: dict, data: dict, timeout: int) -> dict:
        """发送 HTTP 请求"""
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers=headers,
            )
            import ssl
            context = ssl.create_default_context()
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context), urllib.request.HTTPRedirectHandler)
            with opener.open(req, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                
                if self.provider == "openai" or self.provider in ["deepseek", "qwen", "zhipu", "minimax", "uclaw"]:
                    return {"success": True, "content": result.get("choices", [{}])[0].get("message", {}).get("content", "")}
                elif self.provider == "anthropic":
                    return {"success": True, "content": result.get("content", [{}])[0].get("text", "")}
                elif self.provider == "gemini":
                    return {"success": True, "content": result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")}
                elif self.provider == "ollama":
                    return {"success": True, "content": result.get("message", {}).get("content", "")}
                else:
                    return {"success": True, "content": str(result)}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            return {"success": False, "error": f"HTTP {e.code}: {error_body}"}
        except urllib.error.URLError as e:
            return {"success": False, "error": f"网络错误: {e.reason}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def parse_commands(response_text: str) -> list:
    """解析 LLM 返回的命令"""
    commands = []
    in_thinking_block = False
    in_cli_section = False
    
    lines = response_text.strip().split("\n")
    
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
            
        if line.startswith("<think>"):
            in_thinking_block = True
            continue
        if line.startswith("</think"):
            in_thinking_block = False
            continue
            
        if in_thinking_block:
            continue
            
        if "## CLI Commands" in line or "## CLI" in line:
            in_cli_section = True
            continue
        if "## End Commands" in line:
            in_cli_section = False
            break
            
        if line.startswith("#"):
            continue
            
        if line.startswith("{"):
            continue
            
        if line.startswith("```"):
            line = line[3:].strip()
            if line.startswith(("bash", "python", "sh")):
                line = line[line.find(" ", 4) + 1:].strip() if " " in line[4:] else line[4:]
                
        cli_prefixes = (
            "scene ", "object ", "material ", "modifier ",
            "light ", "camera ", "animation ", "render ",
            "session ", "preview "
        )
        
        if line.startswith(cli_prefixes):
            commands.append(line)
        elif in_cli_section and line and not line.startswith("[") and not line.startswith("输出:"):
            commands.append(line)
            
    return commands


def build_messages(user_input: str, chat_history: list, system_prompt: str = SYSTEM_PROMPT) -> list:
    """构建消息列表"""
    messages = [{"role": "system", "content": system_prompt}]
    for entry in chat_history:
        messages.append({"role": entry.get("role", "user"), "content": entry.get("content", "")})
    messages.append({"role": "user", "content": user_input})
    return messages
