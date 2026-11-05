# 3D Industrial Component Surface Inspection Using Polygon Normals

> **Computer Graphics Microproject**  
> **Candidate:** RASHMI  
> **Registration Number:** 2411021061295  
> **Department:** Department of Information Technology (IT)  
> **Institution:** Alliance School of Advanced Computing, Alliance University (NAAC Grade A+ Accredited)  
> **Academic Year:** 2026  
> **Software Environment:** Blender 5.0.1 (Python API / `bpy`, `bmesh`, `mathutils`)  
> **Repository:** [Rashmigowda1206/Computer_Graphics_Microproject](https://github.com/Rashmigowda1206/Computer_Graphics_Microproject)  

---

<p align="center">
  <img src="alliance_university_logo.png" alt="Alliance University - NAAC Grade A+" width="520"/>
</p>

<p align="center">
  <img src="poster_inspected_transparent.png" alt="3D Component Surface Inspection Hero Render" width="700"/>
</p>

---

## 1. Project Abstract
Surface orientation verification is a foundational quality-assurance stage in industrial automated manufacturing and robotic optical inspection. Before physical components (such as valve bodies, gearbox housings, and flanged pipe connectors) can be measured by coordinate-measuring machines (CMMs) or scanned with laser profilometers, an inspection system must determine which polygon facets are oriented toward the optical sensor, which are obscured or facing away, and which lie at glancing edge-on angles.

This microproject develops an interactive **3D Industrial Component Surface Inspection System** implemented directly inside **Blender 5.0.1** using Python (`bpy`). The system calculates polygon surface normals from first principles via the vector cross product, transforms them rigorously into world space using the inverse-transpose of the transformation matrix, and classifies surface orientation relative to a configurable inspection vector via the vector dot product. Front-facing surfaces are rendered in **Green**, back-facing surfaces in **Red**, and glancing/side-facing surfaces in **Yellow**, accompanied by high-performance **Cyan 3D normal vector arrows** and automated **CSV quality report generation**.

---

## 2. Problem Statement & Objective
In computer-aided manufacturing (CAM) and automated optical inspection (AOI), sensors must identify surface visibility and orientation:
- **Challenge:** Raw 3D CAD meshes contain thousands of arbitrary polygons. As components rotate on assembly conveyors or robotic turntables, the surface facets facing the optical sensor continually change.
- **Objective:**
  1. Calculate polygon surface normals using vector geometry.
  2. Transform normal vectors to world space accurately under translation, rotation, and non-uniform scaling using $(M_{3\times 3}^{-1})^T$.
  3. Classify polygon faces into disjoint categories: **FRONT-FACING**, **BACK-FACING**, and **SIDE-FACING** relative to an inspection vector $\vec{V}$ using an angular threshold $T$.
  4. Provide a non-destructive color-coding visualization and 3D normal vector arrows.
  5. Build an interactive Blender sidebar dashboard for parameter tuning, preset views, statistical tracking, and CSV export.

> **Crucial Distinction:** This project inspects **geometric surface orientation** relative to a viewing or sensor direction. It identifies surface facet visibility and alignment; it does **not** independently detect microscopic physical flaws such as metallurgical cracks, inclusions, or scratches unless paired with tactile or photometric sensors.

---

## 3. Mathematical Foundations & Computer Graphics Theory

```
                   World-Space Polygon Normal N
                                ^
                                |      Inspection Direction V
                                |      /
                                |     /  Angle θ
                                |    /
                         +---------------+
                         | Polygon Face  |  Dot Product: D = N · V = cos(θ)
                         +---------------+
```

### 3.1. Polygon Surface Normal (Vector Cross Product)
For any polygon face defined by ordered vertices $P_0, P_1, P_2, \dots$ in counter-clockwise winding order (right-hand rule):
Two coplanar edge vectors spanning the facet are:
$$\vec{E}_1 = P_1 - P_0 = (x_1 - x_0, \; y_1 - y_0, \; z_1 - z_0)$$
$$\vec{E}_2 = P_2 - P_0 = (x_2 - x_0, \; y_2 - y_0, \; z_2 - z_0)$$

The unnormalized surface normal $\vec{N}_{\text{local}}$ is the vector cross product:
$$\vec{N}_{\text{local}} = \vec{E}_1 \times \vec{E}_2 = \begin{vmatrix} \mathbf{i} & \mathbf{j} & \mathbf{k} \\ E_{1x} & E_{1y} & E_{1z} \\ E_{2x} & E_{2y} & E_{2z} \end{vmatrix}$$

$$\vec{N}_{\text{local}} = \begin{pmatrix} E_{1y}E_{2z} - E_{1z}E_{2y} \\ E_{1z}E_{2x} - E_{1x}E_{2z} \\ E_{1x}E_{2y} - E_{1y}E_{2x} \end{pmatrix}$$

Normalized unit normal:
$$\hat{N}_{\text{local}} = \frac{\vec{N}_{\text{local}}}{\|\vec{N}_{\text{local}}\|}$$

---

### 3.2. World-Space Normal Transformation (The Normal Matrix)
In 3D computer graphics, vertices transform according to the $4 \times 4$ model matrix $M$:
$$P_{\text{world}} = M \cdot P_{\text{local}}$$

However, surface normals are *covariant vectors* representing directional planes. Under non-uniform scaling (e.g. scaling by $(1.0, 3.0, 0.5)$), simply multiplying $\hat{N}$ by $M$ causes the transformed vector to lose its $90^\circ$ orthogonality to the surface.
The mathematically rigorous transformation requires the **inverse-transpose** of the upper $3 \times 3$ model matrix:
$$M_{\text{normal}} = (M_{3 \times 3}^{-1})^T$$
$$\vec{N}_{\text{world}} = M_{\text{normal}} \cdot \hat{N}_{\text{local}}$$
$$\hat{N}_{\text{world}} = \frac{\vec{N}_{\text{world}}}{\|\vec{N}_{\text{world}}\|}$$

Our code implements this exact transformation:
```python
normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
normal_world = (normal_matrix @ poly.normal).normalized()
```

---

### 3.3. Dot Product Orientation Classification
Let $\hat{V}$ be the normalized inspection direction vector ($\|\hat{V}\| = 1$).
The dot product between the surface normal $\hat{N}_{\text{world}}$ and the inspection direction $\hat{V}$ is:
$$D = \hat{N}_{\text{world}} \cdot \hat{V} = N_x V_x + N_y V_y + N_z V_z = \cos(\theta)$$
where $\theta$ is the spatial angle between the surface normal and the inspection sensor vector.

Using an adjustable threshold $T \in [0, 1)$ (default $T = 0.30$, corresponding to $\theta \approx 72.5^\circ$):

| Classification | Condition | Geometric Meaning | Visualization Color |
| :--- | :--- | :--- | :--- |
| **FRONT-FACING** | $D > +T$ | Surface points directly toward the sensor ($\theta < 72.5^\circ$) | **Green** |
| **BACK-FACING** | $D < -T$ | Surface points directly away from the sensor ($\theta > 107.5^\circ$) | **Red** |
| **SIDE-FACING** | $-T \le D \le T$ | Surface is glancing or edge-on ($72.5^\circ \le \theta \le 107.5^\circ$) | **Yellow** |

Every polygon belongs to **exactly one** category:
$$\text{Total Faces} = N_{\text{front}} + N_{\text{back}} + N_{\text{side}}$$

---

## 4. Industrial Component Model Details
The 3D component is a precision **Industrial Flanged Valve Housing / Gearbox Connector** designed with a rich mixture of geometric surface types:
1. **Gearbox_Valve_Housing:** Main vertical cast-iron chamber with stepped cylindrical collars, internal bores, and dual horizontal pipe sections with heavy circular connection flanges and 4 angled triangular gusset stiffener ribs.
2. **Base_Mounting_Plate:** Machined steel mounting base with beveled corners, recessed pads, and anchor holes.
3. **Top_Inspection_Cover:** Circular top hatch with knurled cap and central hex boss.
4. **Flange_Mounting_Bolts:** 22 high-tensile hexagonal fasteners (6 left flange, 6 right flange, 6 top cover, 4 base plate) with 12-sided circular washers and 6-sided hex heads.

```
Total Inspectable Objects: 4
Total Polygon Faces:       826
Flat Faces:                Flange faces, base plate, gusset sides, bolt tops
Curved Faces:              Pipe cylinders, flange rims, neck collars
Angled Faces:              Gusset rib slopes, chamfer bevels
Multi-directional Faces:   Hex bolt facets (60° rotational increments)
```

---

## 5. Scene Organization (Collections)
The Blender scene is organized into clean, dedicated collections:
- `Industrial_Component`: Contains the 4 inspectable component meshes (`Gearbox_Valve_Housing`, `Base_Mounting_Plate`, `Top_Inspection_Cover`, `Flange_Mounting_Bolts`).
- `Inspection_Visualization`: Houses the unified 3D cyan normal vector arrow mesh (`Normal_Vectors_Visualizer`).
- `Inspection_Labels`: Reserved for 3D annotations and text markers.
- `Lighting_and_Cameras`: 3-Point studio lighting rig (Key Light 650W, Fill Light 280W, Rim Backlight 450W) and framed inspection camera.
- `Inspection_Dashboard_Assets`: Staging platform pedestal (`Studio_Staging_Pedestal`).

---

## 6. Sidebar Dashboard Interface & Controls

To access the dashboard in Blender:
1. Open `Industrial_Surface_Inspection.blend` in Blender 5.0.1.
2. In the **3D Viewport**, press <kbd>N</kbd> to toggle the sidebar.
3. Click on the **Surface Inspector** tab.

```
+-------------------------------------------------------+
|  INDUSTRIAL SURFACE INSPECTOR                         |
|  CG Concept: Surface Normals & Dot Product            |
+-------------------------------------------------------+
| [1. Inspection Parameters]                            |
|   Inspection Vector (V): [X: 0.00] [Y: -0.93] [Z: 0.37]|
|   Presets: [+X] [-X] [+Y] [-Y] [+Z] [-Z] [ISO]        |
|   [Align with Camera]                                 |
|   Threshold (T): [ 0.30 ]                             |
|     - Front: D > +0.30 (Green)                        |
|     - Back:  D < -0.30 (Red)                          |
|     - Side:  |D| <= 0.30 (Yellow)                     |
|   Arrow Size: [0.35]   Density Step: [2]              |
+-------------------------------------------------------+
| [2. Inspection Actions]                               |
|   [ RUN SURFACE INSPECTION ] (Large button)           |
|   [ Toggle Normal Arrows ]                            |
|   [ Restore Materials ]   [ Reset All ]               |
+-------------------------------------------------------+
| [3. Inspection Statistics]                            |
|   Inspected Meshes: 4    Total Polygons: 826          |
|   ● FRONT-FACING: 305 (36.9%)                         |
|   ● BACK-FACING:  305 (36.9%)                         |
|   ● SIDE-FACING:  216 (26.2%)                         |
|   ✓ Sum Verification: 826/826 (100.0%)               |
|   Cyan Normal Arrows Displayed: 413                   |
+-------------------------------------------------------+
| [4. CSV Quality Report]                               |
|   Path: [ //inspection_report.csv ]                   |
|   [ Export CSV Report ]                               |
+-------------------------------------------------------+
```

### Explanation of Controls:
- **Inspection Vector (V):** Sets the 3D unit vector representing the inspection sensor line-of-sight.
- **Preset Buttons (+X, -X, +Y, -Y, +Z, -Z, ISO):** Instantly sets standard orthographic and isometric viewing directions.
- **Align with Camera:** Grabs the active viewport camera position in world space and aligns the inspection vector with the camera optical line-of-sight.
- **Threshold Slider ($T$):** Adjusts sensitivity between Front, Back, and Side classifications.
- **Arrow Size & Density Step:** Controls the 3D length of normal arrows and subsampling rate (e.g. 1 arrow every 2 faces) to guarantee maximum viewport framerate.
- **Run Surface Inspection:** Calculates world normals, performs dot product classification, applies Green/Red/Yellow materials, generates 3D normal arrows, and updates statistics.
- **Toggle Normal Arrows:** Instantly shows or hides the cyan normal vector arrows in the viewport.
- **Restore Materials:** Restores the original brushed steel, cast-iron, and galvanized bolt materials non-destructively.
- **Export CSV Report:** Generates an engineering quality control report on disk.

---

## 7. Sample Step-by-Step Inspection Procedure
1. **Open Project:** Launch Blender 5.0.1 and open `Industrial_Surface_Inspection.blend`.
2. **Examine Scene:** The model opens in Material Preview mode with initial inspection colors (Green, Red, Yellow) and cyan 3D arrows visible.
3. **Orbit Viewport:** Middle-click and drag to rotate the 3D view. Notice how normal arrows clearly indicate the geometric perpendiculars of the cylindrical faces, flange rims, and hex bolt caps.
4. **Change Direction:** In the sidebar panel (`N` key -> `Surface Inspector`), click the `+Z` preset button.
5. **Observe Real-Time Update:** 
   - All horizontal top surfaces (top cover, flange tops, base plate top) immediately turn **Green** ($D > 0.30$).
   - All bottom downward-facing surfaces turn **Red** ($D < -0.30$).
   - All vertical cylinder walls turn **Yellow** ($|D| \le 0.30$).
6. **Adjust Threshold:** Move the threshold slider to `0.10` and click `Run Surface Inspection`. Observe how the yellow band narrows as the criteria for edge-on faces tightens.
7. **Toggle Normals:** Click `Toggle Normal Arrows` to hide/show the cyan arrows.
8. **Restore Original Materials:** Click `Restore Materials` to inspect the realistic metallic PBR materials.
9. **Export CSV:** Click `Export CSV Report` to produce `inspection_report.csv`.

---

## 8. Exported CSV Report Format
The exported file contains comprehensive metadata and per-polygon classification rows:
```csv
# 3D Industrial Component Surface Inspection Report
# CG Concept: Surface Normals & Dot Product Classification
# Total Faces: 826,Front: 305 (36.9%),Back: 305 (36.9%),Side: 216 (26.2%)
# Direction: (0.000, -0.928, 0.371),Threshold: 0.30

Object_Name,Polygon_Index,Classification,Dot_Product,Normal_X,Normal_Y,Normal_Z,InspectDir_X,InspectDir_Y,InspectDir_Z,Threshold
Gearbox_Valve_Housing,0,FRONT,0.8721,0.0000,-0.9914,-0.1305,0.0000,-0.9285,0.3714,0.30
Gearbox_Valve_Housing,1,FRONT,0.7157,0.0000,-0.9239,-0.3827,0.0000,-0.9285,0.3714,0.30
Gearbox_Valve_Housing,2,BACK,-0.9205,0.1305,0.9914,0.0000,0.0000,-0.9285,0.3714,0.30
Gearbox_Valve_Housing,3,SIDE,-0.2470,0.0000,-0.1305,-0.9914,0.0000,-0.9285,0.3714,0.30
...
```

---

## 9. File Structure & Deliverables

```
Computer_Graphics_Microproject/
├── Industrial_Surface_Inspection.blend   # Master Blender 5.0.1 project file (starts in Original CAD)
├── surface_inspection.py                 # Core normal math, transformation, and classification
├── inspection_dashboard.py               # Blender UI panel, interactive operators, and presets
├── run_inspector.py                      # One-click startup and auto-registration script
├── main.py                               # Master scene builder & CAD generator script
├── setup_presentation.py                 # Presentation configuration script
├── inspection_report.csv                 # Exported quality inspection CSV report
├── Demo_Presentation_Video.mp4           # Complete demonstration video of the project in Blender
├── Presentation.ppt                      # Presentation deck (.ppt format)
├── Presentation_Deck.html                # Interactive slide deck
├── Project_Report.doc                    # Comprehensive formal project report (.doc format)
├── Project_Report.md                     # Markdown project report
├── Poster_A3_Landscape.pdf               # ISO A3 Landscape Print-ready vector PDF (420 x 297 mm)
├── Poster_A3_Landscape_300DPI.png        # 300 DPI high-definition print poster (4963 x 3509 px)
├── Poster_A3_Landscape.html              # Interactive A3 web poster
├── alliance_university_logo.png          # Official Alliance University NAAC Grade A+ emblem
├── screenshots/                          # High-resolution multi-angle 3D working renders
└── README.md                             # Comprehensive microproject documentation
```

---

## 10. Technical Specifications & Software
- **Software:** Blender 5.0.1 (Windows x64)
- **API:** Blender Python API (`bpy`, `bmesh`, `mathutils`)
- **Graphics Pipeline:** EEVEE / Material Preview with Principled BSDF nodes
- **Draw Calls:** Single unified mesh for normal arrows (optimal GPU performance)
- **Mathematical Integrity:** Verified 100% face sum invariance ($N_{\text{front}} + N_{\text{back}} + N_{\text{side}} \equiv N_{\text{total}}$).
