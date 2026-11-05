"""
Inspection Dashboard Module
===========================
Blender 5.0.1 Sidebar Panel & Operators for 3D Industrial Component Surface Inspection.

Adds the "Industrial Surface Inspector" panel to the 3D Viewport Sidebar (press N in 3D Viewport).
Provides interactive controls:
- Starts in pristine ORIGINAL CAD state upon opening
- Dual primary presentation buttons:
    * "▶ Show Inspection (Colors & Arrows)" (computes normals, applies Green/Red/Yellow, displays Cyan arrows)
    * "⟲ Reset to Original CAD Model" (restores metallic materials, hides arrows)
- Interactive toggles: "Toggle Normal Arrows" & "Toggle Orientation Colors"
- Real-time live updating: dragging direction or threshold updates live on the 3D mesh
- 6 Quick Direction Presets (+X, -X, +Y, -Y, +Z, -Z, ISO, Camera View)
- Angular Threshold Slider (Front: D > +T, Back: D < -T, Side: |D| <= T)
- Inspection Statistics Display (Front, Back, Side counts & percentages with 100% verification check)
- CSV Quality Audit Report Export Operator
"""

import bpy
from mathutils import Vector
import os
import sys

# Ensure local module directory is in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.append(_current_dir)

import surface_inspection


# Cache for latest inspection data (used for CSV export)
_LATEST_INSPECTED_DATA = []
_LATEST_STATS = None


def update_show_arrows(self, context):
    """Callback when show_arrows property is toggled."""
    surface_inspection.set_normal_arrows_visibility(self.show_arrows)


def update_inspection_params(self, context):
    """Live-updates the 3D inspection visualization when sliders change."""
    if self.is_inspected:
        bpy.ops.inspect.run_inspection()


class SurfaceInspectionSettings(bpy.types.PropertyGroup):
    """Property group storing user settings and inspection statistics."""
    
    direction: bpy.props.FloatVectorProperty(
        name="Direction",
        description="Vector direction from which the inspection sensor/camera views the surface",
        size=3,
        default=(0.0, -1.0, 0.4),
        precision=3,
        step=10,
        update=update_inspection_params,
    )
    
    threshold: bpy.props.FloatProperty(
        name="Threshold (T)",
        description="Orientation classification threshold (Front: D > +T, Back: D < -T, Side: |D| <= T)",
        default=0.30,
        min=0.0,
        max=0.99,
        step=0.05,
        precision=2,
        update=update_inspection_params,
    )
    
    arrow_scale: bpy.props.FloatProperty(
        name="Arrow Length",
        description="Length of normal vector arrows in 3D world units",
        default=0.35,
        min=0.05,
        max=2.0,
        step=0.05,
        precision=2,
        update=update_inspection_params,
    )
    
    arrow_subsample: bpy.props.IntProperty(
        name="Arrow Step",
        description="Display 1 arrow every N polygon faces to prevent visual clutter",
        default=2,
        min=1,
        max=10,
        update=update_inspection_params,
    )
    
    show_arrows: bpy.props.BoolProperty(
        name="Show Normal Arrows",
        description="Toggle visibility of cyan surface normal arrows in 3D viewport",
        default=False,
        update=update_show_arrows,
    )
    
    is_inspected: bpy.props.BoolProperty(
        name="Is Inspected",
        description="Flag indicating whether inspection colors are currently displayed",
        default=False,
    )
    
    csv_export_path: bpy.props.StringProperty(
        name="CSV Report Path",
        description="File path for exporting inspection results report",
        subtype='FILE_PATH',
        default="//inspection_report.csv",
    )
    
    # Statistical counters
    stat_total_objects: bpy.props.IntProperty(name="Objects", default=0)
    stat_total_faces: bpy.props.IntProperty(name="Total Faces", default=0)
    stat_front_faces: bpy.props.IntProperty(name="Front Faces", default=0)
    stat_back_faces: bpy.props.IntProperty(name="Back Faces", default=0)
    stat_side_faces: bpy.props.IntProperty(name="Side Faces", default=0)
    stat_front_pct: bpy.props.FloatProperty(name="Front %", default=0.0, precision=1)
    stat_back_pct: bpy.props.FloatProperty(name="Back %", default=0.0, precision=1)
    stat_side_pct: bpy.props.FloatProperty(name="Side %", default=0.0, precision=1)
    stat_arrow_count: bpy.props.IntProperty(name="Arrows", default=0)


# ==============================================================================
# OPERATORS
# ==============================================================================

class INSPECT_OT_run_inspection(bpy.types.Operator):
    """Executes surface normal inspection, classifies polygons, colors surfaces and shows 3D normal arrows"""
    bl_idname = "inspect.run_inspection"
    bl_label = "Show Inspection (Colors & Arrows)"
    bl_description = "Calculates polygon normals, performs dot-product classification, colors surfaces and shows 3D arrows"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global _LATEST_INSPECTED_DATA, _LATEST_STATS
        settings = context.scene.surface_inspector
        
        dir_vec = Vector(settings.direction)
        if dir_vec.length < 1e-4:
            self.report({'WARNING'}, "Inspection direction cannot be zero. Resetting to (0, -1, 0).")
            settings.direction = (0.0, -1.0, 0.0)
            dir_vec = Vector((0.0, -1.0, 0.0))
            
        stats, inspected_data = surface_inspection.run_component_inspection(
            inspection_direction=dir_vec,
            threshold=settings.threshold,
            arrow_scale=settings.arrow_scale,
            subsample_step=settings.arrow_subsample
        )
        
        _LATEST_INSPECTED_DATA = inspected_data
        _LATEST_STATS = stats
        
        # Update settings stats
        settings.stat_total_objects = stats["total_objects"]
        settings.stat_total_faces = stats["total_faces"]
        settings.stat_front_faces = stats["front_faces"]
        settings.stat_back_faces = stats["back_faces"]
        settings.stat_side_faces = stats["side_faces"]
        settings.stat_front_pct = stats["front_pct"]
        settings.stat_back_pct = stats["back_pct"]
        settings.stat_side_pct = stats["side_pct"]
        settings.stat_arrow_count = stats["arrow_count"]
        settings.is_inspected = True
        settings.show_arrows = True
        
        # Ensure arrow visibility matches setting
        surface_inspection.set_normal_arrows_visibility(True)
        
        self.report({'INFO'}, f"Inspected {stats['total_faces']} faces: {stats['front_faces']} Front, {stats['back_faces']} Back, {stats['side_faces']} Side")
        return {'FINISHED'}


class INSPECT_OT_restore_materials(bpy.types.Operator):
    """Restores the original CAD materials and hides normal vector arrows"""
    bl_idname = "inspect.restore_materials"
    bl_label = "Reset to Original CAD Model"
    bl_description = "Removes inspection color-coding and restores original metallic CAD materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.surface_inspector
        restored = surface_inspection.restore_all_component_materials()
        surface_inspection.remove_normal_arrows()
        settings.is_inspected = False
        settings.show_arrows = False
        self.report({'INFO'}, f"Restored original CAD materials on {restored} objects")
        return {'FINISHED'}


class INSPECT_OT_toggle_normals(bpy.types.Operator):
    """Toggles visibility of the cyan surface normal arrows in 3D Viewport"""
    bl_idname = "inspect.toggle_normals"
    bl_label = "Toggle Normal Arrows"
    bl_description = "Shows or hides the cyan normal direction arrows"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.surface_inspector
        if not settings.is_inspected:
            bpy.ops.inspect.run_inspection()
            settings.show_arrows = True
        else:
            settings.show_arrows = not settings.show_arrows
            surface_inspection.set_normal_arrows_visibility(settings.show_arrows)
            
        status = 'Visible' if settings.show_arrows else 'Hidden'
        self.report({'INFO'}, f"Normal arrows visibility: {status}")
        return {'FINISHED'}


class INSPECT_OT_toggle_colors(bpy.types.Operator):
    """Toggles between original metallic materials and inspection color-coding"""
    bl_idname = "inspect.toggle_colors"
    bl_label = "Toggle Orientation Colors"
    bl_description = "Switches between original metallic materials and inspection color-coding"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.surface_inspector
        if settings.is_inspected:
            surface_inspection.restore_all_component_materials()
            settings.is_inspected = False
            self.report({'INFO'}, "Showing Original CAD Materials")
        else:
            bpy.ops.inspect.run_inspection()
            self.report({'INFO'}, "Showing Inspection Orientation Colors")
        return {'FINISHED'}


class INSPECT_OT_reset_visualization(bpy.types.Operator):
    """Resets inspection colors and deletes generated normal vectors"""
    bl_idname = "inspect.reset_visualization"
    bl_label = "Reset All"
    bl_description = "Restores original materials and removes all generated visualization objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global _LATEST_INSPECTED_DATA, _LATEST_STATS
        settings = context.scene.surface_inspector
        surface_inspection.restore_all_component_materials()
        surface_inspection.remove_normal_arrows()
        settings.is_inspected = False
        settings.show_arrows = False
        settings.stat_total_objects = 0
        settings.stat_total_faces = 0
        settings.stat_front_faces = 0
        settings.stat_back_faces = 0
        settings.stat_side_faces = 0
        settings.stat_front_pct = 0.0
        settings.stat_back_pct = 0.0
        settings.stat_side_pct = 0.0
        settings.stat_arrow_count = 0
        _LATEST_INSPECTED_DATA = []
        _LATEST_STATS = None
        self.report({'INFO'}, "Inspection visualization reset completely")
        return {'FINISHED'}


class INSPECT_OT_export_csv(bpy.types.Operator):
    """Exports inspection results to a CSV report file"""
    bl_idname = "inspect.export_csv"
    bl_label = "Export CSV Report"
    bl_description = "Exports polygon classifications, normals, and dot products to a CSV file"
    bl_options = {'REGISTER'}

    def execute(self, context):
        global _LATEST_INSPECTED_DATA, _LATEST_STATS
        settings = context.scene.surface_inspector
        
        if not _LATEST_INSPECTED_DATA:
            bpy.ops.inspect.run_inspection()
            
        if not _LATEST_INSPECTED_DATA:
            self.report({'ERROR'}, "No inspection data available to export.")
            return {'CANCELLED'}
            
        export_path = settings.csv_export_path
        if not export_path:
            export_path = "//inspection_report.csv"
            
        try:
            saved_file = surface_inspection.export_inspection_csv(export_path, _LATEST_INSPECTED_DATA, _LATEST_STATS)
            self.report({'INFO'}, f"Exported CSV report to: {saved_file}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to export CSV: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}


class INSPECT_OT_preset_direction(bpy.types.Operator):
    """Sets a predefined inspection direction"""
    bl_idname = "inspect.preset_direction"
    bl_label = "Set Preset Direction"
    bl_description = "Sets inspection direction to an axis or standard viewpoint"
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.StringProperty()

    def execute(self, context):
        settings = context.scene.surface_inspector
        presets = {
            "+X": (1.0, 0.0, 0.0),
            "-X": (-1.0, 0.0, 0.0),
            "+Y": (0.0, 1.0, 0.0),
            "-Y": (0.0, -1.0, 0.0),
            "+Z": (0.0, 0.0, 1.0),
            "-Z": (0.0, 0.0, -1.0),
            "ISO": (0.577, -0.577, 0.577),
        }
        if self.preset in presets:
            settings.direction = presets[self.preset]
            if settings.is_inspected:
                bpy.ops.inspect.run_inspection()
        return {'FINISHED'}


class INSPECT_OT_align_camera(bpy.types.Operator):
    """Sets inspection direction pointing toward the active camera"""
    bl_idname = "inspect.align_camera"
    bl_label = "Align with Active Camera"
    bl_description = "Calculates inspection direction pointing directly from component to camera"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        cam = context.scene.camera
        if not cam:
            self.report({'WARNING'}, "No active camera found in scene.")
            return {'CANCELLED'}
            
        cam_dir = cam.matrix_world.translation.normalized()
        settings = context.scene.surface_inspector
        settings.direction = (cam_dir.x, cam_dir.y, cam_dir.z)
        
        if settings.is_inspected:
            bpy.ops.inspect.run_inspection()
            
        self.report({'INFO'}, f"Aligned inspection direction with camera: ({cam_dir.x:.2f}, {cam_dir.y:.2f}, {cam_dir.z:.2f})")
        return {'FINISHED'}


# ==============================================================================
# 3D VIEWPORT SIDEBAR PANEL
# ==============================================================================

class VIEW3D_PT_surface_inspector(bpy.types.Panel):
    """Industrial Surface Inspector UI panel in 3D Viewport sidebar"""
    bl_label = "Industrial Surface Inspector"
    bl_idname = "VIEW3D_PT_surface_inspector"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Surface Inspector'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.surface_inspector

        # --- BANNER: CURRENT DISPLAY STATE ---
        state_box = layout.box()
        if settings.is_inspected:
            col_state = state_box.column(align=True)
            row_s = col_state.row()
            row_s.label(text="● ACTIVE: INSPECTION MODE", icon='CHECKBOX_HLT')
            sub_col = col_state.column(align=True)
            sub_col.scale_y = 0.85
            sub_col.label(text="Colors: Front(Green) | Back(Red) | Side(Yellow)")
            sub_col.label(text="Arrows: Cyan 3D Normal Vectors")
        else:
            col_state = state_box.column(align=True)
            col_state.label(text="● CURRENT: ORIGINAL CAD MODEL", icon='OBJECT_DATAMODE')
            sub_col = col_state.column(align=True)
            sub_col.scale_y = 0.85
            sub_col.label(text="PBR Machined Steel & Cast Iron Assembly")
            sub_col.label(text="Click below to display inspection analysis")

        # --- SECTION 1: PRIMARY PRESENTATION BUTTONS ---
        act_box = layout.box()
        act_box.label(text="Presentation Controls", icon='PLAY')

        # Large Main Action Buttons
        r_run = act_box.row()
        r_run.scale_y = 1.6
        r_run.operator("inspect.run_inspection", text="▶ Show Inspection (Colors & Arrows)", icon='CHECKMARK')

        r_cad = act_box.row()
        r_cad.scale_y = 1.3
        r_cad.operator("inspect.restore_materials", text="⟲ Reset to Original CAD Model", icon='FILE_REFRESH')

        # Interactive Quick Toggles
        tog_row = act_box.row(align=True)
        arrow_icon = 'HIDE_OFF' if settings.show_arrows else 'HIDE_ON'
        tog_row.operator("inspect.toggle_normals", text="Toggle Arrows", icon=arrow_icon)
        color_icon = 'RESTRICT_COLOR_OFF' if settings.is_inspected else 'RESTRICT_COLOR_ON'
        tog_row.operator("inspect.toggle_colors", text="Toggle Colors", icon=color_icon)

        # --- SECTION 2: DIRECTION PRESETS & SENSORS ---
        preset_box = layout.box()
        preset_box.label(text="Inspection Direction Presets", icon='ORIENTATION_VIEW')
        preset_flow = preset_box.grid_flow(columns=3, align=True)
        for label, code in [("+X Front", "+X"), ("-X Back", "-X"), ("+Y Left", "+Y"), 
                            ("-Y Right", "-Y"), ("+Z Top", "+Z"), ("-Z Bottom", "-Z"),
                            ("ISO View", "ISO")]:
            op = preset_flow.operator("inspect.preset_direction", text=label)
            op.preset = code
        preset_box.operator("inspect.align_camera", text="Align with Active Camera", icon='CAMERA_DATA')

        # Direction Sliders
        col_dir = preset_box.column(align=True)
        col_dir.label(text="Custom Inspection Vector (V):")
        col_dir.prop(settings, "direction", text="")

        # --- SECTION 3: THRESHOLD & ARROWS SETTINGS ---
        param_box = layout.box()
        param_box.label(text="Threshold & Arrow Settings", icon='PREFERENCES')
        param_box.prop(settings, "threshold", text="Threshold (T)", slider=True)
        
        t_note = param_box.column(align=True)
        t_note.scale_y = 0.8
        t_note.label(text=f"• Front: Dot > +{settings.threshold:.2f} (Green)")
        t_note.label(text=f"• Back:  Dot < -{settings.threshold:.2f} (Red)")
        t_note.label(text=f"• Side:  |Dot| ≤ {settings.threshold:.2f} (Yellow)")

        arrow_row = param_box.row(align=True)
        arrow_row.prop(settings, "arrow_scale", text="Arrow Length")
        arrow_row.prop(settings, "arrow_subsample", text="Density Step")

        # --- SECTION 4: REAL-TIME STATISTICS ---
        stat_box = layout.box()
        stat_box.label(text="Quality & Orientation Statistics", icon='INFO')
        if settings.stat_total_faces > 0:
            col_stat = stat_box.column(align=True)
            col_stat.label(text=f"Total Polygons Analyzed: {settings.stat_total_faces}")
            stat_box.separator()
            stat_box.label(text=f"● FRONT-FACING: {settings.stat_front_faces} ({settings.stat_front_pct:.1f}%)", icon='COLOR_GREEN')
            stat_box.label(text=f"● BACK-FACING:  {settings.stat_back_faces} ({settings.stat_back_pct:.1f}%)", icon='COLOR_RED')
            stat_box.label(text=f"● SIDE-FACING:  {settings.stat_side_faces} ({settings.stat_side_pct:.1f}%)", icon='COLOR_YELLOW')
            stat_box.separator()
            sum_check = settings.stat_front_faces + settings.stat_back_faces + settings.stat_side_faces
            c_box = stat_box.box()
            c_box.scale_y = 0.85
            if sum_check == settings.stat_total_faces:
                c_box.label(text=f"✓ 100% Verified: {sum_check}/{settings.stat_total_faces} Polygons", icon='CHECKBOX_HLT')
            c_box.label(text=f"3D Normal Arrows Generated: {settings.stat_arrow_count}", icon='ARROW_LEFTRIGHT')
        else:
            stat_box.label(text="Status: Ready in Original CAD Mode", icon='DOT')
            stat_box.label(text="Click 'Show Inspection' to analyze faces.")

        # --- SECTION 5: CSV AUDIT REPORT ---
        csv_box = layout.box()
        csv_box.label(text="CSV Quality Report", icon='EXPORT')
        csv_box.prop(settings, "csv_export_path", text="")
        csv_row = csv_box.row()
        csv_row.scale_y = 1.1
        csv_row.operator("inspect.export_csv", text="Export CSV Quality Report", icon='TEXT')


# ==============================================================================
# REGISTRATION
# ==============================================================================

CLASSES = [
    SurfaceInspectionSettings,
    INSPECT_OT_run_inspection,
    INSPECT_OT_restore_materials,
    INSPECT_OT_toggle_normals,
    INSPECT_OT_toggle_colors,
    INSPECT_OT_reset_visualization,
    INSPECT_OT_export_csv,
    INSPECT_OT_preset_direction,
    INSPECT_OT_align_camera,
    VIEW3D_PT_surface_inspector,
]

def register():
    for cls in CLASSES:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass  # Already registered
            
    bpy.types.Scene.surface_inspector = bpy.props.PointerProperty(type=SurfaceInspectionSettings)


def unregister():
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except ValueError:
            pass
            
    if hasattr(bpy.types.Scene, "surface_inspector"):
        del bpy.types.Scene.surface_inspector


if __name__ == "__main__":
    register()
