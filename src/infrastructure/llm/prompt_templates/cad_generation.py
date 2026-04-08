"""CAD generation prompt templates."""

from infrastructure.llm.prompt_templates.build123d_api_reference import (
    BUILD123D_API_REFERENCE,
)

BUILD123D_SYSTEM_PROMPT = f"""You are an expert mechanical engineer who generates build123d Python code \
for mechanical parts.

build123d is a Python CAD library that creates 3D models programmatically.
You specialize in creating mechanical components such as brackets, housings, shafts, \
flanges, plates, gears, and other machined or manufactured parts.

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

CRITICAL - Physical Connectivity Rules:
- The part MUST be a single, physically connected solid
- ALL features must be physically attached to the base solid
- NEVER create floating or disconnected components
- When adding features, ensure they INTERSECT with existing geometry

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

Output ONLY valid Python code.
The code should create a variable named 'result' containing the final Part object.
"""


def build_initial_generation_prompt(
    user_prompt: str,
    few_shot_examples: list[dict],
) -> str:
    """
    Build prompt for initial mechanical part CAD code generation.

    Args:
        user_prompt: User's description of desired mechanical part.
        few_shot_examples: List of few-shot examples.

    Returns:
        Formatted prompt string.
    """
    examples_text = ""
    for i, example in enumerate(few_shot_examples, 1):
        examples_text += f"""
Example {i}:
{example["description"]}
```python
{example["code"]}
```
"""

    prompt = f"""Generate build123d Python code for: {user_prompt}

Examples:
{examples_text}

Output ONLY Python code:

```python
"""
    return prompt


def build_crossover_prompt(
    parent1_code: str,
    parent2_code: str,
    parent1_description: str,
    parent2_description: str,
    target_prompt: str,
) -> str:
    """
    Build prompt for crossover operation on mechanical parts.

    Args:
        parent1_code: First parent's CAD code.
        parent2_code: Second parent's CAD code.
        parent1_description: Description of first parent.
        parent2_description: Description of second parent.
        target_prompt: Original target description.

    Returns:
        Formatted prompt string.
    """
    prompt = f"""You are combining two mechanical part designs to create an improved offspring.

Target Mechanical Part: {target_prompt}

Parent 1 Description: {parent1_description}
Parent 1 Code:
```python
{parent1_code}
```

Parent 2 Description: {parent2_description}
Parent 2 Code:
```python
{parent2_code}
```

Analyze both parent mechanical parts:
1. Identify their geometric similarities
2. Identify strengths of each parent (accurate features, proper dimensions)
3. Identify weaknesses of each parent (missing features, incorrect geometry)
4. Combine the best features to create an improved mechanical part design

Generate new build123d code that:
- Combines complementary features from both parents
- Better matches the target mechanical part description
- Maintains valid, manufacturable geometry
- Preserves important mechanical features (holes, chamfers, fillets, etc.)

CRITICAL: Ensure the result is a single, physically connected solid with NO floating parts.
All features must be properly attached and respect physical connectivity.

Output ONLY the Python code, no explanations.
The code must define a variable 'result' containing the final Part.

```python
"""
    return prompt


def build_mutation_prompt(
    cad_code: str,
    target_prompt: str,
) -> str:
    """
    Build prompt for mutation operation on mechanical parts.

    Args:
        cad_code: CAD code to mutate.
        target_prompt: Original target description.

    Returns:
        Formatted prompt string.
    """
    prompt = f"""Refine and improve the following mechanical part CAD code to better match the target.

Target Mechanical Part: {target_prompt}

Current Code:
```python
{cad_code}
```

Refine the mechanical part by:
1. Adjusting dimensions or proportions to match specifications
2. Adding missing mechanical features (holes, chamfers, fillets, slots)
3. Improving geometric accuracy
4. Ensuring manufacturability
5. Fixing any geometric issues

CRITICAL: Ensure the result is a single, physically connected solid.
Verify that all features are properly attached with NO floating or disconnected components.
All parts must respect physical laws and face continuity.

Output ONLY the improved Python code, no explanations.
The code must define a variable 'result' containing the final Part.

```python
"""
    return prompt
