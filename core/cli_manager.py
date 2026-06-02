"""CLI-Anything 子进程管理器 - 用于在 Blender 内调用 CLI-Anything."""

import subprocess
import json
import sys
import os
import tempfile
import shlex


class CLIAnythingManager:
    """管理 CLI-Anything 子进程"""

    def __init__(self, project_path: str = None):
        self.project_path = os.path.abspath(project_path or tempfile.gettempdir())
        self.project_file = None  # Will be set when scene is created
        self.cli_path = self._find_cli_path()
        self.session = None
        self._ensure_cli_anything()
    
    def _ensure_cli_anything(self) -> bool:
        """确保 CLI-Anything 已安装"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "cli_anything.blender.blender_cli", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True
        except:
            pass
        
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://pypi.org/pypi/cli-anything/json",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                pass
            install_cmd = [sys.executable, "-m", "pip", "install", "cli-anything"]
            subprocess.run(install_cmd, check=True, capture_output=True)
            return True
        except Exception as e:
            print(f"Failed to install cli-anything: {e}")
            return False
    
    def _find_cli_path(self) -> str:
        """查找 CLI-Anything 可执行文件"""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "cli_anything", "blender", "__main__.py"),
            os.path.join(sys.exec_prefix, "Scripts", "cli-anything-blender.exe"),
            "C:\\Users\\Administrator\\AppData\\Roaming\\Blender Foundation\\Blender\\5.1\\scripts\\addons\\CLI-Anything-Blender\\cli_anything\\blender\\__main__.py",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return sys.executable + ' "' + path + '"'
        
        return sys.executable + ' -m cli_anything.blender.blender_cli'
    
    def execute_command(self, command: str, timeout: int = 60) -> dict:
        """执行单条 CLI 命令，返回 JSON 结果"""
        cmd_parts = shlex.split(command)  # Use shlex to properly handle quoted args

        # Normalize command options: convert underscore_options to hyphen-options
        import re
        normalized_parts = []
        for part in cmd_parts:
            if part.startswith('--'):
                # Replace all underscores after -- with hyphens
                part = re.sub(r'^--(.+)$', lambda m: '--' + m.group(1).replace('_', '-'), part)
            normalized_parts.append(part)
        cmd_parts = normalized_parts

        # Auto-fix argument order for material assign: swap if first arg looks like object name and second like material name
        if len(cmd_parts) >= 3 and cmd_parts[0] == 'material' and cmd_parts[1] == 'assign' and len(cmd_parts) == 4:
            arg1, arg2 = cmd_parts[2], cmd_parts[3]
            if self.project_file and os.path.exists(self.project_file):
                try:
                    with open(self.project_file, 'r', encoding='utf-8') as f:
                        proj = json.load(f)
                    obj_names = [o.get('name', '').lower() for o in proj.get('objects', [])]
                    mat_names = [m.get('name', '').lower() for m in proj.get('materials', [])]
                    if arg1.lower() in obj_names and arg2.lower() in mat_names:
                        cmd_parts = cmd_parts[:2] + [arg2, arg1]
                except Exception:
                    pass

        # Find local cli_anything path - go up from core/ to project root, then to cli_anything/blender/
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_cli = os.path.join(project_root, "cli_anything", "blender", "__main__.py")

        # Build environment with PYTHONPATH set to project root to ensure local version is used
        # Also set PYTHONHOME to prevent Python from loading from wrong installation
        env = os.environ.copy()
        env['PYTHONPATH'] = project_root
        env['PYTHONHOME'] = os.path.dirname(sys.executable)
        env['PYTHONNOUSERSITE'] = '1'

        # Check if this is a scene new command with --output
        if "scene new" in command and "--output" in command:
            # scene new with output - don't use --project, let it create fresh
            cmd = [sys.executable, local_cli, "--json"] + cmd_parts
        elif self.project_file and os.path.exists(self.project_file):
            # Use existing project file
            cmd = [sys.executable, local_cli, "--project", self.project_file, "--json"] + cmd_parts
        else:
            cmd = [sys.executable, local_cli, "--json"] + cmd_parts

        try:
            result = subprocess.run(
                cmd,
                shell=False,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
                cwd=self.project_path,
                env=env
            )

            # After scene new with output succeeds, set project file path
            if "scene new" in command and "--output" in command and result.returncode == 0:
                # Extract output path from command
                try:
                    output_path = self._extract_output_path(command)
                    if output_path:
                        self.project_file = output_path
                except Exception:
                    pass

            if result.returncode == 0 and result.stdout.strip():
                try:
                    return {"success": True, "data": json.loads(result.stdout)}
                except json.JSONDecodeError:
                    return {"success": True, "output": result.stdout}
            else:
                return {"success": False, "error": result.stderr or f"命令执行失败 (code {result.returncode})"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"命令执行超时 ({timeout}s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_output_path(self, command: str) -> str:
        """Extract --output path from command string, returning absolute path"""
        parts = shlex.split(command)
        for i, part in enumerate(parts):
            if part == "--output" or part == "-o":
                if i + 1 < len(parts):
                    return os.path.abspath(parts[i + 1])
        return None

    def _save_project(self) -> None:
        """保存当前项目到文件"""
        if not self.project_file:
            self.project_file = os.path.abspath(os.path.join(self.project_path, "cli_anything_project.json"))
        # Execute scene save command with path
        cmd = [sys.executable, "-m", "cli_anything.blender.blender_cli", "--project", self.project_file, "scene", "save", self.project_file]
        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
        except Exception:
            pass
    
    def execute_commands(self, commands: list, timeout: int = 120) -> list:
        """批量执行命令，返回结果列表"""
        results = []
        for cmd in commands:
            result = self.execute_command(cmd, timeout=timeout)
            results.append({"command": cmd, "result": result})
        return results
    
    def scene_new(self, name: str = "BlenderScene") -> dict:
        """创建新场景"""
        # Set project file path with absolute path
        self.project_file = os.path.abspath(os.path.join(self.project_path, f"{name.replace(' ', '_')}_project.json"))
        # Use --output to save the scene file immediately
        return self.execute_command(f'scene new --name "{name}" --output "{self.project_file}"')
    
    def scene_info(self) -> dict:
        """获取场景信息"""
        return self.execute_command("scene info")
    
    def object_add(self, obj_type: str, name: str = None, location: str = "0,0,0", scale: str = None, **kwargs) -> dict:
        """添加对象"""
        cmd = f"object add {obj_type} --location {location}"
        if name:
            cmd += f' --name "{name}"'
        if scale:
            cmd += f" --scale {scale}"
        for key, value in kwargs.items():
            cmd += f" --{key} {value}"
        return self.execute_command(cmd)
    
    def material_create(self, name: str, color: str = "1,1,1,1", **kwargs) -> dict:
        """创建材质"""
        cmd = f'material create --name "{name}" --color {color}'
        for key, value in kwargs.items():
            cmd += f" --{key} {value}"
        return self.execute_command(cmd)
    
    def object_set_material(self, obj_name: str, mat_name: str) -> dict:
        """设置对象材质"""
        return self.execute_command(f'object set-material --object "{obj_name}" --material "{mat_name}"')
    
    def render_execute(self, output_path: str = None) -> dict:
        """执行渲染"""
        cmd = "render execute"
        if output_path:
            cmd += f' --output "{output_path}"'
        return self.execute_command(cmd, timeout=300)
    
    def run_repl_command(self, user_input: str, timeout: int = 60) -> dict:
        """在 REPL 模式下执行命令"""
        cmd = f'echo "{user_input}" | {sys.executable} -m cli_anything.blender.blender_cli repl --json'
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_path
            )
            if result.returncode == 0:
                return {"success": True, "output": result.stdout}
            else:
                return {"success": False, "error": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}


_cli_manager = None


def get_cli_manager() -> CLIAnythingManager:
    """获取全局 CLI 管理器实例"""
    global _cli_manager
    if _cli_manager is None:
        _cli_manager = CLIAnythingManager()
    return _cli_manager
