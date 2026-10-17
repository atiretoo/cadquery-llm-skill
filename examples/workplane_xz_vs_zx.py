# Example: Demonstrates how Workplane("XZ") extrudes in -Y while Workplane("ZX") extrudes in +Y.

import cadquery as cq

# Parameters
plate_size = 40.0
plate_thickness = 2.0
cyl_radius = 5.0
cyl_length = 20.0
x_offset = 10.0

# Thin square plate on the XZ plane at Y = 0.
# Because "XZ" has xDir = +X and yDir = +Z, the right-hand rule (X x Z = -Y)
# sets the plane normal to (0, -1, 0), so .extrude(2) extrudes from Y = 0 to Y = -2.
plate = cq.Workplane("XZ").rect(plate_size, plate_size).extrude(plate_thickness)

# Cylinder extruded with a positive distance (+20) on Workplane("XZ") at global X = -10.
# Because the "XZ" normal points in -Y, this cylinder extends backward (Y: 0 -> -20).
cyl_xz = (
    cq.Workplane("XZ")
    .center(-x_offset, 0)  # on "XZ", local (x, y) maps to global (X, Z)
    .circle(cyl_radius)
    .extrude(cyl_length)
)

# Cylinder extruded with a positive distance (+20) on the forward cyclic Workplane("ZX")
# at global X = +10.
# Because "ZX" has xDir = +Z and yDir = +X, the right-hand rule (Z x X = +Y)
# sets the plane normal to (0, +1, 0), so this cylinder extends forward (Y: 0 -> +20).
# Note that 2D coordinates on "ZX" are ordered (z, x).
cyl_zx = (
    cq.Workplane("ZX")
    .center(0, x_offset)   # on "ZX", local (x, y) maps to global (Z, X)
    .circle(cyl_radius)
    .extrude(cyl_length)
)

result = plate.union(cyl_xz).union(cyl_zx)

# The following call can be used if running in CQ-editor
# show_object(result)
