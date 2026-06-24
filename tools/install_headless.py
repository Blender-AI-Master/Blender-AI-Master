"""Headless install helper for CLI-Anything-Blender.

Run via:
    blender --background --python install_headless.py -- <zip_path>

After this script completes:
  - The addon is installed at scripts/addons/cli_anything_blender/
  - userpref.blend records cli_anything_blender as enabled
  - On next GUI startup, Blender will show "AI Assistant for Blender" in Edit > Preferences > Extensions
"""
import bpy
import os
import sys
import shutil
import zipfile
import re

# Parse args
if "--" in sys.argv:
    argv = sys.argv[sys.argv.index("--") + 1:]
else:
    argv = sys.argv[1:]

if not argv:
    print("[ERROR] Usage: blender --background --python install_headless.py -- <zip_path>", flush=True)
    sys.exit(1)

zip_path = argv[0]
print(f"[install_headless] zip: {zip_path}", flush=True)
print(f"[install_headless] zip exists: {os.path.exists(zip_path)}", flush=True)

if not os.path.exists(zip_path):
    sys.exit(1)

# Verify zip structure (Blender 5.1 requires __init__.py in cli_anything_blender/ subdir)
with zipfile.ZipFile(zip_path, "r") as zf:
    names = zf.namelist()
    has_root_init = any(
        n.startswith("cli_anything_blender/") and n.endswith("__init__.py")
        for n in names
    )
    if not has_root_init:
        print("[ERROR] ZIP structure invalid - __init__.py must be in cli_anything_blender/ subdir", flush=True)
        sys.exit(2)
    print(f"[install_headless] ZIP OK ({len(names)} files)", flush=True)

# Clean user addons (残留目录)
addons_path = os.path.join(
    os.environ.get("APPDATA", ""),
    "Blender Foundation", "Blender", "5.1", "scripts", "addons"
)
if os.path.exists(addons_path):
    for d in os.listdir(addons_path):
        if d.lower().replace("_", "").startswith("clianything"):
            full = os.path.join(addons_path, d)
            if os.path.isdir(full):
                shutil.rmtree(full, ignore_errors=True)
                print(f"[install_headless] Cleaned: {full}", flush=True)

# Also clean extensions paths (Blender 5.1 manifest 模式原生位置)
for ext_path in [
    os.path.join(os.environ.get("APPDATA", ""), "Blender Foundation", "Blender", "5.1", "extensions", "user_default", "cli_anything_blender"),
    r"C:\Program Files\Blender Foundation\Blender 5.1\5.1\extensions\user_default\cli_anything_blender",
]:
    if os.path.exists(ext_path):
        shutil.rmtree(ext_path, ignore_errors=True)
        print(f"[install_headless] Cleaned extensions: {ext_path}", flush=True)

# Install zip (uses Blender's official installer -> scripts/addons/)
try:
    bpy.ops.preferences.addon_install(filepath=zip_path, target="DEFAULT", overwrite=True)
    print("INSTALL_OK", flush=True)
except Exception as e:
    print(f"INSTALL_FAIL: {type(e).__name__}: {e}", flush=True)
    sys.exit(3)

# Verify license in installed manifest, patch if missing
installed_dir = os.path.join(addons_path, "cli_anything_blender")
installed_manifest = os.path.join(installed_dir, "blender_manifest.toml")
if os.path.exists(installed_manifest):
    with open(installed_manifest, "r", encoding="utf-8") as f:
        content = f.read()
    if not re.search(r"^\s*license\s*=", content, re.MULTILINE):
        print("[install_headless] Patching manifest with license field...", flush=True)
        new_block = ('license = [\n    "SPDX:GPL-3.0-or-later",\n]\n'
                     'copyright = [\n    "2026 TripoAR Team",\n]\n\n')
        content = re.sub(r"(\[permissions\])", new_block + r"\1", content, count=1)
        with open(installed_manifest, "w", encoding="utf-8") as f:
            f.write(content)
        print("[install_headless] Manifest patched with license + copyright", flush=True)
    else:
        print("[install_headless] Manifest already has license", flush=True)

# Re-register the addon if we patched the manifest
try:
    bpy.ops.preferences.addon_disable(module="cli_anything_blender")
except Exception:
    pass

# Enable
try:
    bpy.ops.preferences.addon_enable(module="cli_anything_blender")
    print("ENABLE_OK", flush=True)
except Exception as e:
    print(f"ENABLE_FAIL: {type(e).__name__}: {e}", flush=True)
    sys.exit(4)

# SAVE userpref so the enabled state persists across GUI restarts
try:
    bpy.ops.wm.save_userpref()
    print("SAVED_USERPREF", flush=True)
except Exception as e:
    print(f"SAVE_FAIL: {type(e).__name__}: {e}", flush=True)

# Final state
addons = bpy.context.preferences.addons
print(f"Loaded addons: {list(addons.keys())}", flush=True)
if "cli_anything_blender" in addons:
    mod = addons["cli_anything_blender"]
    print(f"Module: {mod.module!r}", flush=True)
    print("FINAL_OK", flush=True)
else:
    print("FINAL_FAIL: addons not in dict", flush=True)
    sys.exit(5)
