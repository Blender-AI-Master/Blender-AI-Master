"""Blender CLI - Material management module."""

import copy
from typing import Dict, Any, List, Optional


# Default Principled BSDF material
DEFAULT_MATERIAL = {
    "type": "principled",
    "color": [0.8, 0.8, 0.8, 1.0],
    "metallic": 0.0,
    "roughness": 0.5,
    "specular": 0.5,
    "emission_color": [0.0, 0.0, 0.0, 1.0],
    "emission_strength": 0.0,
    "alpha": 1.0,
    "use_backface_culling": False,
}

# Valid material properties and their constraints
MATERIAL_PROPS = {
    "color": {"type": "color4", "description": "Base color [R, G, B, A] (0.0-1.0)"},
    "metallic": {"type": "float", "min": 0.0, "max": 1.0, "description": "Metallic factor"},
    "roughness": {"type": "float", "min": 0.0, "max": 1.0, "description": "Roughness factor"},
    "specular": {"type": "float", "min": 0.0, "max": 2.0, "description": "Specular factor"},
    "emission_color": {"type": "color4", "description": "Emission color [R, G, B, A]"},
    "emission_strength": {"type": "float", "min": 0.0, "max": 1000.0, "description": "Emission strength"},
    "alpha": {"type": "float", "min": 0.0, "max": 1.0, "description": "Alpha (opacity)"},
    "use_backface_culling": {"type": "bool", "description": "Enable backface culling"},
}


def _next_id(project: Dict[str, Any]) -> int:
    """Generate the next unique material ID."""
    materials = project.get("materials", [])
    existing_ids = [m.get("id", 0) for m in materials]
    return max(existing_ids, default=-1) + 1


def _unique_name(project: Dict[str, Any], base_name: str) -> str:
    """Generate a unique material name."""
    materials = project.get("materials", [])
    existing_names = {m.get("name", "") for m in materials}
    if base_name not in existing_names:
        return base_name
    counter = 1
    while f"{base_name}.{counter:03d}" in existing_names:
        counter += 1
    return f"{base_name}.{counter:03d}"


def create_material(
    project: Dict[str, Any],
    name: str = "Material",
    color: Optional[List[float]] = None,
    metallic: float = 0.0,
    roughness: float = 0.5,
    specular: float = 0.5,
    emission_color: Optional[List[float]] = None,
    emission_strength: float = 0.0,
) -> Dict[str, Any]:
    """Create a new Principled BSDF material.

    Args:
        project: The scene dict
        name: Material name
        color: Base color [R, G, B, A] (0.0-1.0 each)
        metallic: Metallic factor (0.0-1.0)
        roughness: Roughness factor (0.0-1.0)
        specular: Specular factor (0.0-2.0)
        emission_color: Emission color [R, G, B, A]
        emission_strength: Emission strength (0.0-1000.0)

    Returns:
        The new material dict
    """
    if color is not None:
        if len(color) < 3:
            raise ValueError(f"Color must have at least 3 components [R, G, B], got {len(color)}")
        if len(color) == 3:
            color = list(color) + [1.0]
        for i, c in enumerate(color):
            if not 0.0 <= c <= 1.0:
                raise ValueError(f"Color component {i} must be 0.0-1.0, got {c}")

    if emission_color is not None:
        if len(emission_color) < 3:
            raise ValueError(f"Emission color must have at least 3 components [R, G, B], got {len(emission_color)}")
        if len(emission_color) == 3:
            emission_color = list(emission_color) + [1.0]

    if not 0.0 <= emission_strength <= 1000.0:
        raise ValueError(f"Emission strength must be 0.0-1000.0, got {emission_strength}")

    if not 0.0 <= metallic <= 1.0:
        raise ValueError(f"Metallic must be 0.0-1.0, got {metallic}")
    if not 0.0 <= roughness <= 1.0:
        raise ValueError(f"Roughness must be 0.0-1.0, got {roughness}")
    if not 0.0 <= specular <= 2.0:
        raise ValueError(f"Specular must be 0.0-2.0, got {specular}")

    mat_name = _unique_name(project, name)

    mat = {
        "id": _next_id(project),
        "name": mat_name,
        "type": "principled",
        "color": color if color else list(DEFAULT_MATERIAL["color"]),
        "metallic": metallic,
        "roughness": roughness,
        "specular": specular,
        "emission_color": emission_color if emission_color else list(DEFAULT_MATERIAL["emission_color"]),
        "emission_strength": emission_strength,
        "alpha": 1.0,
        "use_backface_culling": False,
    }

    if "materials" not in project:
        project["materials"] = []
    project["materials"].append(mat)

    return mat


def _find_material_index(project: Dict[str, Any], name: str) -> int:
    """Find material index by name."""
    materials = project.get("materials", [])
    for i, mat in enumerate(materials):
        if mat.get("name") == name:
            return i
    raise ValueError(f"Material '{name}' not found")


def _find_object_index(project: Dict[str, Any], name: str) -> int:
    """Find object index by name."""
    objects = project.get("objects", [])
    for i, obj in enumerate(objects):
        if obj.get("name") == name:
            return i
    raise ValueError(f"Object '{name}' not found")


def assign_material(
    project: Dict[str, Any],
    material_index: int,
    object_index: int,
) -> Dict[str, Any]:
    """Assign a material to an object.

    Args:
        project: The scene dict
        material_index: Index of the material (can be int, str index, or str name)
        object_index: Index of the object (can be int, str index, or str name)

    Returns:
        Dict with assignment info
    """
    materials = project.get("materials", [])
    objects = project.get("objects", [])

    # Resolve first argument as material
    if isinstance(material_index, str):
        if material_index.isdigit():
            material_index = int(material_index)
        else:
            # Try to find by name
            try:
                material_index = _find_material_index(project, material_index)
            except ValueError as e:
                raise ValueError(f"Material '{material_index}' not found. Available materials: {[m['name'] for m in materials]}")

    # Resolve second argument as object
    if isinstance(object_index, str):
        if object_index.isdigit():
            object_index = int(object_index)
        else:
            try:
                object_index = _find_object_index(project, object_index)
            except ValueError as e:
                raise ValueError(f"Object '{object_index}' not found. Available objects: {[o['name'] for o in objects]}")

    if material_index < 0 or material_index >= len(materials):
        raise IndexError(f"Material index {material_index} out of range (0-{len(materials)-1})")
    if object_index < 0 or object_index >= len(objects):
        raise IndexError(f"Object index {object_index} out of range (0-{len(objects)-1})")

    mat = materials[material_index]
    obj = objects[object_index]
    obj["material"] = mat["id"]

    return {
        "material": mat["name"],
        "material_id": mat["id"],
        "object": obj["name"],
        "object_id": obj["id"],
    }


def set_material_property(
    project: Dict[str, Any],
    index: int,
    prop: str,
    value: Any,
) -> None:
    """Set a material property.

    Args:
        project: The scene dict
        index: Material index
        prop: Property name
        value: New value
    """
    materials = project.get("materials", [])
    if index < 0 or index >= len(materials):
        raise IndexError(f"Material index {index} out of range (0-{len(materials)-1})")

    mat = materials[index]

    if prop not in MATERIAL_PROPS:
        raise ValueError(
            f"Unknown material property: {prop}. Valid: {list(MATERIAL_PROPS.keys())}"
        )

    spec = MATERIAL_PROPS[prop]
    ptype = spec["type"]

    if ptype == "float":
        value = float(value)
        if "min" in spec and value < spec["min"]:
            raise ValueError(f"Property '{prop}' minimum is {spec['min']}, got {value}")
        if "max" in spec and value > spec["max"]:
            raise ValueError(f"Property '{prop}' maximum is {spec['max']}, got {value}")
        mat[prop] = value
    elif ptype == "color4":
        if isinstance(value, str):
            value = [float(x) for x in value.split(",")]
        if len(value) < 3:
            raise ValueError(f"Color must have at least 3 components, got {len(value)}")
        if len(value) == 3:
            value = list(value) + [1.0]
        for i, c in enumerate(value):
            if not 0.0 <= float(c) <= 1.0:
                raise ValueError(f"Color component {i} must be 0.0-1.0, got {c}")
        mat[prop] = [float(x) for x in value]
    elif ptype == "bool":
        mat[prop] = str(value).lower() in ("true", "1", "yes")
    else:
        mat[prop] = value


def get_material(project: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Get a material by index."""
    materials = project.get("materials", [])
    if index < 0 or index >= len(materials):
        raise IndexError(f"Material index {index} out of range (0-{len(materials)-1})")
    return materials[index]


def list_materials(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List all materials with summary info."""
    result = []
    for i, mat in enumerate(project.get("materials", [])):
        result.append({
            "index": i,
            "id": mat.get("id", i),
            "name": mat.get("name", f"Material {i}"),
            "type": mat.get("type", "principled"),
            "color": mat.get("color", [0.8, 0.8, 0.8, 1.0]),
            "metallic": mat.get("metallic", 0.0),
            "roughness": mat.get("roughness", 0.5),
            "specular": mat.get("specular", 0.5),
        })
    return result
