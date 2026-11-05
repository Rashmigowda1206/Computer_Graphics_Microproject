"""
Setup Presentation Script for Blender Files
===========================================
Configures .blend files so that upon opening:
1. The 3D model is in its pristine ORIGINAL CAD state (Machined Steel, Cast Iron, Galvanized Bolts).
2. Inspection orientation colors (Green/Red/Yellow) and normal arrows are cleared.
3. 3D Viewport is set to Material Preview mode.
4. Embedded scripts are updated with the interactive presentation panel.
5. Text datablock run_inspector.py has use_module = True so Blender registers it on load.
"""

import bpy
import os
import sys

proj_dir = os.path.dirname(os.path.abspath(__file__))
if proj_dir not in sys.path:
    sys.path.insert(0, proj_dir)

import surface_inspection
import inspection_dashboard

inspection_dashboard.register()

# 1. Sync updated embedded text blocks
files_to_sync = ['surface_inspection.py', 'inspection_dashboard.py', 'run_inspector.py']
for fn in files_to_sync:
    fp = os.path.join(proj_dir, fn)
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    tb = bpy.data.texts.get(fn)
    if not tb:
        tb = bpy.data.texts.new(fn)
    tb.clear()
    tb.write(content)
    if fn == 'run_inspector.py':
        tb.use_module = True  # Register on load

# 2. Restore all component objects to Original CAD materials
restored = surface_inspection.restore_all_component_materials()
print(f"Restored original materials on {restored} objects.")

# 3. Remove any generated normal vector visualizers
surface_inspection.remove_normal_arrows()

# 4. Set inspector settings to CAD state
if hasattr(bpy.context.scene, 'surface_inspector'):
    settings = bpy.context.scene.surface_inspector
    settings.is_inspected = False
    settings.show_arrows = False

# 5. Update instruction label text
lbl = bpy.data.objects.get('Scene_Instruction_Label')
if lbl and lbl.data:
    lbl.data.body = "3D Industrial Surface Inspection\nPress [N] in 3D Viewport -> 'Surface Inspector' Tab -> Click '▶ Show Inspection'"

# 6. Ensure viewport shading is Material Preview across all screens
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'

# Save the file
bpy.ops.wm.save_mainfile()
print("Saved blend file successfully in pristine Original CAD presentation state!")
