"""
Industrial Surface Inspector Runner & Auto-Execution Script
===========================================================
This script registers the Industrial Surface Inspector UI panel and operators in Blender,
configures viewport shading to Material Preview mode, and ensures the model begins in its
pristine ORIGINAL CAD state ready for interactive presentation.
"""

import bpy
import sys
import os
import types
import importlib

# 1. Ensure directory containing modules is added to sys.path
def resolve_module_paths():
    candidates = []
    if bpy.data.filepath:
        candidates.append(os.path.dirname(os.path.abspath(bpy.data.filepath)))
    default_dir = r"c:\Users\monis\Downloads\3D component surface inspection\3D_Industrial_Component_Surface_Inspection"
    if os.path.exists(default_dir):
        candidates.append(default_dir)
    cwd = os.getcwd()
    candidates.append(cwd)
    
    for path in candidates:
        if path and os.path.exists(path) and path not in sys.path:
            sys.path.insert(0, path)

resolve_module_paths()

# 2. Fallback loader from bpy.data.texts if module is embedded
def load_embedded_text_module(name):
    target_names = [f"{name}.py", name]
    text_block = None
    for tn in target_names:
        if tn in bpy.data.texts:
            text_block = bpy.data.texts[tn]
            break
    if text_block is not None:
        mod = types.ModuleType(name)
        mod.__file__ = f"<bpy.data.texts['{text_block.name}']> "
        sys.modules[name] = mod
        exec(compile(text_block.as_string(), text_block.name, 'exec'), mod.__dict__)
        return mod
    return None

# Load or reload surface_inspection
try:
    if "surface_inspection" in sys.modules:
        import surface_inspection
        importlib.reload(surface_inspection)
    else:
        import surface_inspection
except ImportError:
    mod = load_embedded_text_module("surface_inspection")
    if mod is None:
        raise ImportError("Could not find surface_inspection module on disk or in bpy.data.texts!")

# Load or reload inspection_dashboard
try:
    if "inspection_dashboard" in sys.modules:
        import inspection_dashboard
        importlib.reload(inspection_dashboard)
    else:
        import inspection_dashboard
except ImportError:
    mod = load_embedded_text_module("inspection_dashboard")
    if mod is None:
        raise ImportError("Could not find inspection_dashboard module on disk or in bpy.data.texts!")

# 3. Register dashboard add-on
inspection_dashboard.register()
print("✓ Industrial Surface Inspector panel registered successfully!")

# 4. Set 3D Viewport shading to Material Preview so CAD metallic shaders shine
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'

# 5. Ensure model starts in pristine ORIGINAL CAD mode
try:
    surface_inspection.restore_all_component_materials()
    surface_inspection.remove_normal_arrows()
    if hasattr(bpy.context.scene, "surface_inspector"):
        settings = bpy.context.scene.surface_inspector
        settings.is_inspected = False
        settings.show_arrows = False
    print("✓ Model ready in ORIGINAL CAD state (PBR Machined Steel & Cast Iron).")
except Exception as e:
    print(f"Notice during CAD init: {e}")

print("\n" + "="*60)
print("  3D INDUSTRIAL COMPONENT SURFACE INSPECTION PRESENTATION READY")
print("  - Current State: ORIGINAL CAD (Machined Metallic Assembly)")
print("  - To Show Inspection: Press [N] in 3D Viewport -> 'Surface Inspector' Tab")
print("  - Click: '▶ Show Inspection (Colors & Arrows)'")
print("  - Click: '⟲ Reset to Original CAD Model' anytime to return!")
print("="*60 + "\n")
