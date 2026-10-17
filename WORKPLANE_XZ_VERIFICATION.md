# Verification: `Workplane("XZ")` vs `Workplane("ZX")` and `Plane.named` Mechanics

## 1. How `cq.Plane` Computes Its Axes (`xDir`, `yDir`, `zDir`)

A `cq.Plane(origin, xDir, normal)` is constructed from an **origin**, a local X direction (**`xDir`**), and a plane normal (**`zDir`**). Inside `Plane._setPlaneDir(xDir)` and `Plane._calcTransforms()` (`cadquery/occ_impl/geom.py`), CadQuery constructs an OpenCASCADE right-handed coordinate system (`gp_Ax3`) and computes the local 2D Y axis (**`yDir`**) via the right-hand cross product:

```python
def _setPlaneDir(self, xDir):
    """Set the vectors parallel to the plane, i.e. xDir and yDir"""
    xDir = Vector(xDir)
    self.xDir = xDir.normalized()
    self.yDir = self.zDir.cross(self.xDir).normalized()
```

Because $\text{yDir} = \text{zDir} \times \text{xDir}$ (equivalently $\text{zDir} = \text{xDir} \times \text{yDir}$), **no right-handed plane in 3D space can simultaneously have `xDir = +X`, `yDir = +Z`, and `zDir (normal) = +Y`**. You can only pick two of the three:

| Definition | `xDir` (Local X) | `yDir` (`zDir × xDir`) | `zDir` (Normal / Extrude) | CadQuery Name |
|---|---|---|---|---|
| `Plane(origin, (1, 0, 0), (0, -1, 0))` | `+X` `(1, 0, 0)` | `+Z` `(0, 0, 1)` | **`-Y` `(0, -1, 0)`** | **`"XZ"`** (or `"bottom"`) |
| `Plane(origin, (0, 0, 1), (0, 1, 0))` | **`+Z` `(0, 0, 1)`** | **`+X` `(1, 0, 0)`** | **`+Y` `(0, 1, 0)`** | **`"ZX"`** |
| `Plane(origin, (1, 0, 0), (0, 1, 0))` | `+X` `(1, 0, 0)` | **`-Z` `(0, 0, -1)`** | **`+Y` `(0, 1, 0)`** | **`"top"`** |

### Why Changing `"XZ"` to `Plane(origin, (1, 0, 0), (0, 1, 0))` Would Break `"XZ"`
In `cq.Plane.named()`, every two-letter plane name `"AB"` guarantees that the **first letter (`A`) is `+xDir`** and the **second letter (`B`) is `+yDir`**:
- If `"XZ"` were changed to `Plane(origin, (1, 0, 0), (0, 1, 0))`, then `yDir = zDir.cross(xDir) = (0, 1, 0) × (1, 0, 0) = (0, 0, -1)` (**`-Z`**). A 2D point `(10, 20)` would map to global `(10, 0, -20)` instead of `(10, 0, 20)`. (CadQuery actually provides `Plane(origin, (1, 0, 0), (0, 1, 0))` under the name `"top"`.)
- Because `"XZ"` must have `xDir = +X` and `yDir = +Z`, its normal is forced by the right-hand rule to be `zDir = -Y`.

### Direct Source-Code Extract (`inspect.getsource(cq.Plane.named)`)
```python
        =========== ======= ======= ======
        Name        xDir    yDir    zDir
        =========== ======= ======= ======
        XY          +x      +y      +z
        YZ          +y      +z      +x
        ZX          +z      +x      +y
        XZ          +x      +z      -y
        YX          +y      +x      -z
        ZY          +z      +y      -x
        front       +x      +y      +z
        back        -x      +y      -z
        left        +z      +y      -x
        right       -z      +y      +x
        top         +x      -z      +y
        bottom      +x      +z      -y
        =========== ======= ======= ======

        namedPlanes = {
            # origin, xDir, normal
            "XY": Plane(origin, (1, 0, 0), (0, 0, 1)),
            "YZ": Plane(origin, (0, 1, 0), (1, 0, 0)),
            "ZX": Plane(origin, (0, 0, 1), (0, 1, 0)),
            "XZ": Plane(origin, (1, 0, 0), (0, -1, 0)),
            "YX": Plane(origin, (0, 1, 0), (0, 0, -1)),
            "ZY": Plane(origin, (0, 0, 1), (-1, 0, 0)),
            ...
        }
```

---

## 2. Pure BRep Fluent Example & Visual Proof (`./assets/`)

Running the **exact same fluent chain** ([examples/workplane_xz_vs_zx.py](examples/workplane_xz_vs_zx.py)) with `.center(10, 0)` on `Workplane("XZ")` vs `Workplane("ZX")` demonstrates both effects simultaneously. Notice the **`Y` (up), `X` (right), and `Z` (front-right)** axis triad in the bottom-left corner of each render:

### 1. `Workplane("XZ")` with `.center(10, 0)` — Extrudes Downward (`-Y`), Shifted Along `+X` (Right Edge)
```python
result_xz = (
    cq.Workplane("XZ")
    .tag("base_plane")
    .rect(40, 40)
    .extrude(2)                        # Extrudes plate in -Y (Y: 0 -> -2)
    .workplaneFromTagged("base_plane") # Reuses the "XZ" datum plane at Y = 0
    .center(10, 0)                     # Local (10, 0) -> global X = +10, Z = 0 (right edge)
    .circle(6)
    .extrude(20)                       # Extrudes cylinder in -Y (Y: 0 -> -20)
)
```
![Pure BRep chain on Workplane("XZ") with .center(10, 0): extrudes downward in -Y, cylinder near +X right edge](assets/workplane_xz_extrude.png)

### 2. `Workplane("ZX")` with `.center(10, 0)` — Extrudes Upward (`+Y`), Shifted Along `+Z` (Front Edge)
```python
result_zx = (
    cq.Workplane("ZX")
    .tag("base_plane")
    .rect(40, 40)
    .extrude(2)                        # Extrudes plate in +Y (Y: 0 -> +2)
    .workplaneFromTagged("base_plane") # Reuses the "ZX" datum plane at Y = 0
    .center(10, 0)                     # Local (10, 0) -> global Z = +10, X = 0 (front edge!)
    .circle(6)
    .extrude(20)                       # Extrudes cylinder in +Y (Y: 0 -> +20)
)
```
![Pure BRep chain on Workplane("ZX") with .center(10, 0): extrudes upward in +Y, cylinder shifted to +Z front edge](assets/workplane_zx_extrude.png)

