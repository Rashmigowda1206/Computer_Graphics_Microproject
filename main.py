"""
Main Scene Setup and Project Builder
====================================
Computer Graphics Microproject: 3D Industrial Component Surface Inspection
Target Environment: Blender 5.0.1 Python API (`bpy`)

This script:
1. Cleans up default template objects and creates organized scene collections:
   - Industrial_Component
   - Inspection_Visualization
   - Inspection_Labels
   - Lighting_and_Cameras
   - Inspection_Dashboard_Assets
2. Procedurally builds a highly detailed 3D Industrial Component:
   - Industrial Flanged Valve Housing
   - Central housing with cylindrical body and stepped collars
   - Horizontal pipe section with dual heavy connection flanges
   - Precision hex bolts with washers on flanges, top cap, and base
   - 4 Angled triangular gussets / stiffener ribs
   - Heavy machined base mounting plate with anchor slots
   - Top inspection hatch / cover plate
3. Sets up realistic PBR metallic materials for the component and studio staging.
4. Configures 3-point studio lighting and a framed camera view.
5. Registers the inspection dashboard add-on and runs an initial surface inspection.
6. Exports an initial verification CSV report.
7. Embeds scripts into Blender text datablocks for seamless standalone operation.
8. Saves the complete project as Industrial_Surface_Inspection.blend.
"""

import bpy
import bmesh
from mathutils import Vector, Matrix, Euler
import math
import os
import sys

# Ensure local script directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

import surface_inspection
import inspection_dashboard


# ==============================================================================
# SCENE INITIALIZATION & COLLECTION MANAGEMENT
# ==============================================================================

def setup_collections():
    """Initializes and returns the organized scene collections."""
    collection_names = [
        surface_inspection.COLLECTION_COMPONENT,
        surface_inspection.COLLECTION_VISUALIZATION,
        "Inspection_Labels",
        "Lighting_and_Cameras",
        surface_inspection.COLLECTION_ASSETS,
    ]
    
    cols = {}
    master_col = bpy.context.scene.collection
    
    # Remove default objects
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
        
    # Create required collections
    for name in collection_names:
        col = bpy.data.collections.get(name)
        if not col:
            col = bpy.data.collections.new(name)
            master_col.children.link(col)
        cols[name] = col
        
    return cols


# ==============================================================================
# PBR MATERIAL CREATION
# ==============================================================================

def create_pbr_material(name, base_color, metallic=0.0, roughness=0.5, emit_color=(0,0,0,1), emit_strength=0.0):
    """Creates a Principled BSDF material with specified physical properties."""
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
        
    mat.use_fake_user = True  # Protect from being purged by Blender when unassigned
    mat.diffuse_color = base_color
    
    if mat.node_tree:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            if "Base Color" in bsdf.inputs:
                bsdf.inputs["Base Color"].default_value = base_color
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = metallic
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = roughness
            if emit_strength > 0 and "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = emit_color
                if "Emission Strength" in bsdf.inputs:
                    bsdf.inputs["Emission Strength"].default_value = emit_strength
                    
    return mat


def setup_materials():
    """Creates original industrial materials."""
    mats = {
        "Mat_Machined_Steel": create_pbr_material("Mat_Machined_Steel", (0.76, 0.78, 0.80, 1.0), metallic=0.88, roughness=0.22),
        "Mat_Cast_Iron": create_pbr_material("Mat_Cast_Iron", (0.28, 0.30, 0.32, 1.0), metallic=0.70, roughness=0.45),
        "Mat_Galvanized_Bolt": create_pbr_material("Mat_Galvanized_Bolt", (0.85, 0.86, 0.88, 1.0), metallic=0.95, roughness=0.15),
        "Mat_Studio_Pedestal": create_pbr_material("Mat_Studio_Pedestal", (0.10, 0.11, 0.13, 1.0), metallic=0.15, roughness=0.55),
    }
    return mats


# ==============================================================================
# PROCEDURAL INDUSTRIAL COMPONENT MODELING
# ==============================================================================

def add_hex_bolt(bm, center, normal, head_radius=0.13, head_height=0.12, washer_radius=0.19, washer_height=0.03):
    """Constructs a high-tensile hex bolt with washer at center facing along normal."""
    up = Vector((0.0, 0.0, 1.0))
    norm = normal.normalized()
    if norm.dot(up) > 0.9999:
        rot_mat = Matrix.Identity(3)
    elif norm.dot(up) < -0.9999:
        rot_mat = Matrix.Rotation(math.pi, 3, 'X')
    else:
        rot_axis = up.cross(norm).normalized()
        rot_angle = math.acos(max(-1.0, min(1.0, up.dot(norm))))
        rot_mat = Matrix.Rotation(rot_angle, 3, rot_axis)
        
    # Circular Washer (12 segments)
    t_washer = Matrix.Translation(center + norm * (washer_height * 0.5)) @ rot_mat.to_4x4()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=12,
        radius1=washer_radius,
        radius2=washer_radius,
        depth=washer_height,
        matrix=t_washer
    )
    
    # Hex Head (6 segments)
    t_head = Matrix.Translation(center + norm * (washer_height + head_height * 0.5)) @ rot_mat.to_4x4()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=6,
        radius1=head_radius,
        radius2=head_radius,
        depth=head_height,
        matrix=t_head
    )


def add_gusset_rib(bm, center, normal_axis, width=0.14, height=0.8, reach=0.65):
    """Constructs a triangular stiffener rib connecting body to flange."""
    # Build a wedge prism
    half_w = width * 0.5
    # Local coordinates of triangular cross-section in XZ, extruded along Y
    v0 = Vector((0.0, -half_w, 0.0))
    v1 = Vector((reach, -half_w, 0.0))
    v2 = Vector((0.0, -half_w, height))
    
    v3 = Vector((0.0, half_w, 0.0))
    v4 = Vector((reach, half_w, 0.0))
    v5 = Vector((0.0, half_w, height))
    
    verts = [bm.verts.new(center + v) for v in [v0, v1, v2, v3, v4, v5]]
    
    # Faces
    bm.faces.new([verts[0], verts[1], verts[2]])
    bm.faces.new([verts[3], verts[5], verts[4]])
    bm.faces.new([verts[0], verts[3], verts[4], verts[1]])
    bm.faces.new([verts[1], verts[4], verts[5], verts[2]])
    bm.faces.new([verts[2], verts[5], verts[3], verts[0]])


def build_industrial_housing_mesh():
    """
    Constructs the main mechanical housing mesh containing:
    - Vertical cylindrical body with stepped collars
    - Horizontal pipe with dual heavy circular connection flanges
    - Flange counterbore recesses
    - 4 Triangular stiffener gussets
    """
    bm = bmesh.new()
    
    # 1. Vertical main housing body
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=24,
        radius1=1.10,
        radius2=1.10,
        depth=2.30,
        matrix=Matrix.Translation((0.0, 0.0, 0.0))
    )
    
    # Lower collar
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=24,
        radius1=1.22,
        radius2=1.22,
        depth=0.25,
        matrix=Matrix.Translation((0.0, 0.0, -0.95))
    )
    
    # Upper collar
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=24,
        radius1=1.22,
        radius2=1.22,
        depth=0.25,
        matrix=Matrix.Translation((0.0, 0.0, 0.95))
    )
    
    # 2. Horizontal flanged pipe
    rot_y90 = Matrix.Rotation(math.pi / 2, 4, 'Y')
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=24,
        radius1=0.72,
        radius2=0.72,
        depth=3.60,
        matrix=Matrix.Translation((0.0, 0.0, 0.10)) @ rot_y90
    )
    
    # Left flange
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=24,
        radius1=1.45,
        radius2=1.45,
        depth=0.35,
        matrix=Matrix.Translation((-1.80, 0.0, 0.10)) @ rot_y90
    )
    # Left flange bore recess (counterbore)
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=16,
        radius1=0.48,
        radius2=0.48,
        depth=0.10,
        matrix=Matrix.Translation((-1.95, 0.0, 0.10)) @ rot_y90
    )
    
    # Right flange
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=24,
        radius1=1.45,
        radius2=1.45,
        depth=0.35,
        matrix=Matrix.Translation((1.80, 0.0, 0.10)) @ rot_y90
    )
    # Right flange bore recess
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=16,
        radius1=0.48,
        radius2=0.48,
        depth=0.10,
        matrix=Matrix.Translation((1.95, 0.0, 0.10)) @ rot_y90
    )
    
    # 3. 4 Triangular gusset stiffeners
    # Left top gusset
    add_gusset_rib(bm, Vector((-1.0, 0.0, 0.45)), Vector((1, 0, 0)), width=0.14, height=0.6, reach=-0.6)
    # Left bottom gusset
    add_gusset_rib(bm, Vector((-1.0, 0.0, -0.45)), Vector((1, 0, 0)), width=0.14, height=-0.6, reach=-0.6)
    # Right top gusset
    add_gusset_rib(bm, Vector((1.0, 0.0, 0.45)), Vector((-1, 0, 0)), width=0.14, height=0.6, reach=0.6)
    # Right bottom gusset
    add_gusset_rib(bm, Vector((1.0, 0.0, -0.45)), Vector((-1, 0, 0)), width=0.14, height=-0.6, reach=0.6)
    
    # Recalculate face normals
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    
    mesh = bpy.data.meshes.new("Mesh_Gearbox_Valve_Housing")
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def build_base_plate_mesh():
    """
    Constructs the heavy machined base mounting plate with beveled edges and corner mounting slots.
    """
    bm = bmesh.new()
    
    # Main base plate slab
    bmesh.ops.create_cube(
        bm,
        size=1.0,
        matrix=Matrix.Translation((0.0, 0.0, -1.30)) @ Matrix.Diagonal((4.20, 2.90, 0.28, 1.0))
    )
    
    # 4 Corner mounting pads
    pad_positions = [
        (-1.75, -1.15, -1.14),
        (-1.75,  1.15, -1.14),
        ( 1.75, -1.15, -1.14),
        ( 1.75,  1.15, -1.14),
    ]
    for pad_pos in pad_positions:
        bmesh.ops.create_cone(
            bm,
            cap_ends=True,
            segments=16,
            radius1=0.28,
            radius2=0.28,
            depth=0.06,
            matrix=Matrix.Translation(pad_pos)
        )
        
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    
    mesh = bpy.data.meshes.new("Mesh_Base_Mounting_Plate")
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def build_top_cover_mesh():
    """
    Constructs the top circular inspection hatch cover with knurled cap.
    """
    bm = bmesh.new()
    
    # Cover disc
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=24,
        radius1=1.26,
        radius2=1.26,
        depth=0.20,
        matrix=Matrix.Translation((0.0, 0.0, 1.25))
    )
    
    # Central boss / cap
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=16,
        radius1=0.48,
        radius2=0.48,
        depth=0.26,
        matrix=Matrix.Translation((0.0, 0.0, 1.45))
    )
    
    # Hex nut on top cap
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=6,
        radius1=0.22,
        radius2=0.22,
        depth=0.18,
        matrix=Matrix.Translation((0.0, 0.0, 1.62))
    )
    
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    
    mesh = bpy.data.meshes.new("Mesh_Top_Inspection_Cover")
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def build_fastener_bolts_mesh():
    """
    Constructs all precision hex bolts with washers:
    - 6 on Left Flange
    - 6 on Right Flange
    - 6 on Top Inspection Cover
    - 4 on Base Mounting Plate
    Total = 22 high-tensile industrial fasteners.
    """
    bm = bmesh.new()
    
    # Left and Right Flange Bolts
    r_bolt = 1.15
    for i in range(6):
        theta = i * (2 * math.pi / 6)
        y_b = r_bolt * math.cos(theta)
        z_b = 0.10 + r_bolt * math.sin(theta)
        # Left flange bolts (facing -X)
        add_hex_bolt(bm, Vector((-1.975, y_b, z_b)), Vector((-1.0, 0.0, 0.0)), head_radius=0.12, head_height=0.11)
        # Right flange bolts (facing +X)
        add_hex_bolt(bm, Vector((1.975, y_b, z_b)), Vector((1.0, 0.0, 0.0)), head_radius=0.12, head_height=0.11)
        
    # Top Cover Bolts
    r_top_bolt = 1.02
    for i in range(6):
        theta = i * (2 * math.pi / 6) + (math.pi / 6)
        x_b = r_top_bolt * math.cos(theta)
        y_b = r_top_bolt * math.sin(theta)
        add_hex_bolt(bm, Vector((x_b, y_b, 1.35)), Vector((0.0, 0.0, 1.0)), head_radius=0.10, head_height=0.09)
        
    # Base Plate Anchor Bolts
    base_bolt_pos = [
        (-1.75, -1.15, -1.11),
        (-1.75,  1.15, -1.11),
        ( 1.75, -1.15, -1.11),
        ( 1.75,  1.15, -1.11),
    ]
    for pos in base_bolt_pos:
        add_hex_bolt(bm, Vector(pos), Vector((0.0, 0.0, 1.0)), head_radius=0.14, head_height=0.12)
        
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    
    mesh = bpy.data.meshes.new("Mesh_Flange_Mounting_Bolts")
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def build_studio_pedestal_mesh():
    """Constructs the staging platform / ground pedestal."""
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=32,
        radius1=4.50,
        radius2=4.80,
        depth=0.20,
        matrix=Matrix.Translation((0.0, 0.0, -1.54))
    )
    mesh = bpy.data.meshes.new("Mesh_Studio_Pedestal")
    bm.to_mesh(mesh)
    bm.free()
    return mesh


# ==============================================================================
# LIGHTING AND CAMERA SETUP
# ==============================================================================

def setup_lighting_and_camera(collections):
    """Sets up a 3-point studio lighting rig and framed inspection camera."""
    cam_col = collections["Lighting_and_Cameras"]
    
    # 1. Inspection Camera
    cam_data = bpy.data.cameras.new("Inspection_Camera")
    cam_data.lens = 52.0  # Professional focal length
    cam_obj = bpy.data.objects.new("Inspection_Camera", cam_data)
    cam_col.objects.link(cam_obj)
    
    # Position camera for optimal 3/4 isometric inspection view
    cam_obj.location = (4.8, -5.4, 3.8)
    # Track towards center
    rot_euler = Euler((math.radians(60.0), 0.0, math.radians(42.0)), 'XYZ')
    cam_obj.rotation_euler = rot_euler
    bpy.context.scene.camera = cam_obj
    
    # 2. Key Light (Warm, high intensity)
    key_data = bpy.data.lights.new("Key_Light", type='AREA')
    key_data.energy = 650.0
    key_data.color = (1.0, 0.96, 0.92)
    key_data.size = 2.5
    key_obj = bpy.data.objects.new("Key_Light", key_data)
    key_obj.location = (4.5, -4.0, 5.0)
    key_obj.rotation_euler = Euler((math.radians(45.0), 0.0, math.radians(45.0)), 'XYZ')
    cam_col.objects.link(key_obj)
    
    # 3. Fill Light (Cool, soft)
    fill_data = bpy.data.lights.new("Fill_Light", type='AREA')
    fill_data.energy = 280.0
    fill_data.color = (0.88, 0.94, 1.0)
    fill_data.size = 3.5
    fill_obj = bpy.data.objects.new("Fill_Light", fill_data)
    fill_obj.location = (-4.0, -3.5, 3.0)
    fill_obj.rotation_euler = Euler((math.radians(50.0), 0.0, math.radians(-45.0)), 'XYZ')
    cam_col.objects.link(fill_obj)
    
    # 4. Rim / Edge Backlight (Accentuate silhouettes and surface normals)
    rim_data = bpy.data.lights.new("Rim_Light", type='AREA')
    rim_data.energy = 450.0
    rim_data.color = (0.95, 0.98, 1.0)
    rim_data.size = 2.0
    rim_obj = bpy.data.objects.new("Rim_Light", rim_data)
    rim_obj.location = (0.0, 4.5, 4.0)
    rim_obj.rotation_euler = Euler((math.radians(-45.0), 0.0, math.radians(180.0)), 'XYZ')
    cam_col.objects.link(rim_obj)


# ==============================================================================
# SCRIPT EMBEDDING FOR STANDALONE OPERATION
# ==============================================================================

def embed_scripts_into_blend():
    """
    Embeds the inspection script modules into Blender's internal text datablocks
    so the project remains fully functional without external file dependencies.
    """
    files_to_embed = [
        ("surface_inspection.py", os.path.join(SCRIPT_DIR, "surface_inspection.py")),
        ("inspection_dashboard.py", os.path.join(SCRIPT_DIR, "inspection_dashboard.py")),
    ]
    
    for block_name, file_path in files_to_embed:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            text_block = bpy.data.texts.get(block_name)
            if not text_block:
                text_block = bpy.data.texts.new(block_name)
            text_block.clear()
            text_block.write(content)
            
    # Also embed the robust runner script
    runner_path = os.path.join(base_dir, "run_inspector.py")
    if os.path.exists(runner_path):
        with open(runner_path, "r", encoding="utf-8") as f:
            runner_code = f.read()
    else:
        runner_code = '''import bpy, sys, os, importlib
blend_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else ""
if blend_dir and blend_dir not in sys.path:
    sys.path.insert(0, blend_dir)
import inspection_dashboard
inspection_dashboard.register()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
try:
    import surface_inspection
    surface_inspection.restore_all_component_materials()
    surface_inspection.remove_normal_arrows()
except Exception as e:
    pass
print("Industrial Surface Inspector panel loaded in Original CAD mode!")
'''
    runner_block = bpy.data.texts.get("run_inspector.py")
    if not runner_block:
        runner_block = bpy.data.texts.new("run_inspector.py")
    runner_block.clear()
    runner_block.write(runner_code)


def create_3d_instruction_label(label_col):
    """Adds a 3D instructional text label in the viewport."""
    curve = bpy.data.curves.new("Scene_Instruction_Label", type='FONT')
    curve.body = "3D Component Surface Inspection\nPress [N] in 3D Viewport -> 'Surface Inspector' Tab -> Click '▶ Show Inspection'"
    curve.size = 0.13
    curve.align_x = 'CENTER'
    curve.align_y = 'CENTER'
    
    obj_label = bpy.data.objects.new("Scene_Instruction_Label", curve)
    label_col.objects.link(obj_label)
    obj_label.location = (0.0, -2.85, -1.42)
    obj_label.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    
    mat_lbl = bpy.data.materials.new("Mat_Scene_Label")
    mat_lbl.diffuse_color = (0.0, 0.85, 1.0, 1.0)
    if mat_lbl.node_tree:
        bsdf = mat_lbl.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.0, 0.85, 1.0, 1.0)
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (0.0, 0.85, 1.0, 1.0)
                bsdf.inputs["Emission Strength"].default_value = 1.0
    obj_label.data.materials.append(mat_lbl)
    obj_label.hide_select = True


# ==============================================================================
# MASTER BUILD ROUTINE
# ==============================================================================

def build_project():
    """Builds the entire 3D Industrial Surface Inspection project."""
    print("=========================================================")
    print("Building 3D Industrial Component Surface Inspection Scene")
    print("=========================================================")
    
    # 1. Setup Collections
    cols = setup_collections()
    comp_col = cols[surface_inspection.COLLECTION_COMPONENT]
    asset_col = cols[surface_inspection.COLLECTION_ASSETS]
    label_col = cols["Inspection_Labels"]
    
    # 2. Setup Materials
    mats = setup_materials()
    
    # 3. Create Industrial Component Meshes
    # Main Housing
    mesh_housing = build_industrial_housing_mesh()
    obj_housing = bpy.data.objects.new("Gearbox_Valve_Housing", mesh_housing)
    obj_housing.data.materials.append(mats["Mat_Cast_Iron"])
    comp_col.objects.link(obj_housing)
    
    # Base Plate
    mesh_base = build_base_plate_mesh()
    obj_base = bpy.data.objects.new("Base_Mounting_Plate", mesh_base)
    obj_base.data.materials.append(mats["Mat_Machined_Steel"])
    comp_col.objects.link(obj_base)
    
    # Top Cover
    mesh_cover = build_top_cover_mesh()
    obj_cover = bpy.data.objects.new("Top_Inspection_Cover", mesh_cover)
    obj_cover.data.materials.append(mats["Mat_Machined_Steel"])
    comp_col.objects.link(obj_cover)
    
    # Fastener Bolts
    mesh_bolts = build_fastener_bolts_mesh()
    obj_bolts = bpy.data.objects.new("Flange_Mounting_Bolts", mesh_bolts)
    obj_bolts.data.materials.append(mats["Mat_Galvanized_Bolt"])
    comp_col.objects.link(obj_bolts)
    
    # Studio Pedestal
    mesh_pedestal = build_studio_pedestal_mesh()
    obj_pedestal = bpy.data.objects.new("Studio_Staging_Pedestal", mesh_pedestal)
    obj_pedestal.data.materials.append(mats["Mat_Studio_Pedestal"])
    asset_col.objects.link(obj_pedestal)
    
    # 3D Instruction Label
    create_3d_instruction_label(label_col)
    
    # 4. Setup Lighting & Camera
    setup_lighting_and_camera(cols)
    
    # 5. Register Inspection Addon
    inspection_dashboard.register()
    
    # 6. Run Initial Surface Inspection
    settings = bpy.context.scene.surface_inspector
    settings.direction = (0.0, -1.0, 0.4)
    settings.threshold = 0.30
    settings.arrow_scale = 0.35
    settings.arrow_subsample = 2
    settings.show_arrows = True
    
    print("Running initial surface normal inspection...")
    bpy.ops.inspect.run_inspection()
    
    # 7. Export Initial Verification CSV
    csv_file = os.path.join(SCRIPT_DIR, "inspection_report.csv")
    settings.csv_export_path = csv_file
    bpy.ops.inspect.export_csv()
    print(f"Exported initial verification CSV report to: {csv_file}")
    
    # 7b. Reset to pristine state so the component opens interactively on-demand
    print("Resetting visualization so component opens in pristine interactive state...")
    bpy.ops.inspect.reset_visualization()
    
    # 8. Configure Viewport Shading for Material Display
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'
                        space.shading.use_scene_lights = True
                        space.shading.use_scene_world = False
                        
    # 9. Embed Scripts
    embed_scripts_into_blend()
    
    # 10. Save Finished .blend File
    blend_path = os.path.join(SCRIPT_DIR, "Industrial_Surface_Inspection.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Successfully saved project to: {blend_path}")
    print("=========================================================")


if __name__ == "__main__":
    build_project()
