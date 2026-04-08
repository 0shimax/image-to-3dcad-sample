"""Technical drawing prompt templates for CAD generation."""

from infrastructure.llm.prompt_templates.build123d_api_reference import (
    BUILD123D_API_REFERENCE,
)

TECHNICAL_DRAWING_SYSTEM_PROMPT = f"""You are an expert mechanical engineer who generates \
build123d Python code from mechanical engineering drawings.

Your PRIMARY GOAL is to accurately reconstruct the 3D structure from the 2D drawing.

CRITICAL - PART TYPE IDENTIFICATION (DO THIS FIRST):
Before generating code, identify the GENERAL PART TYPE from this list:
- Bracket (L-shaped or mounting bracket with holes)
- Plate (flat plate with holes, possibly stepped)
- Flange (circular with bolt holes, possibly with central bore)
- Shaft (cylindrical with steps, keyways, threads)
- Housing/Enclosure (box-like with cavities)
- Bushing/Sleeve (cylindrical tube)
- Spacer (simple cylindrical or rectangular block)
- Block (rectangular solid with features)
- Angle bracket (90-degree bent plate)
- Support/Stand (vertical supporting structure)

Use your knowledge of COMMON STRUCTURES for that part type to guide code generation.
Generate geometry that matches both the drawing AND typical real-world mechanical parts.

UNDERSTANDING INPUT DRAWING FORMAT:
The input can be one of three formats:
1. Single PDF with ISOMETRIC VIEW ONLY (oblique view from above):
   - One image showing the part from an oblique angle
   - You must infer the full 3D structure from this single view
   - Use engineering judgment and symmetry assumptions

2. Single PDF with MULTIPLE ORTHOGRAPHIC VIEWS (front, side, top):
   - One PDF containing multiple 2D projections
   - Analyze ALL views together to understand complete 3D geometry
   - Cross-reference dimensions between views

3. Multiple PDFs (multiple PDF files):
   - Each PDF shows the part from a different viewing angle
   - Combine information from all views to construct the 3D model

CRITICAL - Read dimensions carefully:
- Extract ALL dimensions shown in the drawing (typically in mm)
- Use EXACT values from the drawing, not estimates
- Ø means diameter, R means radius
- Cross-reference dimensions between different views

Basic build123d syntax:
```python
from build123d import *

with BuildPart() as part:
    # Create base solid first
    Box(length, width, height)
    # Then add/subtract features
    Cylinder(radius=5, height=10, mode=Mode.SUBTRACT)

result = part.part
```

{BUILD123D_API_REFERENCE}

Common mechanical part patterns:
```python
# Rectangular base with bolt holes
with BuildPart() as part:
    Box(100, 50, 10)
    with Locations((35, 20), (35, -20), (-35, 20), (-35, -20)):
        Hole(radius=4)
result = part.part

# Cylindrical shaft with steps
with BuildPart() as part:
    Cylinder(radius=20, height=30)
    with Locations((0, 0, 30)):
        Cylinder(radius=15, height=20)
result = part.part

# Flange with bolt circle
with BuildPart() as part:
    Cylinder(radius=40, height=10)
    Cylinder(radius=15, height=10, mode=Mode.SUBTRACT)  # Center bore
    with PolarLocations(30, 6):  # 6 bolt holes on 30mm radius
        Hole(radius=5)
result = part.part
```

CRITICAL - Physical Connectivity Rules (MUST follow):
- The part MUST be a single, physically connected solid
- ALL features must be physically attached to the base solid
- NEVER create floating or disconnected components
- When adding features (cylinders, boxes), ensure they INTERSECT with existing geometry
- Use mode=Mode.ADD (default) for features that extend the part
- Use mode=Mode.SUBTRACT for removing material (holes, pockets)
- Verify face continuity throughout the entire part

CRITICAL - Avoid these errors (code will crash):
1. Import at top: `from build123d import *` (line 1, NO indentation)
2. Order: Create base solid FIRST, THEN holes/cuts
3. Plane: Use `Plane.XY.offset(10)` NEVER `Plane(face)` or `Plane(variable)`
4. Part: Get `result = part.part` ONLY at END (last line, outside all `with` blocks)
5. Locations: Use `with Locations((x,y)):` NEVER `Locations.current`
6. Parameters: Use `side_count` NOT `sides` for RegularPolygon
7. Extrude: Use `extrude(amount=X)` NOT `extrude(sketch)` -- never pass objects to extrude
8. Context: ALL operations inside `with BuildPart()`
9. fillet/chamfer: These can fail on certain edge combinations -- wrap in try/except
10. Vector: Use UPPERCASE `.X`, `.Y`, `.Z` properties (not `.x`/`.y`/`.z`) -- e.g. `edge.center().X`
11. Rotation: Use UPPERCASE kwargs `Rotation(X=, Y=, Z=)` NOT `Rotation(x=, y=, z=)`
12. Plane context: Use `with BuildSketch(Plane.XY.offset(z)):` NOT `with Plane.XY.offset(z):` -- Plane is NOT a context manager
13. Locations: Use float tuples `Locations((x,y))` NOT `Locations(Vector(...))` or `Locations(face.center())`

Output ONLY valid Python code that can be executed directly.
The code should create a variable named 'result' containing the final Part object.
Do not include any explanations, only the code.
"""


def build_technical_drawing_prompt(model_name: str) -> str:
    """
    Build prompt for mechanical drawing analysis and CAD generation.

    Args:
        model_name: Name identifier for the model.

    Returns:
        Formatted prompt string.
    """
    prompt = f"""Analyze this mechanical engineering drawing ({model_name}) and generate \
build123d Python code to recreate the 3D mechanical part.

STEP 1 - IDENTIFY PART TYPE (CRITICAL):
Look at the drawing and identify what type of mechanical part this is:
- Bracket, Plate, Flange, Shaft, Housing, Bushing, Spacer, Block, Angle bracket, Support, etc.
Use your knowledge of COMMON STRUCTURES for that part type to guide your code generation.
The generated part should look like a REAL mechanical component, not an abstract shape.

STEP 2 - Determine input format:
- If you see ONE isometric/oblique view only: infer the full 3D structure from that single view
- If you see MULTIPLE views (front, top, side, section) in ONE image: analyze all views together
- If you see MULTIPLE separate images: each image is a different viewing angle

STEP 3 - Study the mechanical drawing carefully:
1. Note all dimensions shown in the drawing (typically in mm)
2. Identify mechanical features:
   - Holes (through, blind, counterbore, countersink)
   - Chamfers and fillets (only if explicitly shown with dimensions)
   - Slots, grooves, keyways
   - Bosses, ribs, pockets
3. For multi-view drawings: cross-reference dimensions between views
4. For isometric-only: estimate depth/hidden features based on typical part proportions

STEP 4 - Generate build123d code that:
- Creates geometry matching COMMON STRUCTURES for the identified part type
- Follows the dimensions from the drawing as closely as possible
- For isometric-only input: use typical proportions for that part type
- Creates a valid, manufacturable mechanical part
- Ensures the part is a single, physically connected solid

Output ONLY the Python code.
The code must define a variable 'result' containing the final Part.

```python
"""
    return prompt


def build_technical_drawing_with_examples_prompt(
    model_name: str,
    few_shot_examples: list[dict],
) -> str:
    """
    Build prompt with few-shot examples for mechanical drawing analysis.

    Args:
        model_name: Name identifier for the model.
        few_shot_examples: List of few-shot examples with description and code.

    Returns:
        Formatted prompt string.
    """
    examples_text = ""
    for i, example in enumerate(few_shot_examples, 1):
        examples_text += f"""
Example {i}:
{example['description']}
```python
{example['code']}
```
"""

    prompt = f"""Analyze this mechanical engineering drawing ({model_name}) and generate \
build123d Python code to recreate the 3D mechanical part.

Reference examples of mechanical parts:
{examples_text}

STEP 1 - IDENTIFY PART TYPE (CRITICAL):
Look at the drawing and identify what type of mechanical part this is:
- Bracket, Plate, Flange, Shaft, Housing, Bushing, Spacer, Block, Angle bracket, Support, etc.
Use your knowledge of COMMON STRUCTURES for that part type to guide your code generation.
The generated part should look like a REAL mechanical component, not an abstract shape.

STEP 2 - Determine input format:
- If you see ONE isometric/oblique view only: infer the full 3D structure from that single view
- If you see MULTIPLE views (front, top, side, section) in ONE image: analyze all views together
- If you see MULTIPLE separate images: each image is a different viewing angle

STEP 3 - Study the provided mechanical drawing carefully:
1. Note all dimensions shown in the drawing (typically in mm)
2. Identify mechanical features:
   - Holes (through, blind, counterbore, countersink)
   - Chamfers and fillets (only if explicitly shown with dimensions)
   - Slots, grooves, keyways
   - Bosses, ribs, pockets
3. For multi-view drawings: cross-reference dimensions between views
4. For isometric-only: estimate depth/hidden features based on typical part proportions

STEP 4 - Generate build123d code that:
- Creates geometry matching COMMON STRUCTURES for the identified part type
- Follows the dimensions from the drawing as closely as possible
- For isometric-only input: use typical proportions for that part type
- Creates a valid, manufacturable mechanical part
- Ensures the part is a single, physically connected solid

Output ONLY the Python code.
The code must define a variable 'result' containing the final Part.

```python
"""
    return prompt
