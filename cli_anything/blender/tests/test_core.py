"""Unit tests for Blender CLI core modules.

Tests use synthetic data only - no real Blender or external dependencies.
"""

import json
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cli_anything.blender.core.scene import (
    create_scene, open_scene, save_scene, get_scene_info, list_profiles,
    PROFILES,
)
from cli_anything.blender.core.objects import (
    add_object, remove_object, duplicate_object, transform_object,
    set_object_property, get_object, list_objects, MESH_PRIMITIVES,
)
from cli_anything.blender.core.materials import (
    create_material, assign_material, set_material_property,
    get_material, list_materials,
)
from cli_anything.blender.core.modifiers import (
    list_available, get_modifier_info, add_modifier, remove_modifier,
    set_modifier_param, list_modifiers,
)
from cli_anything.blender.core.lighting import (
    add_light, set_light, add_camera, set_active_camera,
    list_lights, list_cameras,
)
from cli_anything.blender.core.session import Session


# ── Scene Tests ────────────────────────────────────────────────────

class TestScene:
    def test_create_default(self):
        scene = create_scene()
        assert scene["scene"]["resolution_x"] == 1920
        assert scene["scene"]["resolution_y"] == 1080
        assert scene["scene"]["engine"] == "CYCLES"
        assert scene["version"] == "1.0"

    def test_create_with_dimensions(self):
        scene = create_scene(name="test", resolution_x=1280, resolution_y=720, fps=30)
        assert scene["scene"]["resolution_x"] == 1280
        assert scene["scene"]["resolution_y"] == 720
        assert scene["scene"]["fps"] == 30

    def test_create_with_profile(self):
        scene = create_scene(profile="hd720p")
        assert scene["scene"]["resolution_x"] == 1280
        assert scene["scene"]["resolution_y"] == 720

    def test_create_invalid_engine(self):
        with pytest.raises(ValueError, match="Invalid render engine"):
            create_scene(engine="INVALID")

    def test_create_invalid_resolution(self):
        with pytest.raises(ValueError, match="Resolution must be positive"):
            create_scene(resolution_x=0, resolution_y=1080)

    def test_create_invalid_fps(self):
        with pytest.raises(ValueError, match="FPS must be positive"):
            create_scene(fps=0)

    def test_save_and_open(self):
        scene = create_scene(name="test_scene")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            save_scene(scene, path)
            loaded = open_scene(path)
            assert loaded["name"] == "test_scene"
            assert loaded["scene"]["resolution_x"] == 1920
        finally:
            os.unlink(path)

    def test_open_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            open_scene("/nonexistent/path.json")

    def test_get_info(self):
        scene = create_scene(name="info_test")
        info = get_scene_info(scene)
        assert info["name"] == "info_test"
        assert info["object_count"] == 0
        assert "scene" in info

    def test_list_profiles(self):
        profiles = list_profiles()
        assert len(profiles) > 0
        names = [p["name"] for p in profiles]
        assert "hd720p" in names
        assert "hd1080p" in names
        assert "4k" in names


# ── Object Tests ───────────────────────────────────────────────────

class TestObjects:
    def _make_scene(self):
        return create_scene()

    def test_add_cube(self):
        scene = self._make_scene()
        obj = add_object(scene, mesh_type="cube", name="TestCube")
        assert obj["name"] == "TestCube"
        assert obj["mesh_type"] == "cube"
        assert obj["location"] == [0, 0, 0]
        assert obj["id"] == 0

    def test_add_sphere(self):
        scene = self._make_scene()
        obj = add_object(scene, mesh_type="sphere", name="TestSphere")
        assert obj["name"] == "TestSphere"
        assert obj["mesh_type"] == "sphere"

    def test_add_with_location(self):
        scene = self._make_scene()
        obj = add_object(scene, mesh_type="cube", location=[1, 2, 3])
        assert obj["location"] == [1, 2, 3]

    def test_add_with_rotation(self):
        scene = self._make_scene()
        obj = add_object(scene, mesh_type="cube", rotation=[45, 0, 90])
        assert obj["rotation"] == [45, 0, 90]

    def test_add_with_scale(self):
        scene = self._make_scene()
        obj = add_object(scene, mesh_type="cube", scale=[2, 2, 2])
        assert obj["scale"] == [2, 2, 2]

    def test_add_invalid_mesh_type(self):
        scene = self._make_scene()
        with pytest.raises(ValueError, match="Unknown mesh type"):
            add_object(scene, mesh_type="invalid")

    def test_add_with_mesh_params(self):
        scene = self._make_scene()
        obj = add_object(scene, mesh_type="sphere", mesh_params={"radius": 2.0})
        assert obj["mesh_type"] == "sphere"

    def test_remove_object(self):
        scene = self._make_scene()
        add_object(scene, mesh_type="cube")
        add_object(scene, mesh_type="sphere")
        removed = remove_object(scene, 0)
        assert removed["name"] == "Cube"
        objects = list_objects(scene)
        assert len(objects) == 1

    def test_remove_invalid_index(self):
        scene = self._make_scene()
        with pytest.raises(IndexError):
            remove_object(scene, 99)

    def test_duplicate_object(self):
        scene = self._make_scene()
        add_object(scene, mesh_type="cube", name="Original")
        dup = duplicate_object(scene, 0)
        assert "Original" in dup["name"]
        assert dup["id"] == 1

    def test_transform_object(self):
        scene = self._make_scene()
        add_object(scene, mesh_type="cube")
        obj = transform_object(scene, 0, translate=[1, 1, 1], rotate=[90, 0, 0], scale=[2, 2, 2])
        assert obj["location"] == [1, 1, 1]
        assert obj["rotation"] == [90, 0, 0]
        assert obj["scale"] == [2, 2, 2]

    def test_set_object_property(self):
        scene = self._make_scene()
        add_object(scene, mesh_type="cube")
        set_object_property(scene, 0, "name", "Renamed")
        obj = get_object(scene, 0)
        assert obj["name"] == "Renamed"

    def test_set_object_location(self):
        scene = self._make_scene()
        add_object(scene, mesh_type="cube")
        set_object_property(scene, 0, "location", [5, 5, 5])
        obj = get_object(scene, 0)
        assert obj["location"] == [5, 5, 5]

    def test_list_objects(self):
        scene = self._make_scene()
        add_object(scene, mesh_type="cube")
        add_object(scene, mesh_type="sphere")
        objects = list_objects(scene)
        assert len(objects) == 2

    def test_get_object(self):
        scene = self._make_scene()
        add_object(scene, mesh_type="cube", name="TestObj")
        obj = get_object(scene, 0)
        assert obj["name"] == "TestObj"

    def test_unique_ids(self):
        scene = self._make_scene()
        add_object(scene, mesh_type="cube")
        add_object(scene, mesh_type="sphere")
        add_object(scene, mesh_type="cylinder")
        ids = [get_object(scene, i)["id"] for i in range(3)]
        assert len(set(ids)) == 3


# ── Material Tests ──────────────────────────────────────────────────

class TestMaterials:
    def _make_scene(self):
        return create_scene()

    def test_create_material_default(self):
        scene = self._make_scene()
        mat = create_material(scene, name="TestMat")
        assert mat["name"] == "TestMat"
        assert mat["roughness"] == 0.5
        assert mat["metallic"] == 0.0

    def test_create_material_with_color(self):
        scene = self._make_scene()
        mat = create_material(scene, name="RedMat", color=[1, 0, 0, 1])
        assert mat["color"] == [1, 0, 0, 1]

    def test_create_material_with_properties(self):
        scene = self._make_scene()
        mat = create_material(scene, name="MetalMat", metallic=0.9, roughness=0.2)
        assert mat["metallic"] == 0.9
        assert mat["roughness"] == 0.2

    def test_assign_material(self):
        scene = self._make_scene()
        add_object(scene, mesh_type="cube")
        create_material(scene, name="Mat")
        result = assign_material(scene, 0, 0)
        assert result["material"] == "Mat"
        assert result["object"] == "Cube"

    def test_set_material_property(self):
        scene = self._make_scene()
        create_material(scene, name="Mat")
        set_material_property(scene, 0, "color", [0.5, 0.5, 0.5, 1.0])
        mat = get_material(scene, 0)
        assert mat["color"] == [0.5, 0.5, 0.5, 1.0]

    def test_list_materials(self):
        scene = self._make_scene()
        create_material(scene, name="Mat1")
        create_material(scene, name="Mat2")
        mats = list_materials(scene)
        assert len(mats) == 2

    def test_get_material(self):
        scene = self._make_scene()
        create_material(scene, name="TestMat")
        mat = get_material(scene, 0)
        assert mat["name"] == "TestMat"


# ── Modifier Tests ─────────────────────────────────────────────────

class TestModifiers:
    def _make_scene(self):
        scene = create_scene()
        add_object(scene, mesh_type="cube")
        return scene

    def test_list_available(self):
        mods = list_available()
        assert len(mods) > 0
        names = [m["name"] for m in mods]
        assert "subdivision" in names
        assert "bevel" in names

    def test_list_available_by_category(self):
        generate_mods = list_available(category="generate")
        assert all(m["category"] == "generate" for m in generate_mods)

    def test_get_modifier_info(self):
        info = get_modifier_info("subdivision")
        assert info["name"] == "subdivision"
        assert "category" in info

    def test_add_modifier(self):
        scene = self._make_scene()
        result = add_modifier(scene, "subdivision", object_index=0)
        assert result["modifier_type"] == "subdivision"
        assert result["name"] == "Subdivision"

    def test_add_modifier_with_params(self):
        scene = self._make_scene()
        result = add_modifier(scene, "bevel", object_index=0, params={"width": 0.05})
        assert result["params"]["width"] == 0.05

    def test_remove_modifier(self):
        scene = self._make_scene()
        add_modifier(scene, "subdivision", object_index=0)
        result = remove_modifier(scene, 0, object_index=0)
        assert "removed" in result

    def test_set_modifier_param(self):
        scene = self._make_scene()
        add_modifier(scene, "bevel", object_index=0)
        set_modifier_param(scene, 0, "width", 0.1, object_index=0)
        mods = list_modifiers(scene, object_index=0)
        assert mods[0]["params"]["width"] == 0.1

    def test_list_modifiers(self):
        scene = self._make_scene()
        add_modifier(scene, "subdivision", object_index=0)
        add_modifier(scene, "bevel", object_index=0)
        mods = list_modifiers(scene, object_index=0)
        assert len(mods) == 2


# ── Lights and Cameras Tests ────────────────────────────────────────

class TestLightsAndCameras:
    def _make_scene(self):
        return create_scene()

    def test_add_point_light(self):
        scene = self._make_scene()
        lt = add_light(scene, light_type="POINT", name="PointLight")
        assert lt["name"] == "PointLight"
        assert lt["type"] == "POINT"

    def test_add_sun_light(self):
        scene = self._make_scene()
        lt = add_light(scene, light_type="SUN", name="SunLight")
        assert lt["type"] == "SUN"

    def test_add_spot_light(self):
        scene = self._make_scene()
        lt = add_light(scene, light_type="SPOT", name="SpotLight")
        assert lt["type"] == "SPOT"

    def test_add_area_light(self):
        scene = self._make_scene()
        lt = add_light(scene, light_type="AREA", name="AreaLight")
        assert lt["type"] == "AREA"

    def test_add_light_with_location(self):
        scene = self._make_scene()
        lt = add_light(scene, light_type="POINT", location=[5, 5, 5])
        assert lt["location"] == [5, 5, 5]

    def test_set_light_property(self):
        scene = self._make_scene()
        add_light(scene, light_type="POINT", name="Light")
        set_light(scene, 0, "energy", 100.0)
        lt = list_lights(scene)[0]
        assert lt["energy"] == 100.0

    def test_add_camera(self):
        scene = self._make_scene()
        cam = add_camera(scene, name="MainCamera")
        assert cam["name"] == "MainCamera"

    def test_add_camera_with_location(self):
        scene = self._make_scene()
        cam = add_camera(scene, location=[5, 5, 3])
        assert cam["location"] == [5, 5, 3]


# ── Session Tests ───────────────────────────────────────────────────

class TestSession:
    def test_create_session(self):
        session = Session()
        assert session is not None

    def test_session_set_project(self):
        session = Session()
        proj = create_scene(name="test")
        session.set_project(proj, None)
        assert session.get_project()["name"] == "test"

    def test_session_undo_redo(self):
        session = Session()
        proj = create_scene(name="test")
        session.set_project(proj, None)

        scene = session.get_project()
        add_object(scene, mesh_type="cube")
        session.snapshot("add cube")

        scene = session.get_project()
        assert len(scene["objects"]) == 1

        session.undo()
        scene = session.get_project()
        assert len(scene["objects"]) == 0

        session.redo()
        scene = session.get_project()
        assert len(scene["objects"]) == 1

    def test_undo_empty_stack(self):
        session = Session()
        result = session.undo()
        assert result is None

    def test_redo_empty_stack(self):
        session = Session()
        result = session.redo()
        assert result is None

    def test_new_snapshot_clears_redo(self):
        session = Session()
        proj = create_scene()
        session.set_project(proj, None)

        add_object(proj, mesh_type="cube")
        session.snapshot("add 1")

        session.undo()
        session.get_project()

        add_object(proj, mesh_type="sphere")
        session.snapshot("add 2")

        assert len(session.list_history()) == 2

    def test_session_status(self):
        session = Session()
        proj = create_scene()
        session.set_project(proj, None)
        status = session.status()
        assert "has_project" in status

    def test_save_session(self):
        session = Session()
        proj = create_scene(name="save_test")
        session.set_project(proj, None)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            saved = session.save_session(path)
            assert os.path.exists(saved)
        finally:
            os.unlink(path)

    def test_list_history(self):
        session = Session()
        proj = create_scene()
        session.set_project(proj, None)

        add_object(proj, mesh_type="cube")
        session.snapshot("add cube")

        history = session.list_history()
        assert len(history) == 1
        assert history[0]["description"] == "add cube"
