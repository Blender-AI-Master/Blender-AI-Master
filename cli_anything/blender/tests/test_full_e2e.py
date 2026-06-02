"""End-to-end tests for Blender CLI.

Tests require Blender to be installed for full rendering tests.
Without Blender, script generation tests will still pass.
"""

import json
import os
import subprocess
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cli_anything.blender.core.scene import (
    create_scene, open_scene, save_scene, get_scene_info,
)
from cli_anything.blender.core.objects import (
    add_object, list_objects, get_object,
)
from cli_anything.blender.core.materials import (
    create_material, assign_material,
)
from cli_anything.blender.core.render import generate_bpy_script
from cli_anything.blender.utils.blender_backend import find_blender, get_version


BLENDER_AVAILABLE = True
try:
    find_blender()
except RuntimeError:
    BLENDER_AVAILABLE = False


def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev."""
    import shutil
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-anything-", "cli_anything.") + "." + name.split("-")[-1] + "_cli"
    return [sys.executable, "-m", module]


CLI_BASE = _resolve_cli("cli-anything-blender")


def _run(args, check=True):
    return subprocess.run(
        CLI_BASE + args,
        capture_output=True,
        text=True,
        check=check,
    )


# ── Scene Workflow Tests ────────────────────────────────────────────

class TestSceneWorkflow:
    def test_create_save_open_roundtrip(self, tmp_path):
        path = tmp_path / "test_scene.json"
        scene = create_scene(name="roundtrip_test")
        save_scene(scene, str(path))
        loaded = open_scene(str(path))
        assert loaded["name"] == "roundtrip_test"
        assert loaded["scene"]["resolution_x"] == 1920

    def test_scene_with_objects_survives_roundtrip(self, tmp_path):
        path = tmp_path / "scene_with_objs.json"
        scene = create_scene(name="with_objects")
        add_object(scene, mesh_type="cube", name="Cube1")
        add_object(scene, mesh_type="sphere", name="Sphere1")
        save_scene(scene, str(path))
        loaded = open_scene(str(path))
        objs = list_objects(loaded)
        assert len(objs) == 2

    def test_scene_info_reflects_additions(self):
        scene = create_scene(name="info_test")
        add_object(scene, mesh_type="cube")
        add_object(scene, mesh_type="sphere")
        info = get_scene_info(scene)
        assert info["object_count"] == 2


# ── Object Operations Tests ────────────────────────────────────────

class TestObjectOperations:
    def test_add_various_mesh_types(self):
        scene = create_scene()
        for mesh_type in ["cube", "sphere", "cylinder", "cone", "plane", "torus"]:
            obj = add_object(scene, mesh_type=mesh_type)
            assert obj["mesh_type"] == mesh_type

    def test_multiple_objects_maintain_order(self):
        scene = create_scene()
        add_object(scene, mesh_type="cube", name="First")
        add_object(scene, mesh_type="sphere", name="Second")
        add_object(scene, mesh_type="cylinder", name="Third")
        objs = list_objects(scene)
        assert objs[0]["name"] == "First"
        assert objs[1]["name"] == "Second"
        assert objs[2]["name"] == "Third"


# ── Render Pipeline Tests ───────────────────────────────────────────

class TestRenderPipeline:
    def test_generate_bpy_script_contains_commands(self, tmp_path):
        scene = create_scene(name="render_test")
        add_object(scene, mesh_type="cube", name="TestCube")
        create_material(scene, name="RedMat", color=[1, 0, 0, 1])

        output_path = str(tmp_path / "render.py")
        script = generate_bpy_script(scene, output_path)

        assert "Cube" in script or "bpy.ops.mesh.primitive_cube_add()" in script

    def test_generate_bpy_script_with_material(self, tmp_path):
        scene = create_scene()
        add_object(scene, mesh_type="cube")
        create_material(scene, name="TestMat", metallic=0.8)

        output_path = str(tmp_path / "render.py")
        script = generate_bpy_script(scene, output_path)

        assert "material" in script.lower() or "bpy.data.materials.new" in script

    @pytest.mark.skipif(not BLENDER_AVAILABLE, reason="Blender not installed")
    def test_blender_version_detected(self):
        version = get_version()
        assert "Blender" in version


# ── CLI Subprocess Tests ───────────────────────────────────────────

class TestCLISubprocess:
    def test_help(self):
        result = _run(["--help"], check=False)
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "help" in result.stdout.lower()

    def test_scene_new(self, tmp_path):
        path = tmp_path / "new_scene.json"
        result = _run(["scene", "new", "--name", "cli_test", "-o", str(path)], check=False)
        assert result.returncode == 0
        assert os.path.exists(path)

    def test_scene_new_json(self, tmp_path):
        result = _run(["--json", "scene", "new", "--name", "json_test"], check=False)
        assert result.returncode == 0
        try:
            data = json.loads(result.stdout)
            assert data["name"] == "json_test"
        except json.JSONDecodeError:
            pytest.fail(f"JSON output expected, got: {result.stdout}")

    def test_scene_profiles(self):
        result = _run(["scene", "profiles"], check=False)
        assert result.returncode == 0
        assert "hd720p" in result.stdout or "HD" in result.stdout

    def test_object_list_json(self):
        result = _run(["--json", "object", "list"], check=False)
        assert result.returncode == 0
        try:
            data = json.loads(result.stdout)
            assert isinstance(data, list)
        except json.JSONDecodeError:
            pytest.fail(f"JSON output expected, got: {result.stdout}")

    def test_material_list(self):
        result = _run(["material", "list"], check=False)
        assert result.returncode == 0

    def test_full_workflow_json(self, tmp_path):
        path = tmp_path / "workflow.json"
        _run(["scene", "new", "--name", "workflow_test", "-o", str(path)], check=False)
        result = _run(["--json", "--project", str(path), "object", "list"], check=False)
        assert result.returncode == 0


# ── Real World Workflow Tests ─────────────────────────────────────

class TestRealWorldWorkflows:
    def test_simple_chair_workflow(self, tmp_path):
        path = tmp_path / "chair.json"

        result = _run(["scene", "new", "--name", "ChairScene", "-o", str(path)], check=False)
        assert result.returncode == 0

        commands = [
            ["--project", str(path), "object", "add", "cube", "--name", "Seat", "--location", "0,0,0.5", "--scale", "1,1,0.1"],
            ["--project", str(path), "object", "add", "cube", "--name", "Backrest", "--location", "0,-0.5,1.2", "--scale", "1,0.1,1.5"],
            ["--project", str(path), "material", "create", "--name", "Oak", "--color", "0.55,0.35,0.2,1", "--roughness", "0.6"],
        ]

        for cmd in commands:
            result = _run(cmd, check=False)
            assert result.returncode == 0, f"Command failed: {' '.join(cmd)}\nError: {result.stderr}"

        result = _run(["--project", str(path), "--json", "object", "list"], check=False)
        assert result.returncode == 0

        try:
            data = json.loads(result.stdout)
            assert len(data) >= 2
        except json.JSONDecodeError:
            pytest.fail(f"JSON output expected, got: {result.stdout}")

    def test_material_assignment_workflow(self, tmp_path):
        path = tmp_path / "material_workflow.json"

        _run(["scene", "new", "--name", "MatTest", "-o", str(path)], check=False)
        _run(["--project", str(path), "object", "add", "sphere", "--name", "Ball"], check=False)
        _run(["--project", str(path), "material", "create", "--name", "RedMetal", "--color", "1,0,0,1", "--metallic", "0.9"], check=False)

        result = _run(["--project", str(path), "material", "assign", "0", "0"], check=False)
        assert result.returncode == 0

    def test_modifier_workflow(self, tmp_path):
        path = tmp_path / "modifier_workflow.json"

        _run(["scene", "new", "--name", "ModTest", "-o", str(path)], check=False)
        _run(["--project", str(path), "object", "add", "cube", "--name", "Box"], check=False)
        result = _run(["--project", str(path), "modifier", "add", "bevel", "--object", "0", "--param", "width=0.05"], check=False)
        assert result.returncode == 0
