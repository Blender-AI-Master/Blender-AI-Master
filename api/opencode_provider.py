"""OpenCode API 调用模块 - 通过持久会话调用 OpenCode AI (Creative Agent 模式)."""

import subprocess
import json
import os
import re
import time
import socket
import threading


OPENCODE_PATH = os.environ.get(
    "OPENCODE_EXE",
    os.path.join(os.environ.get("APPDATA", ""), "npm", "node_modules", "opencode-ai", "bin", "opencode.exe")
)

DEFAULT_PORT = 4096
SERVER_URL = f"http://localhost:{DEFAULT_PORT}"


def is_port_in_use(port: int) -> bool:
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


class OpenCodeProvider:
    """OpenCode 大模型接口 - 通过持久会话调用 opencode --attach"""

    _server_process = None
    _server_lock = threading.Lock()
    _initialized = False

    def __init__(self, model: str = "", api_key: str = "", base_url: str = ""):
        self.provider = "opencode"
        self.model = model or "creative"
        self.api_key = api_key
        self.base_url = base_url
        self._opencode_path = self._find_opencode()

    def _find_opencode(self) -> str:
        """查找 opencode 可执行文件"""
        if os.path.exists(OPENCODE_PATH):
            return OPENCODE_PATH

        possible_paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "npm", "node_modules", "opencode-ai", "bin", "opencode.exe"),
            r"C:\Users\Administrator\AppData\Roaming\npm\node_modules\opencode-ai\bin\opencode.exe",
            "opencode",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return "opencode"

    @classmethod
    def _ensure_server_running(cls) -> bool:
        """确保 OpenCode 服务正在运行"""
        with cls._server_lock:
            if cls._server_process is not None and cls._server_process.poll() is None:
                return True

            if is_port_in_use(DEFAULT_PORT):
                return True

            try:
                cls._server_process = subprocess.Popen(
                    [OPENCODE_PATH, "serve", "--port", str(DEFAULT_PORT)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                time.sleep(3)
                return True
            except Exception:
                return False

    def chat(self, messages: list, timeout: int = 600) -> dict:
        """发送对话请求，返回结果"""
        try:
            user_input = self._extract_user_input(messages)
            if not user_input:
                return {"success": False, "error": "未找到用户输入"}

            if not self._ensure_server_running():
                return {"success": False, "error": "无法启动 OpenCode 服务"}

            result = self._run_opencode_attach(user_input, timeout)
            return result

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"OpenCode 执行超时 ({timeout}s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_user_input(self, messages: list) -> str:
        """从消息列表中提取用户输入"""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return ""

    def _run_opencode_attach(self, user_input: str, timeout: int) -> dict:
        """通过 --attach 连接持久服务运行 opencode"""
        cmd = [
            self._opencode_path,
            "run",
            user_input,
            "--agent", "creative",
            "--format", "json",
            "--attach", SERVER_URL,
            "--continue",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0 and not result.stdout:
                return {"success": False, "error": result.stderr or f"OpenCode 执行失败 (code {result.returncode})"}

            response_text = self._parse_creative_output(result.stdout)
            return {"success": True, "content": response_text}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_creative_output(self, output: str) -> str:
        """解析 creative agent 的 JSON 输出，提取 CLI 命令"""
        try:
            lines = output.strip().split("\n")
            full_content = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith("{"):
                    try:
                        data = json.loads(line)

                        if "error" in data:
                            return f"OpenCode 错误: {data.get('error')}"

                        if data.get("type") == "result":
                            content = data.get("content", "")
                            if isinstance(content, str):
                                full_content.append(content)
                            elif isinstance(content, dict):
                                text = content.get("text", "")
                                if text:
                                    full_content.append(text)

                        if "message" in data:
                            msg = data.get("message", {})
                            if isinstance(msg, dict):
                                content = msg.get("content", "")
                                if isinstance(content, str):
                                    full_content.append(content)
                    except json.JSONDecodeError:
                        continue

            if full_content:
                combined = "\n".join(full_content)
                return self._extract_cli_commands_from_creative(combined)

            return self._extract_cli_commands_from_creative(output)

        except Exception as e:
            return f"解析输出失败: {str(e)}\n\n{output}"

    def _extract_cli_commands_from_creative(self, text: str) -> str:
        """从 creative agent 输出中提取 CLI 命令"""
        if not text:
            return text

        text = text.strip()
        lines = text.split("\n")
        command_lines = []
        in_command_section = False

        skip_keywords = [
            "分析", "思考", "组件", "设计", "细节", "规划",
            "Round", "完成", "命令", "---", "```bash"
        ]

        for line in lines:
            line_stripped = line.strip()

            if "## CLI Commands" in line_stripped or "## CLI" in line_stripped:
                in_command_section = True
                continue

            if "## End Commands" in line_stripped:
                break

            if "```" in line_stripped:
                in_command_section = not in_command_section
                continue

            if any(skip in line_stripped for skip in skip_keywords):
                continue

            if line_stripped.startswith("🧠"):
                continue

            if self._is_cli_command_line(line_stripped):
                cleaned = self._clean_command_line(line_stripped)
                if cleaned and len(cleaned) > 5:
                    command_lines.append(cleaned)

        if command_lines:
            return "\n".join(command_lines)

        return text

    def _is_cli_command_line(self, line: str) -> bool:
        """检查是否是一行 CLI 命令"""
        if not line:
            return False

        line_clean = line.split('#')[0].strip()

        if not line_clean:
            return False

        cli_prefixes = [
            "scene ", "object ", "material ", "modifier ",
            "light ", "camera ", "animation ", "render ",
            "session ", "preview "
        ]

        return any(line_clean.startswith(prefix) for prefix in cli_prefixes)

    def _clean_command_line(self, line: str) -> str:
        """清理命令行，去除多余字符，修复 mesh type"""
        line = line.strip()

        line = re.sub(r'^[-•*]\s*', '', line)

        line = re.sub(r'\s{2,}', ' ', line)

        mesh_type_map = {
            r'object add box\b': 'object add cube',
            r'object add ico_sphere\b': 'object add ico_sphere',
        }
        for pattern, replacement in mesh_type_map.items():
            line = re.sub(pattern, replacement, line)

        return line


def build_opencode_messages(user_input: str, chat_history: list = None) -> list:
    """构建 OpenCode 消息列表"""
    messages = [{"role": "system", "content": "你是一个专业的 3D 建模专家，会进行创意多轮思考后输出 CLI-Anything 命令。"}]

    if chat_history:
        for entry in chat_history[-10:]:
            messages.append({"role": entry.get("role", "user"), "content": entry.get("content", "")})

    messages.append({"role": "user", "content": user_input})
    return messages
