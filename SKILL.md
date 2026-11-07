---
name: cadquery
description: >-
  REQUIRED whenever writing, generating, modifying, inspecting, or debugging CadQuery Python code,
  3D CAD models, or using the CadQuery MCP server. Contains idiomatic BRep modeling patterns,
  workplane positioning, and selector cheat sheets.
---

# CadQuery LLM Skill

This skill helps LLMs write correct, idiomatic CadQuery code.
Load this file before any CadQuery task. For deeper reference, read the files listed at the bottom.

---

## Two APIs — Know Which One You're Using

CadQuery provides two distinct APIs. Always identify which is appropriate before writing code.

### Fluent (Workplane) API
```python
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10).faces(">Z").hole(3)
```
- Chains operations on a `Workplane` object with hidden state (current plane, stack)
- Best for: parts built up from sketches and feature operations (extrude, hole, fillet, shell)
- Most tutorials and examples use this style

### Free Function API
```python
from cadquery.func import *
b = box(10, 10, 10)
result = b - cylinder(1.5, 10)
```
- No hidden state — all operations are explicit free functions
- Selectors still work as methods on Shape objects
- Boolean ops available as operators: `+` (union), `-` (cut), `*` (intersect), `/` (split)
- Best for: complex face-by-face construction, lofted/swept surfaces, avoiding booleans via `addHole()`/`replace()`, parametric surface mapping
- More verbose but more explicit and composable

**Do not mix the two styles in the same script** unless you explicitly convert between them.
When the task involves building shapes face-by-face, lofting between non-planar edges, or
trimming surfaces in parametric space — prefer the Free Function API.

---

## The Core Mindset: BRep, Not CSG

CadQuery uses **Boundary Representation (BRep)**: a model is defined by its surfaces, edges, and vertices — not by Boolean operations on primitives.

The CSG reflex (union/cut everything) produces brittle, unidiomatic code. The BRep reflex asks:
- What faces, edges, or vertices already exist on this shape?
- Can I select them and build from there?
- Does a workplane operation (extrude, shell, fillet, chamfer) get me there without a Boolean?

**Wrong reflex (CSG):**
```python
result = base.union(cq.Workplane().box(10, 10, 5).translate((0, 0, 10)))
```

**Right reflex (BRep):**
```python
result = base.faces(">Z").workplane().rect(10, 10).extrude(5)
```

Only reach for `.union()`, `.cut()`, or `.intersect()` when you genuinely need to combine separate solids.

---

## Workplanes

A workplane is a local 2D coordinate system. Most geometry is created relative to it.

```python
import cadquery as cq

# Start on XY plane at origin
wp = cq.Workplane("XY")

# Build a solid to work from
cube = cq.Workplane("XY").box(10, 10, 10)

# Move to a face
wp2 = cube.faces(">Z").workplane()

# Offset from a face
wp3 = cube.faces(">Z").workplane(offset=5)

# Arbitrary origin and normal — must use cq.Plane, not keyword args on Workplane
wp4 = cq.Workplane(cq.Plane(origin=(0, 0, 10), normal=(0, 1, 0)))

# Move with transformation (rotate is degrees around local X, Y, Z)
wp5 = cube.faces(">Z").workplane().transformed(offset=(1, 2, 3), rotate=(0, 0, 45))
```

**Rules:**
- `.workplane()` resets the 2D origin to the center of the selected face/edge by default.
- `centerOption` controls what "center" means — the default `"ProjectedOrigin"` projects the parent workplane origin onto the new face, which is often not the face center. Always set it explicitly when position matters.
- After `.workplane()`, coordinates are **local** to that plane, not global.
- `.transformed()` is cumulative within the current workplane context.
- Named planes follow the right-hand cross product ($\text{local } X \times \text{local } Y = \text{normal}$): forward cyclic planes `"XY"`, `"YZ"`, and `"ZX"` have `+Z`, `+X`, and `+Y` normals, whereas `"XZ"` has a **`-Y` normal** (positive extrusions go in `-Y`). On `"ZX"`, local X is `+Z` and local Y is `+X`, so 2D coordinates are written `(z, x)`.

---

## Selectors — Cheat Sheet

Selectors filter faces, edges, wires, or vertices from the current stack.

| Selector | Meaning |
|----------|---------|
| `">Z"` | Face/edge with highest Z centroid |
| `"<Z"` | Face/edge with lowest Z centroid |
| `"\|X"` | Faces whose normal is parallel to X axis |
| `"#Z"` | Faces/edges whose normal or direction is orthogonal to Z |
| `"+Z"` | Faces whose normal points in +Z direction |
| `">>Z[1]"` | Second item when sorted ascending by Z (0-indexed) |
| `"<<Z[0]"` | First item when sorted descending by Z |
| `"%Plane"` | Faces of type Plane (vs Cylinder, Cone, etc.) |
| `"not >Z"` | Inverts the selector |
| `">Z and \|X"` | Combines selectors (AND) |
| `">Z or <Z"` | Combines selectors (OR) |

**Tag-based selection (preferred for stability):**
```python
result = (
    cq.Workplane("XY")
    .box(10, 10, 10)
    .faces(">Z").tag("top")
    .end()
    .faces(tag="top").workplane().hole(3)
)
```

The code above demonstrates how to use tags, and is not a suggestion of the proper way to use them.
In practices you would not call `end` and then query the tagged face immediately again.
Use tags when the geometry might need to be referred to later, and may become hard to access.
Tagging can be very useful, but do not force it in to the script unless it seems needed.

---

## Critical Anti-Patterns


### 1. Boolean when a feature operation suffices
| Instead of... | Use... |
|--------------|--------|
| `.cut(cylinder)` | `.faces(...).hole(d)` |
| `.cut(shell_solid)` | `.shell(thickness)` |
| `.union(chamfered_edge)` | `.edges(...).chamfer(d)` |

### 2. workplane `centerOption` behaviors 
By default, a `workplane()` call uses `ProjectedOrigin` as the default, which uses the current origin and projects it onto the plan defined by the selected faces.
This usually works, but can cause unintended results sometimes.
If the geometric center of the object is the indended center for the operation, it can sometimes be better to use `CenterOfBoundBox`, which uses the X, Y and Z centers of the object's bounding box.
If the user mentions that the features added on the workplane are not in the expected position, one cause could be this `centerOption` parameter.
```python
# Explicit is always better
cq.Workplane("XY").box(10, 10, 5).faces(">Z").workplane(centerOption="CenterOfBoundBox")
```

### 3. Selector ordering assumptions
Selectors like `">>Z[1]"` depend on sort order across all matching entities. Adding fillets or other features changes the entity count and can shift indices. Prefer tags or geometric selectors (`">Z"`) over index-based ones.

### 4. Unclosed wires
When building profiles with `.lineTo()`, `.spline()`, etc., always call `.close()` before `.extrude()` or `.revolve()` unless the wire is intentionally open.

### 5. Forgetting `.end()` after tagging or selector context
After `.tag()` or navigating into a sub-context, use `.end()` to return to the solid before chaining further operations.

### 6. `BREP_API command not done`
This OpenCASCADE kernel error means the requested geometry is invalid. Common causes:
- Fillet/chamfer radius larger than the shortest adjacent edge, or adjacent fillets overlapping — reduce the radius or fillet edge groups separately
- Self-intersecting profile (wire crosses itself, revolve profile crosses the axis)
- Sweep profile too large for the path curvature — the solid folds back on itself
- Shell thickness larger than the local radius of curvature

See `patterns/anti-patterns.md` #14 for detailed fixes.

### 7. Reverse-ordered `"XZ"` workplane normal (`-Y`) and `"ZX"` axis swap
`cq.Workplane("XZ")` sets local X = `+X` and local Y = `+Z`, so the right-hand rule ($X \times Z = -Y$) points the normal in **`-Y`** — causing positive extrusions and offsets to travel backward along the Y axis. For a **`+Y`** normal, use the forward cyclic plane `cq.Workplane("ZX")` (noting that local 2D coordinates on `"ZX"` are `(z, x)`), or select an existing face with `.faces(">Y").workplane()`. See `concepts/workplanes.md` and `patterns/anti-patterns.md` #15.

---

## Free Function API — Quick Reference

Import: `from cadquery.func import *`

**Primitives:**
```python
box(w, h, d)
cylinder(r, h)
sphere(r)
cone(r1, r2)
plane(w, h)          # flat face
circle(r)            # edge
rect(w, h)           # edge
segment((x1,y1,z1), (x2,y2,z2))
```

**Shape assembly:**
```python
wire(e1, e2, ...)         # edges → wire
face(wire)                # closed wire → face
solid(f1, f2, ...)        # faces → solid
shell(f1, f2, ...)        # faces → shell (open solid)
compound(s1, s2, ...)     # shapes → compound
```

**Operations:**
```python
extrude(profile, direction_vector)
loft(e1, e2, e3, cap=False)
sweep(profile, path)
revolve(face, axis_point, axis_dir, angle)
```

**Placement (no workplane needed):**
```python
shape.moved(x=1, y=2, z=3)           # translate
shape.moved(rx=90, ry=0, rz=45)      # rotate (degrees)
shape.moved((1,0,0), (0,1,0))        # place at multiple locations → compound
shape.move(z=5)                       # in-place variant
```

**Boolean operators:**
```python
a + b      # fuse / union
a - b      # cut / difference
a * b      # intersect
a / plane  # split
```

**Adding features without booleans (preferred for performance):**
```python
top = solid.faces(">Z")
inner = extrude(circle(r), (0, 0, h))
top_with_hole = top.addHole(inner.edges("<Z"))
result = solid(solid.remove(top).faces(), inner, top_with_hole)
```

**Selectors work the same way** — they are methods on Shape objects, not tied to either API.

---

## `.shell()` and Hollow Bodies

Shell operates on the existing solid — select the face(s) to open, then shell:

```python
box = cq.Workplane("XY").box(20, 20, 20)
hollow = box.faces(">Z").shell(-2)  # negative = inward
```

Common mistake: calling `.shell()` without first selecting which face to remove, resulting in a fully closed thin shell (usually not what you want).

### Shell & Fillet Ordering Rules (OpenCASCADE Kernel)
OpenCASCADE's offset algorithm in `.shell(-t)` will self-intersect and throw `BRep_API: command not done` if thin features or tight radii are present before shelling:
1. **Shell the main form before adding thin features**: Any feature thinner than $2 \times \text{wall\_thickness}$ (e.g., alignment lips, snap hooks, internal ribs, screw bosses) cannot be hollowed inside itself. Shell the primary outer body first, then union or extrude thin features onto the shelled solid.
2. **Large outer fillets ($R > \text{wall\_thickness}$) go BEFORE `.shell(-t)`**: Applying large structural fillets prior to shelling allows the inner wall to follow the outer contour with a concentric inner radius of $R - t$ (maintaining constant wall thickness).
3. **Small edge-break fillets ($R \le \text{wall\_thickness}$) go AFTER `.shell(-t)`**: If applied before `.shell(-t)`, offsetting a radius $R \le t$ inward by $t$ collapses the inner surface into a zero- or negative-radius crease and fails.

---

## OpenCASCADE (OCCT) Kernel Hygiene & Boolean Rules

*Adapted from [CNCKitchen/ScanRuler](https://github.com/CNCKitchen/ScanRuler) OpenCASCADE modeling guidelines.*

1. **Round 3-edge corners in a single `.fillet()` call**:
   - When three edges meet at a vertex, pass all three to a single `.fillet(r)` call so OCCT constructs a unified corner patch.
   - Sequential `.fillet()` calls on meeting edges force the second fillet to run along the tangent seam of the first, frequently failing with `BRep_API: command not done`. If two meeting edges require different radii ($R_{\text{big}}$ and $R_{\text{small}}$), fillet the continuous chain with $R_{\text{big}}$ first so the cross edge inherits a smooth tangent transition, then fillet with $R_{\text{small}}$.
2. **Never fillet across or end on a shallow crease ($1^\circ\text{--}5^\circ$)**:
   - Adjacent faces meeting at a $1^\circ\text{--}5^\circ$ dihedral angle cause OCCT's fillet spine tracker to fail (`ChFi3d_Builder: chamfer or fillet not computable`). Replace nearly-collinear polyline segments in sketches with a single tangent arc or spline.
3. **Embed bosses, ribs, and helper bodies $\sim 0.5\text{ mm}$ into parent skins**:
   - Starting an extrusion or boolean helper flush on a curved or angled outer skin creates a zero-thickness grazing intersection and leaves micron-wide sliver faces ($< 0.01\text{ mm}^2$) that break downstream fillets. Start the feature $\sim 0.5\text{ mm}$ inside the parent solid so the boolean intersection is clean.
4. **Avoid tangent knife-edges ($\ge 0.05\text{ mm}$ overlap)**:
   - Never union or cut a cylinder that is exactly tangent to a planar face (a zero-thickness line contact). Overlap the cylinder into the wall by $\ge 0.05\text{ mm}$ or bridge it with a fillet so STEP round-trip export does not drop faces.
5. **Revolve axis hygiene**:
   - Profiles passed to `.revolve()` must terminate cleanly **on** the revolve axis ($x = 0$), never crossing to the negative side (self-intersecting solid).
   - When revolving a dome or rounded cap, place the arc's center **on** the revolve axis so the profile meets the axis at $90^\circ$; an off-axis arc meets the pole at an angle and creates a degenerate vertex or dimple that breaks `.shell()` and `.fillet()`.

---

## Visual Inspection & MCP Rendering Guidelines

When inspecting models with the CadQuery MCP server:
- **Shaded 3D PNG (`image_format="png"`)**:
  - Uses offscreen VTK rendering.
  - By default, boundary and feature edge outlines (`show_edges=True`) are rendered on top of shaded faces so chamfers, fillets, and planar top surfaces maintain crisp visual definition rather than washing out under diffuse lighting.
- **Technical Vector SVG (`image_format="svg"`)**:
  - Computes hidden-line removal (HLR) directly from OCC geometry.
  - Generates an opaque card background (`background_card=True`) inside the `<svg>` root tag so black technical strokes remain visible across both dark and light UI themes.
- **Multi-View & Contact Sheet (`multi_view=True`, `contact_sheet=True`)**:
  - `multi_view=True` emits isometric, front, top, and right views in a single call.
  - `contact_sheet=True` composites the 4 standard views into a single labeled $2 \times 2$ grid PNG for rapid visual alignment checks.
- **2D Cross-Section Slicing (`section_axis="X"|"Y"|"Z"`, `section_offset=0.0`)**:
  - Slices the BRep solid with a plane in `render` or `inspect` and renders a 2D millimeter-grid SVG cross-section (plus wire loop counts and bounds) to verify internal wall thicknesses, counterbores, and clearances.
- **Topology Audit & STL Reverse-Engineering (`inspect`, `analyze_stl`, `compare_mesh`)**:
  - Always check `inspect` output for `Is Valid: True`, `Solids: 1` (no accidental multi-body split), `Closed Shells`, and zero sliver faces ($< 0.01\text{ mm}^2$) or short edges ($< 0.1\text{ mm}$).
  - When reverse-engineering a CAD-exported STL, use `analyze_stl` to extract exact planes, cylinders, cones, circles, and axis-aligned step heights, and `compare_mesh` to compute Hausdorff/chamfer surface deviation against the rebuilt CadQuery solid.
- **Local Module Imports**:
  - Prepend `sys.path.insert(0, os.path.abspath("."))` when rendering models that import local project modules (`from src.params import ...`).

---

## For Deeper Reference

| Topic | File |
|-------|------|
| BRep vs CSG concepts | `concepts/brep-mindset.md` |
| Visual inspection & rendering | `concepts/visual-inspection-and-rendering.md` |
| Workplane (fluent) API | `concepts/workplanes.md` |
| Free Function API | `concepts/free-function-api.md` |
| Full selector reference | `concepts/selectors.md` |
| Idiomatic patterns | `patterns/common-patterns.md` |
| Anti-patterns (extended) | `patterns/anti-patterns.md` |
| Annotated examples | `examples/` |
| CadQuery API reference | `docs/` |

When working on a CadQuery task:
1. Read this file first.
2. If the task involves selectors, read `concepts/selectors.md`.
3. Grep `examples/` for methods you're unsure about: `grep -rn "\.shell\(" examples/`
4. Grep `docs/` for API signatures: `grep -n "def shell" docs/`
