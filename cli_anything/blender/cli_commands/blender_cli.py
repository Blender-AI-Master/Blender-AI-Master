#!/usr/bin/env python3
"""Blender CLI - Command-line interface for Blender operations"""

import os
import sys
import json
import click
import subprocess

BLENDER_PATH = os.environ.get("BLENDER_PATH", "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe")
DEFAULT_RESOLUTION = 2048


def run_blender_script(script):
    """Run a Python script in Blender"""
    script_path = os.environ.get("TEMP", "/tmp") + "/blender_cli_script.py"
    with open(script_path, "w", encoding='utf-8') as f:
        f.write(script)
    cmd = [BLENDER_PATH, "--background", "--python", script_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


@click.group()
@click.version_option(version="5.1.1")
def cli():
    """Blender CLI - Automate Blender operations from command line"""
    pass


@cli.command()
@click.option("--method", type=click.Choice(["voxel", "decimate"]), default="voxel")
@click.option("--resolution", type=float, default=0.01, help="Voxel resolution")
@click.option("--ratio", type=float, default=0.5, help="Decimate ratio")
@click.option("--object", "-o", help="Target object name")
def remesh(method, resolution, ratio, object):
    """Apply remesh modifier"""
    obj_name = f'"{object}"' if object else "None"
    
    if method == "voxel":
        script = f"""
import bpy
obj = bpy.data.objects.get({obj_name}) if {obj_name} else bpy.context.active_object
if obj:
    mod = obj.modifiers.new(name="Voxel Remesh", type='REMESH')
    mod.mode = 'VOXEL'
    mod.voxel_size = {resolution}
    mod.adaptivity = 0.01
    mod.use_smooth_shade = False
    bpy.ops.object.modifier_apply(modifier="Voxel Remesh")
    print(f"VOXEL_REMESH_APPLIED:{{len(obj.data.polygons)}}")
else:
    print("ERROR: No object found")
"""
    else:
        script = f"""
import bpy
obj = bpy.data.objects.get({obj_name}) if {obj_name} else bpy.context.active_object
if obj:
    mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
    mod.ratio = {ratio}
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier="Decimate")
    print(f"DECIMATE_APPLIED:{{len(obj.data.polygons)}}")
else:
    print("ERROR: No object found")
"""
    result = run_blender_script(script)
    click.echo(result.stdout.strip())


@cli.command()
@click.option("--method", type=click.Choice(["smart", "unwrap"]), default="smart")
@click.option("--angle", type=float, default=66.0, help="Angle threshold")
def unwrap(method, angle):
    """Unwrap UV coordinates"""
    script = """
import bpy
obj = bpy.context.active_object
if obj:
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_threshold=66.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    print("UV_UNWRAP_COMPLETE")
else:
    print("ERROR: No active object")
"""
    result = run_blender_script(script)
    click.echo(result.stdout.strip())


@cli.command()
@click.option("--file", "-f", required=True, help="Output file path")
@click.option("--format", type=click.Choice(["glb", "gltf", "fbx"]), default="glb")
@click.option("--selection/--no-selection", default=False, help="Export selection only")
def export(file, format, selection):
    """Export scene to file"""
    use_sel = "True" if selection else "False"
    
    if format == "fbx":
        script = f"""
import bpy
bpy.ops.export_scene.fbx(filepath="{file}", use_selection={use_sel})
print("EXPORT_SUCCESS:{file}")
"""
    else:
        script = f"""
import bpy
bpy.ops.export_scene.gltf(filepath="{file}", use_selection={use_sel}, export_format='GLB')
print("EXPORT_SUCCESS:{file}")
"""
    result = run_blender_script(script)
    output = result.stdout.strip() if result.stdout else result.stderr.strip()
    click.echo(output)


@cli.command()
@click.argument("output_path")
@click.option("--resolution", "-r", type=int, default=DEFAULT_RESOLUTION)
@click.option("--type", "bake_type", type=click.Choice(["normal", "diffuse"]), default="normal")
def bake(output_path, resolution, bake_type):
    """Bake texture map"""
    bake_map = {"normal": "NORMAL", "diffuse": "DIFFUSE"}
    
    script = f"""
import bpy
obj = bpy.context.active_object
if not obj:
    print("ERROR: No active object")
else:
    img = bpy.data.images.new("BakeOut", width={resolution}, height={resolution})
    mat = obj.data.materials[0] if obj.data.materials else bpy.data.materials.new(name="BakeMat")
    if not obj.data.materials:
        obj.data.materials.append(mat)
    
    nodes = mat.node_tree.nodes
    for n in list(nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nodes.remove(n)
    
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    nodes.get("Material Output")
    
    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.image = img
    tex_node.location = (bsdf.location.x - 300, bsdf.location.y)
    
    nodes.active = tex_node
    bpy.context.scene.render.engine = 'CYCLES'
    
    try:
        bpy.ops.object.bake(type='{bake_map[bake_type]}', save_mode='EXTERNAL')
        img.filepath_raw = "{output_path}"
        img.file_format = 'PNG'
        img.save()
        print("BAKE_SUCCESS:{output_path}")
    except Exception as e:
        print(f"BAKE_ERROR:{{e}}")
"""
    result = run_blender_script(script)
    output = result.stdout.strip() if result.stdout else result.stderr.strip()
    click.echo(output)


@cli.command()
@click.option("--name", "-n", help="Object name")
def select(name):
    """Select object"""
    obj_name = f'"{name}"' if name else "None"
    script = f"""
import bpy
obj = bpy.data.objects.get({obj_name}) if {obj_name} else bpy.context.active_object
if obj:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    print(f"SELECTED:{{obj.name}}")
else:
    print("ERROR: Object not found")
"""
    result = run_blender_script(script)
    click.echo(result.stdout.strip())


@cli.command()
@click.option("--path", "-p", help="Save path")
def save(path):
    """Save Blender file"""
    save_path = f'"{path}"' if path else '"blender_scene.blend"'
    script = f"""
import bpy
bpy.ops.wm.save_as_mainfile(filepath={save_path})
print("SAVE_SUCCESS")
"""
    result = run_blender_script(script)
    click.echo(result.stdout.strip())


@cli.command()
@click.argument("path")
def open(path):
    """Open Blender file"""
    script = f'''
import bpy
bpy.ops.wm.open_mainfile(filepath="{path}")
print("OPEN_SUCCESS")
'''
    result = run_blender_script(script)
    click.echo(result.stdout.strip())


@cli.command()
def objects():
    """List all objects"""
    script = """
import bpy
for obj in bpy.data.objects:
    print(f"{obj.name}|{obj.type}")
"""
    result = run_blender_script(script)
    for line in result.stdout.strip().split('\n'):
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 2:
                name, obj_type = parts[0], parts[1]
                click.echo(f"  {name} ({obj_type})")


if __name__ == "__main__":
    cli()
