"""Mesh conversion utilities."""

import bpy
import numpy as np
from typing import List, Tuple, Optional, Dict, Any


def create_blender_mesh(
    vertices: List[List[float]],
    faces: List[List[int]],
    vertex_colors: Optional[List[List[float]]] = None,
    mesh_name: str = "AI_Mesh"
) -> bpy.types.Object:
    """Create a Blender mesh from vertices, faces, and optional vertex colors."""
    
    mesh = bpy.data.meshes.new(mesh_name)
    mesh.use_auto_smooth = True
    
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    
    if vertex_colors:
        color_layer = mesh.color_attributes.new(
            name="Col",
            type="BYTE_COLOR",
            domain="CORNER"
        )
        
        num_corners = sum(len(face) for face in faces)
        color_data = np.zeros(num_corners, dtype=np.float32)
        
        idx = 0
        for face_idx, face in enumerate(faces):
            for _ in face:
                for c in range(3):
                    color_data[idx * 3 + c] = vertex_colors[face_idx][c]
                color_data[idx * 3 + 3] = 255
                idx += 1
        
        color_layer.data[:].color = color_data.reshape(-1, 4)
    
    obj = bpy.data.objects.new(mesh_name, mesh)
    bpy.context.collection.objects.link(obj)
    
    return obj


def load_glb_model(file_path: str, mesh_name: str = "AI_Model") -> bpy.types.Object:
    """Load a GLB file as a Blender mesh."""
    bpy.ops.import_scene.gltf(filepath=file_path)
    
    imported_objects = [obj for obj in bpy.context.selected_objects]
    
    if not imported_objects:
        return None
    
    result = imported_objects[0]
    result.name = mesh_name
    
    for obj in imported_objects[1:]:
        if obj.type == 'MESH':
            obj.select_set(True)
        else:
            obj.select_set(False)
    
    if len(imported_objects) > 1:
        bpy.ops.object.join()
        result = bpy.context.active_object
        result.name = mesh_name
    
    return result


def apply_decimate(obj: bpy.types.Object, ratio: float = 0.1) -> bpy.types.Object:
    """Apply decimation modifier to reduce polygon count."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.001)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
    mod.ratio = ratio
    bpy.ops.object.modifier_apply(modifier="Decimate")
    
    return obj


def cleanup_mesh(obj: bpy.types.Object) -> bpy.types.Object:
    """Clean up mesh: remove doubles, delete loose, fix normals."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.001)
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return obj


def assign_vertex_color_material(obj: bpy.types.Object) -> bpy.types.Material:
    """Assign vertex color as material."""
    if not obj.data.color_attributes or len(obj.data.color_attributes) == 0:
        return None
    
    mat = bpy.data.materials.new(name="AI_VCol_Mat")
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    
    if bsdf:
        attr_node = mat.node_tree.nodes.new(type="ShaderNodeAttribute")
        attr_node.attribute_name = obj.data.color_attributes.active.name
        mat.node_tree.links.new(attr_node.outputs["Color"], bsdf.inputs["Base Color"])
    
    obj.data.materials.append(mat)
    
    return mat