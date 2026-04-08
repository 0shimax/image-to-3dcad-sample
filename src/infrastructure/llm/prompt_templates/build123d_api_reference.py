"""build123d API reference for LLM code generation prompts.

Contains verified API signatures extracted from the actual build123d library.
Shared between cad_generation.py and technical_drawing.py system prompts.
"""

BUILD123D_API_REFERENCE = """
=== build123d API Reference (verified signatures) ===

CONTEXTS (required structure):
  with BuildPart() as part:     # 3D solid modeling context
  with BuildSketch() as sketch: # 2D sketch context (use inside BuildPart for extrude)
  with BuildLine() as line:     # 1D line/wire context (use inside BuildSketch)

3D SHAPES (use inside BuildPart):
  Box(length, width, height, mode=Mode.ADD)
  Cylinder(radius, height, arc_size=360, mode=Mode.ADD)
  Sphere(radius, mode=Mode.ADD)
  Cone(bottom_radius, top_radius, height, arc_size=360, mode=Mode.ADD)
  Torus(major_radius, minor_radius, mode=Mode.ADD)
  Wedge(xsize, ysize, zsize, xmin, zmin, xmax, zmax)
  # All 3D shapes accept: align=(Align.CENTER, Align.CENTER, Align.CENTER)

HOLES (use inside BuildPart, default mode=Mode.SUBTRACT):
  Hole(radius, depth=None)                # depth=None for through hole
  CounterBoreHole(radius, counter_bore_radius, counter_bore_depth, depth=None)
  CounterSinkHole(radius, counter_sink_radius, depth=None, counter_sink_angle=82)

2D SHAPES (use inside BuildSketch):
  Rectangle(width, height, rotation=0, mode=Mode.ADD)
  Circle(radius, mode=Mode.ADD)
  RegularPolygon(radius, side_count, mode=Mode.ADD)  # IMPORTANT: side_count NOT sides
  Ellipse(x_radius, y_radius)
  Polygon(*pts)                           # Polygon((0,0), (10,0), (5,10))
  Trapezoid(width, height, left_side_angle, right_side_angle=None)
  SlotOverall(width, height)
  SlotCenterToCenter(center_separation, height)

OPERATIONS:
  extrude(amount=X)
    # CORRECT usage - call AFTER BuildSketch closes, inside BuildPart:
    #   with BuildSketch():
    #       Rectangle(10, 20)
    #   extrude(amount=5)
    # WRONG: extrude(sketch)  -- NEVER pass a sketch object
    # WRONG: extrude(amount=5) inside BuildSketch  -- must be outside BuildSketch
    # Optional params: both=False, taper=0.0, mode=Mode.ADD
  revolve(axis=Axis.Z, revolution_arc=360.0, mode=Mode.ADD)
  loft(sections=None, ruled=False, mode=Mode.ADD)
  sweep(sections=None, path=None, mode=Mode.ADD)
  mirror(objects=None, about=Plane.XZ, mode=Mode.ADD)
  offset(objects=None, amount=0, kind=Kind.ARC)
  split(objects=None, bisect_by=Plane.XZ, keep=Keep.TOP)

EDGE OPERATIONS (may fail on certain edge combinations - wrap in try/except):
  fillet(objects, radius)          # objects = edges, e.g. part.edges()
  chamfer(objects, length)         # optional: length2, angle

POSITIONING (use as context managers, with TUPLE coordinates):
  with Locations((x1,y1), (x2,y2), ...):          # specific positions (float tuples!)
  with PolarLocations(radius, count):              # circular pattern
  with GridLocations(x_spacing, y_spacing, x_count, y_count):  # grid pattern
  with HexLocations(radius, x_count, y_count):    # hexagonal pattern
  # CORRECT: Locations((10, 5), (20, 5))          # tuples of floats
  # WRONG:   Locations(Vector(10, 5, 0))           # do NOT pass Vector objects
  # WRONG:   Locations(face.center())              # do NOT pass Vector objects

ROTATION (UPPERCASE keyword args only):
  Rotation(X=0, Y=0, Z=90)        # Rotate 90 degrees around Z axis
  Rotation(0, 0, 90)              # Same, using positional args
  # CORRECT: Rotation(X=45)       # UPPERCASE keyword
  # WRONG:   Rotation(x=45)       # lowercase causes TypeError: "Invalid key for Rotation"
  # Valid keys: X, Y, Z, rotation, ordering (ALL UPPERCASE)

PLANES (NOT context managers - pass to BuildSketch/BuildPart):
  Plane.XY, Plane.XZ, Plane.YZ
  Plane.front, Plane.back, Plane.left, Plane.right, Plane.top, Plane.bottom
  Plane.XY.offset(z)   # Create offset plane at height z
  # NEVER use Plane(face) or Plane(variable) - always use named planes + offset
  # CORRECT: with BuildSketch(Plane.XY.offset(10)):  # Plane as arg to BuildSketch
  # WRONG:   with Plane.XY.offset(10):               # Plane is NOT a context manager!

ENUMS:
  Mode: ADD, SUBTRACT, INTERSECT, REPLACE
  Align: MIN, CENTER, MAX
  Axis: X, Y, Z

SELECTORS (for fillet/chamfer edge selection):
  part.edges()                     # All edges of the part
  part.edges().filter_by(Axis.Z)   # Edges parallel to Z axis
  part.edges().sort_by(Axis.Z)     # Edges sorted by Z position
  part.faces().sort_by(Axis.Z)     # Faces sorted by Z position

VECTOR PROPERTIES (UPPERCASE - lowercase .x/.y/.z DO NOT EXIST):
  vec.X, vec.Y, vec.Z             # Access vector components (UPPERCASE only!)
  # edge.center().X               # CORRECT - get X coordinate of edge center
  # edge.center().x               # WRONG - AttributeError: 'Vector' has no attribute 'x'
  # Common methods returning Vector: .center(), .position, .Center()
  # ALWAYS use .X, .Y, .Z (uppercase) to access coordinates
"""
