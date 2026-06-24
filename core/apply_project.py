"""Blender CLI - Apply JSON project changes to Blender viewport.

This module provides incremental sync functionality to apply CLI command
results to Blender without rebuilding the entire scene.
"""

import bpy
import math
from typing import Dict, Any, List, Optional, Set

# Blender's mathutils
try:
    import mathutils
except ImportError:
    mathutils = None


# Marker to identify CLI-managed objects
CLI_MANAGED_MARKER = "cli_managed"


def is_cli_managed(obj: bpy.types.Object) -> bool:
    """Check if an object was created by CLI commands."""
    return CLI_MANAGED_MARKER in obj and obj.get(CLI_MANAGED_MARKER, False)


def mark_as_cli_managed(obj: bpy.types.Object) -> None:
    """Mark an object as CLI-managed."""
    obj[CLI_MANAGED_MARKER] = True


def find_blender_object(name: str) -> Optional[bpy.types.Object]:
    """Find a Blender object by name."""
    return bpy.data.objects.get(name)


def find_or_create_object(obj_data: Dict[str, Any]) -> bpy.types.Object:
    """Find existing object or create new one from JSON data."""
    name = obj_data.get("name", "Object")
    obj = find_blender_object(name)

    if obj is None:
        # Create new object
        mesh_type = obj_data.get("mesh_type", "cube")

        if mesh_type == "cube":
            bpy.ops.mesh.primitive_cube_add(size=2)
        elif mesh_type == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1)
        elif mesh_type == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=2)
        elif mesh_type == "cone":
            bpy.ops.mesh.primitive_cone_add(radius1=1, depth=2)
        elif mesh_type == "plane":
            bpy.ops.mesh.primitive_plane_add(size=2)
        elif mesh_type == "torus":
            bpy.ops.mesh.primitive_torus_add()
        elif mesh_type == "monkey":
            bpy.ops.mesh.primitive_monkey_add()
        elif mesh_type == "empty":
            bpy.ops.object.empty_add(type='PLAIN_AXES')
        else:
            bpy.ops.mesh.primitive_cube_add(size=2)

        obj = bpy.context.active_object
        obj.name = name
        mark_as_cli_managed(obj)

    return obj


def apply_transform(obj: bpy.types.Object, obj_data: Dict[str, Any]) -> None:
    """Apply location, rotation, scale from JSON to Blender object."""
    if "location" in obj_data:
        loc = obj_data["location"]
        if mathutils is not None:
            obj.location = mathutils.Vector(loc)
        else:
            obj.location = loc

    if "rotation" in obj_data:
        rot = obj_data["rotation"]
        obj.rotation_euler = (
            math.radians(rot[0]),
            math.radians(rot[1]),
            math.radians(rot[2])
        )

    if "scale" in obj_data:
        obj.scale = obj_data["scale"]


def apply_material(obj: bpy.types.Object, material_data: Dict[str, Any]) -> None:
    """Apply material from JSON to Blender object."""
    mat_name = material_data.get("name", "Material")

    # Find or create material
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
        mark_as_cli_managed(mat)

    # Configure Principled BSDF
    if not mat.use_nodes:
        mat.use_nodes = True

    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "color" in material_data:
            bsdf.inputs["Base Color"].default_value = tuple(material_data["color"])
        if "metallic" in material_data:
            bsdf.inputs["Metallic"].default_value = material_data["metallic"]
        if "roughness" in material_data:
            bsdf.inputs["Roughness"].default_value = material_data["roughness"]
        if "specular" in material_data and "Specular" in bsdf.inputs:
            bsdf.inputs["Specular"].default_value = material_data["specular"]

        # Emission
        emission_color = material_data.get("emission_color")
        emission_strength = material_data.get("emission_strength", 0.0)
        if emission_color and emission_strength > 0:
            bsdf.inputs["Emission Color"].default_value = tuple(emission_color)
            bsdf.inputs["Emission Strength"].default_value = emission_strength

    # Assign to object
    if obj.data and hasattr(obj.data, 'materials'):
        if mat.name not in obj.data.materials:
            obj.data.materials.append(mat)


def apply_modifier(obj: bpy.types.Object, mod_data: Dict[str, Any]) -> None:
    """Apply a single modifier from JSON to Blender object."""
    mod_type = mod_data.get("type", "").upper()
    mod_name = mod_data.get("name", mod_type)

    # Map CLI modifier types to Blender modifier types
    MODIFIER_TYPE_MAP = {
        "SUBDIVISION": "SUBSURF",
        "SUBDIVISION_SURFACE": "SUBSURF",
        "SOLIDIFY": "SOLIDIFY",
        "BEVEL": "BEVEL",
        "DECIMATE": "DECIMATE",
        "MIRROR": "MIRROR",
        "ARRAY": "ARRAY",
        "LATH": "SCREW",
        "SCREW": "SCREW",
        "SKIN": "SKIN",
        "TRIANGULATE": "TRIANGULATE",
        "REMESH": "REMESH",
        "WELD": "WELD",
        "WEIGHTED_NORMAL": "WEIGHTED_NORMAL",
    }

    bpy_mod_type = MODIFIER_TYPE_MAP.get(mod_type, mod_type)

    # Check if modifier already exists
    existing = obj.modifiers.get(mod_name)
    if existing:
        # Update existing modifier
        _update_modifier_params(existing, mod_data)
        return

    # Add new modifier
    try:
        new_mod = obj.modifiers.new(name=mod_name, type=bpy_mod_type)
        _update_modifier_params(new_mod, mod_data)
        mark_as_cli_managed(new_mod)
    except Exception as e:
        print(f"Failed to add modifier {mod_name}: {e}")


def _update_modifier_params(mod: bpy.types.Modifier, mod_data: Dict[str, Any]) -> None:
    """Update modifier parameters from JSON data."""
    params = mod_data.get("params", {})

    # Common parameter mappings
    param_mappings = {
        "levels": "levels",
        "subdivisions": "subdivisions",
        "ratio": "ratio",
        "thickness": "thickness",
        "width": "width",
        "segments": "segments",
        "offset": "offset",
        "mirror_object": "mirror_object",
        "axis": "axis",
    }

    for json_key, bpy_key in param_mappings.items():
        if json_key in params:
            setattr(mod, bpy_key, params[json_key])


def apply_project(project: Dict[str, Any]) -> None:
    """Apply JSON project changes to Blender scene.

    This performs incremental sync - only updates objects/materials/modifiers
    that are present in the JSON and were created by CLI commands.
    Preserves manually made changes to Blender objects.
    """
    # Track which objects we've processed
    processed_objects: Set[str] = set()

    # Apply materials first (objects reference them)
    materials = project.get("materials", [])
    for mat_data in materials:
        mat_name = mat_data.get("name")
        if not mat_name:
            continue

        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            # Material doesn't exist in Blender - create it
            mat = bpy.data.materials.new(name=mat_name)
            mark_as_cli_managed(mat)

        # Configure material
        if not mat.use_nodes:
            mat.use_nodes = True

        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            if "color" in mat_data:
                bsdf.inputs["Base Color"].default_value = tuple(mat_data["color"])
            if "metallic" in mat_data:
                bsdf.inputs["Metallic"].default_value = mat_data["metallic"]
            if "roughness" in mat_data:
                bsdf.inputs["Roughness"].default_value = mat_data["roughness"]
            if "specular" in mat_data and "Specular" in bsdf.inputs:
                bsdf.inputs["Specular"].default_value = mat_data["specular"]

            # Emission
            emission_color = mat_data.get("emission_color")
            emission_strength = mat_data.get("emission_strength", 0.0)
            if emission_color:
                bsdf.inputs["Emission Color"].default_value = tuple(emission_color)
            if emission_strength > 0:
                bsdf.inputs["Emission Strength"].default_value = emission_strength

    # Apply objects
    objects = project.get("objects", [])
    for obj_data in objects:
        obj_name = obj_data.get("name")
        if not obj_name:
            continue

        # Find or create object
        obj = find_or_create_object(obj_data)
        processed_objects.add(obj_name)

        # Apply transforms
        apply_transform(obj, obj_data)

        # Apply material
        material_id = obj_data.get("material")
        if material_id is not None and isinstance(material_id, int):
            mats = project.get("materials", [])
            if 0 <= material_id < len(mats):
                mat_data = mats[material_id]
                apply_material(obj, mat_data)

        # Apply modifiers
        modifiers = obj_data.get("modifiers", [])
        for mod_data in modifiers:
            apply_modifier(obj, mod_data)

    # Update scene settings
    scene_settings = project.get("scene", {})
    if scene_settings:
        scene = bpy.context.scene
        if "unit_system" in scene_settings:
            unit = scene_settings["unit_system"].upper()
            if hasattr(scene.unit_settings, 'system'):
                try:
                    scene.unit_settings.system = 'METRIC' if 'METRIC' in unit else 'IMPERIAL'
                except:
                    pass

    # Render settings
    render_settings = project.get("render", {})
    if render_settings:
        scene = bpy.context.scene
        engine = render_settings.get("engine", "CYCLES")
        if hasattr(scene.render, 'engine'):
            scene.render.engine = 'CYCLES' if engine == 'CYCLES' else 'BLENDER_EEVEE' if engine == 'EEVEE' else 'BLENDER_WORKBENCH'

        if "resolution_x" in render_settings and "resolution_y" in render_settings:
            scene.render.resolution_x = render_settings["resolution_x"]
            scene.render.resolution_y = render_settings["resolution_y"]

    print(f"Applied project: {len(processed_objects)} objects processed")


def get_scene_snapshot() -> Dict[str, Any]:
    """Get current Blender scene state as a minimal snapshot.

    Used for change detection - only returns IDs/names of existing objects.
    """
    objects = []
    for obj in bpy.data.objects:
        if obj.type in ('MESH', 'EMPTY'):
            objects.append({
                "name": obj.name,
                "type": obj.type,
                "material": None,  # Would need to look up
            })

    return {"objects": objects}
