"""OpenCode API 调用模块 - 通过持久会话调用 OpenCode AI (Creative Agent 模式)."""

import subprocess
import json
import os
import re
import time
import socket
import threading


def _get_plugin_dir():
    """获取插件目录路径"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
        """查找 opencode 可执行文件，优先使用系统安装版本"""
        possible_paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "npm", "node_modules", "opencode-ai", "bin", "opencode.exe"),
            r"C:\Users\Administrator\AppData\Roaming\npm\node_modules\opencode-ai\bin\opencode.exe",
            os.path.join(os.environ.get("ProgramFiles"), "opencode", "opencode.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA"), "opencode", "opencode.exe"),
            "opencode",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                print(f"DEBUG _find_opencode: found system opencode at {path}")
                return path

        bundled_path = os.path.join(_get_plugin_dir(), "opencode_bin", "opencode.exe")
        if os.path.exists(bundled_path):
            print(f"DEBUG _find_opencode: system opencode not found, using bundled at {bundled_path}")
            return bundled_path

        return None

    def _check_opencode_available(self) -> tuple:
        """检查 OpenCode 是否可用，返回 (可用, 错误信息)"""
        opencode_path = self._find_opencode()
        if not opencode_path:
            return False, "OpenCode CLI 未安装。请先安装 OpenCode：\n1. 运行: npm install -g opencode-ai\n2. 或者从 https://github.com/anomalyco/opencode 下载安装"

        if not os.path.exists(opencode_path):
            return False, f"OpenCode 未找到: {opencode_path}"

        return True, ""

    @classmethod
    def _ensure_server_running(cls) -> bool:
        """确保 OpenCode 服务正在运行"""
        with cls._server_lock:
            if cls._server_process is not None and cls._server_process.poll() is None:
                return True

            if is_port_in_use(DEFAULT_PORT):
                return True

            opencode_path = None

            bundled_path = os.path.join(_get_plugin_dir(), "opencode_bin", "opencode.exe")
            if os.path.exists(bundled_path):
                opencode_path = bundled_path
            else:
                possible_paths = [
                    os.environ.get("OPENCODE_EXE"),
                    os.path.join(os.environ.get("APPDATA", ""), "npm", "node_modules", "opencode-ai", "bin", "opencode.exe"),
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), "npm", "node_modules", "opencode-ai", "bin", "opencode.exe"),
                    r"C:\Users\Administrator\AppData\Roaming\npm\node_modules\opencode-ai\bin\opencode.exe",
                ]
                for path in possible_paths:
                    if path and os.path.exists(path):
                        opencode_path = path
                        break

            if not opencode_path:
                return False

            try:
                cls._server_process = subprocess.Popen(
                    [opencode_path, "serve", "--port", str(DEFAULT_PORT)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                for i in range(15):
                    time.sleep(1)
                    if is_port_in_use(DEFAULT_PORT):
                        return True
                return True
            except Exception:
                return False

    def chat(self, messages: list, timeout: int = 600) -> dict:
        """发送对话请求，返回结果"""
        try:
            available, error_msg = self._check_opencode_available()
            if not available:
                return {"success": False, "error": error_msg}

            user_input = self._extract_user_input(messages)
            if not user_input:
                return {"success": False, "error": "未找到用户输入"}

            if not self._ensure_server_running():
                return {"success": False, "error": "无法启动 OpenCode 服务，请确保 Node.js 已安装"}

            result = self._run_opencode_attach(user_input, timeout)
            return result

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"OpenCode 执行超时 ({timeout}s)\n\n创意多轮思考需要较长时间，请耐心等待...\n\n如果问题持续，请尝试：\n1. 检查网络连接\n2. 简化需求描述\n3. 或使用其他 LLM 提供商（如 OpenAI、DeepSeek）"}
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
        opencode_path = self._find_opencode()
        print(f"DEBUG _run: opencode_path={opencode_path}")
        if not opencode_path:
            bundled = os.path.join(_get_plugin_dir(), "opencode_bin", "opencode.exe")
            return {"success": False, "error": f"OpenCode CLI 未找到！\n\n插件内置路径: {bundled}\n\n请确保已正确安装插件（包含 opencode_bin 目录）。\n如问题持续，请尝试使用其他 LLM 提供商。"}

        cmd = [
            opencode_path,
            "run",
            user_input,
            "--agent", "cli-creative",
            "--format", "json",
        ]
        print(f"DEBUG _run: cmd={cmd}")

        try:
            plugin_dir = _get_plugin_dir()
            print(f"DEBUG _run: working directory={plugin_dir}")
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=plugin_dir
            )
            
            try:
                stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout)
                stdout = stdout_bytes.decode('utf-8', errors='replace')
                stderr = stderr_bytes.decode('utf-8', errors='replace')
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout_bytes, stderr_bytes = proc.communicate()
                stdout = stdout_bytes.decode('utf-8', errors='replace')
                stderr = stderr_bytes.decode('utf-8', errors='replace')

            print(f"DEBUG _run: returncode={proc.returncode}, stdout_len={len(stdout)}, stderr_len={len(stderr)}")
            if stderr:
                print(f"DEBUG _run: stderr (first 500): {stderr[:500]}")
            
            if proc.returncode != 0 and not stdout:
                return {"success": False, "error": stderr or f"OpenCode 执行失败 (code {proc.returncode})"}

            response_text = self._parse_creative_output(stdout)
            return {"success": True, "content": response_text}

        except Exception as e:
            error_msg = str(e)
            if "Session not found" in error_msg or "session" in error_msg.lower():
                return {"success": False, "error": f"OpenCode 会话未找到。\n\n可能原因：\n1. 服务器未完全启动，请重试\n2. 会话已过期\n\n请重试一次，或使用其他 LLM 提供商。"}
            return {"success": False, "error": error_msg}

    def _parse_creative_output(self, output: str) -> str:
        """解析 creative agent 的 JSON 输出，提取 CLI 命令"""
        try:
            lines = output.strip().split("\n")
            full_content = []
            json_events = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("{"):
                    json_events.append(line)

            print(f"DEBUG _parse: found {len(json_events)} JSON events")
            
            for line in json_events:
                try:
                    data = json.loads(line)
                    evt_type = data.get("type", "")
                    print(f"DEBUG _parse: event type={evt_type}")
                    
                    if "error" in data:
                        return f"OpenCode 错误: {data.get('error')}"

                    if evt_type == "result":
                        content = data.get("content", "")
                        if isinstance(content, str) and content.strip():
                            print(f"DEBUG _parse: result content length={len(content)}")
                            full_content.append(content)
                        elif isinstance(content, dict):
                            text = content.get("text", "")
                            if text:
                                full_content.append(text)

                    if evt_type == "text":
                        content = data.get("content", "")
                        if isinstance(content, str) and len(content) > 10:
                            print(f"DEBUG _parse: text content preview={content[:200]}...")
                            full_content.append(content)
                        elif isinstance(content, dict):
                            text = content.get("text", "")
                            if text:
                                full_content.append(text)
                        part = data.get("part", {})
                        if isinstance(part, dict):
                            text = part.get("text", "")
                            if text and len(text) > 10:
                                print(f"DEBUG _parse: text from part preview={text[:200]}...")
                                full_content.append(text)
                            
                    if evt_type == "step_finish":
                        content = data.get("content", "")
                        if isinstance(content, str) and content.strip():
                            print(f"DEBUG _parse: step_finish content length={len(content)}")
                            full_content.append(content)
                    
                    if evt_type == "tool_use":
                        # tool_use events may contain command info
                        tool_name = data.get("name", "")
                        tool_input = data.get("input", {})
                        print(f"DEBUG _parse: tool_use name={tool_name}, input={tool_input}")
                        # If it's a command execution tool, extract command
                        if tool_name == "bash" or tool_name == "command":
                            cmd = tool_input.get("command", "") or tool_input.get("cmd", "")
                            if cmd:
                                full_content.append(cmd)
                        # Store raw input for inspection
                        if tool_input:
                            full_content.append(str(tool_input))
                except json.JSONDecodeError:
                    continue

            if full_content:
                combined = "\n".join(full_content)
                print(f"DEBUG _parse: extracted {len(full_content)} blocks, combined length={len(combined)}")
                print(f"DEBUG _parse: combined preview: {combined[:500]}")
                return combined

            print(f"DEBUG _parse: no content extracted, returning original output (length={len(output)})")
            return output

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
    system_prompt = """你是一个专业的 3D 建模专家，使用 CLI-Anything 命令在 Blender 中创建模型。

**核心规则**：
1. **绝对禁止**生成 Python 脚本或任何代码
2. **绝对禁止**使用 bash、shell、python、blender 等工具
3. **只允许**输出纯文本的 CLI-Anything 命令
4. **不要**使用任何工具调用，只输出纯文本

**违规示例（绝对禁止）**：
- import bpy; bpy.ops.mesh.primitive_cylinder_add(...)
- blender --background --python script.py
- bash ... python ...
- 任何 Python、JavaScript、Shell 代码

**CLI-Anything 命令格式**：
- scene new --name SceneName
- object add cube --name CubeName --location 0,0,0 --scale 1,1,1
- object add cylinder --name CylinderName --location 0,0,0 --param "radius=1" --param "depth=2"
- object add sphere --name SphereName --location 0,0,0 --param "radius=1"
- material create --name RedMat --color 1,0,0,1 --metallic 0.5 --roughness 0.5
- object set-material --object CylinderName --material RedMat

**命令前缀白名单**：scene, object, material, modifier, light, camera, animation, render, session, preview

**正确输出示例**：
用户: 创建一个红色圆柱体
输出:
scene new --name red_cylinder
object add cylinder --name Cylinder --location 0,0,0 --param "radius=1" --param "depth=2"
material create --name Red --color 1,0,0,1
object set-material --object Cylinder --material Red

用户: 做一个机器人
输出:
scene new --name robot
object add cube --name body --location 0,1,0 --scale 1,2,1
object add sphere --name head --location 0,3.5,0 --scale 0.6
material create --name Metal --color 0.8,0.8,0.9,1 --metallic 1.0 --roughness 0.2
object set-material --object body --material Metal
object set-material --object head --material Metal

**最终规则**：只输出 CLI-Anything 命令，每行一条，不要任何解释，不要任何工具调用。
"""
    messages = [{"role": "system", "content": system_prompt}]

    if chat_history:
        for entry in chat_history[-10:]:
            messages.append({"role": entry.get("role", "user"), "content": entry.get("content", "")})

    messages.append({"role": "user", "content": user_input})
    return messages
