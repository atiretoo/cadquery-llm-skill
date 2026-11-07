# Visual Inspection & Rendering Guidelines

When generating, modifying, or verifying 3D CAD models using CadQuery and the CadQuery MCP server, visual inspection is essential to verify feature positioning, fillet/chamfer transitions, and overall proportions.

---

## 1. CadQuery MCP Server Rendering Options

The CadQuery MCP server provides a `render` tool with two primary output formats:

### Shaded 3D PNG (`image_format="png"`)
- Renders an offscreen shaded 3D model using VTK.
- **Assembly Colors & Materials**: Preserves part colors, transparencies (`alpha`), and relative positions.
- **Edge Definition (`show_edges=True`)**:
  - By default, boundary and feature edge outlines (`edgecolor=(0.15, 0.15, 0.2, 1.0)`) are drawn on top of shaded faces.
  - *Why this matters*: Without edge lines, adjacent planar surfaces (such as top horizontal faces meeting $45^\circ$ entry chamfers or subtle fillets) reflect similar lighting and wash out, losing visual edge definition. Outlines provide clear contrast and depth.
- **Coordinate Triad (`show_axes=True`)**: Displays a colored XYZ triad in the corner to verify orientation.

### Technical Vector Drawing SVG (`image_format="svg"`)
- Computes exact 2D projection and hidden-line removal using OpenCASCADE's HLR algorithm (`cadquery.occ_impl.exporters.svg.getSVG`).
- Produces sharp, scalable line drawings ideal for engineering schematics and architectural views.
- **Dark-Mode Visibility (`background_card=True`)**:
  - In raw SVG, lines are drawn on a transparent background. In dark-mode chat interfaces or IDE viewers, dark strokes blend into dark backgrounds and become invisible.
  - The MCP server includes an opaque card background (`<rect width="100%" height="100%" fill="#ffffff" rx="8" stroke="#cbd5e1" stroke-width="2"/>`) placed directly inside the `<svg>` root tag so drawings remain crisp and readable in any theme.
- **Hidden Lines (`show_hidden=True` / `False`)**:
  - `show_hidden=False` generates clean exterior silhouette and feature lines.
  - `show_hidden=True` renders dashed gray lines for internal cavities, counterbores, and through-holes.

---

## 2. Multi-View Geometric Verification (`multi_view=True`, `contact_sheet=True`)

Single-angle views can conceal depth misalignment, cutouts missing their targets, or reverse-extrusion errors.
- Pass `multi_view=True` to generate four views simultaneously:
  1. **Isometric** (Z-up standard axonometric perspective)
  2. **Front** (XZ plane from $-Y$)
  3. **Top** (XY plane from $+Z$, verifying slot layout and symmetry)
  4. **Right** (YZ plane from $+X$, verifying height profiles and steps)
- Pass `contact_sheet=True` (with `image_format="png"`) to composite all 4 views (`iso`, `front`, `top`, `right`) into a single labeled $2 \times 2$ grid PNG (`contact_sheet.png`) for rapid single-image inspection.

---

## 3. 2D Cross-Section Slicing (`section_axis`, `section_offset`)

Exterior views cannot always verify internal wall thicknesses, blind hole depths, counterbore seating, or mating clearances inside hollow bodies.
- Pass `section_axis="X" | "Y" | "Z"` and `section_offset=<float>` (in mm) to `render` or `inspect`:
  - **`render`**: Slices the model with the specified plane and generates a 2D millimeter-grid SVG (`section_<axis>_<offset>.svg`) showing outer and inner contour loops with coordinate axes and grid lines.
  - **`inspect`**: Reports the number of closed section wires/loops and the 2D bounding box at that slice height.

---

## 4. Importing Workspace Code in MCP

The MCP server executes scripts in an isolated CQGI environment. When rendering or inspecting scripts that import local project packages (e.g. `from src.params import ...`):
```python
import sys, os
sys.path.insert(0, os.path.abspath("."))

from src.my_part import create_my_part
result = create_my_part()
```
Always assign the final shape to `result` or pass shapes to `show_object(shape, options={"color": "lightblue"})`.

---

## 5. Complementing Visuals with `inspect`, `analyze_stl`, and `compare_mesh`

*Adapted from [CNCKitchen/ScanRuler](https://github.com/CNCKitchen/ScanRuler) verification workflows.*

Always combine visual rendering with numerical and topological inspection via the MCP `inspect` tool:
- **Bounding Box & Print Seating**: Verify `bb.xlen`, `bb.ylen`, `bb.zlen`, and `bb.zmin == 0.0`.
- **Single-Solid & Boolean Volume Guard**:
  - Verify `Solids: 1` (if a `.union()` leaves `Solids: 2`, the helper body missed or only grazed the target; if a `.cut()` leaves volume unchanged, the cutter missed the solid).
- **BRep Topology Audit**:
  - Verify `Is Valid: True` (`BRepCheck_Analyzer`), all shells are closed, and there are zero sliver faces (`area < 0.01 mm²` or `area / perimeter < 0.01 mm`) or short edges (`length < 0.1 mm`) that would cause downstream `.fillet()` operations to fail.
- **Reverse-Engineering CAD STLs (`analyze_stl` & `compare_mesh`)**:
  - Use `analyze_stl(stl_path=...)` on tessellated CAD exports to automatically cluster facet normals and recover exact analytic planes, cylinder/cone axes and radii, circular hole centers, and Z-level step heights.
  - Use `compare_mesh(code=..., reference_stl=...)` to tessellate the rebuilt CadQuery solid and compute bidirectional surface deviation (mean, RMS, max/Hausdorff, P95, and `% within tolerance`) against the reference mesh.
