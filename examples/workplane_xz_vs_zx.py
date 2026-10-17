# Example: Demonstrates both effects of switching from Workplane("XZ") to Workplane("ZX")
# using identical BRep chains with .center(10, 0):
#   1. On "XZ", .extrude() travels in -Y (downward), and .center(10, 0) shifts along +X.
#   2. On "ZX", .extrude() travels in +Y (upward), and .center(10, 0) shifts along +Z
#      because local 2D coordinates on "ZX" are (z, x).

import cadquery as cq

# Parameters
plate_size = 40.0
plate_thickness = 2.0
cyl_radius = 6.0
cyl_length = 20.0
offset = 10.0

# 1. Workplane("XZ"): xDir = +X, yDir = +Z, normal = -Y (X x Z = -Y)
#    - Plate and cylinder extrude backward in -Y (Y: 0 -> -20)
#    - .center(10, 0) places the cylinder at global X = +10, Z = 0 (near the +X right edge)
result_xz = (
    cq.Workplane("XZ")
    .tag("base_plane")
    .rect(plate_size, plate_size)
    .extrude(plate_thickness)          # Extrudes plate in -Y (Y: 0 -> -2)
    .workplaneFromTagged("base_plane") # Reuses the "XZ" datum plane at Y = 0
    .center(offset, 0)                 # Local (10, 0) -> global X = +10, Z = 0
    .circle(cyl_radius)
    .extrude(cyl_length)               # Extrudes cylinder in -Y (Y: 0 -> -20)
)

# 2. Workplane("ZX"): xDir = +Z, yDir = +X, normal = +Y (Z x X = +Y)
#    - Changing only "XZ" -> "ZX" flips the extrusion to +Y (Y: 0 -> +20)
#    - The same .center(10, 0) now places the cylinder at global Z = +10, X = 0
#      (near the +Z front edge), because local (x, y) on "ZX" maps to global (Z, X).
#      To place it at global X = +10, Z = 0 on "ZX", use .center(0, offset).
result = (
    cq.Workplane("ZX")
    .tag("base_plane")
    .rect(plate_size, plate_size)
    .extrude(plate_thickness)          # Extrudes plate in +Y (Y: 0 -> +2)
    .workplaneFromTagged("base_plane") # Reuses the "ZX" datum plane at Y = 0
    .center(offset, 0)                 # Local (10, 0) -> global Z = +10, X = 0!
    .circle(cyl_radius)
    .extrude(cyl_length)               # Extrudes cylinder in +Y (Y: 0 -> +20)
)

# The following call can be used if running in CQ-editor
# show_object(result)
