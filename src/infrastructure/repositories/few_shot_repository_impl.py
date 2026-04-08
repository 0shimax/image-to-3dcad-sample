"""Few-shot repository implementation."""

import random
from pathlib import Path
import json

from domain.repositories.few_shot_repository import (
    FewShotRepository,
    FewShotExample,
)


DEFAULT_EXAMPLES = [
    FewShotExample(
        description="A simple cube with side length 10mm",
        code='''from build123d import *

with BuildPart() as part:
    Box(10, 10, 10)

result = part.part
''',
    ),
    FewShotExample(
        description="A cylinder with radius 5mm and height 20mm",
        code='''from build123d import *

with BuildPart() as part:
    Cylinder(radius=5, height=20)

result = part.part
''',
    ),
    FewShotExample(
        description="A box with a cylindrical hole through the center",
        code='''from build123d import *

with BuildPart() as part:
    Box(30, 30, 10)
    Cylinder(radius=5, height=10, mode=Mode.SUBTRACT)

result = part.part
''',
    ),
    FewShotExample(
        description="An L-shaped bracket",
        code='''from build123d import *

with BuildPart() as part:
    with BuildSketch() as sketch:
        with Locations((0, 0)):
            Rectangle(50, 10)
        with Locations((0, 25)):
            Rectangle(10, 40)
    extrude(amount=10)

result = part.part
''',
    ),
    FewShotExample(
        description="A cone with base radius 10mm and height 25mm",
        code='''from build123d import *

with BuildPart() as part:
    Cone(bottom_radius=10, top_radius=0, height=25)

result = part.part
''',
    ),
    FewShotExample(
        description="A sphere with radius 15mm",
        code='''from build123d import *

with BuildPart() as part:
    Sphere(radius=15)

result = part.part
''',
    ),
    FewShotExample(
        description="A rectangular plate with four corner holes",
        code='''from build123d import *

with BuildPart() as part:
    Box(100, 60, 5)
    with Locations(
        (40, 20, 0), (-40, 20, 0),
        (40, -20, 0), (-40, -20, 0)
    ):
        Cylinder(radius=3, height=5, mode=Mode.SUBTRACT)

result = part.part
''',
    ),
    FewShotExample(
        description="A torus (donut shape) with major radius 20mm and minor radius 5mm",
        code='''from build123d import *

with BuildPart() as part:
    Torus(major_radius=20, minor_radius=5)

result = part.part
''',
    ),
    FewShotExample(
        description="A hexagonal prism with circumradius 15mm and height 30mm",
        code='''from build123d import *

with BuildPart() as part:
    with BuildSketch() as sketch:
        RegularPolygon(radius=15, side_count=6)
    extrude(amount=30)

result = part.part
''',
    ),
    FewShotExample(
        description="A box with rounded edges (filleted)",
        code='''from build123d import *

with BuildPart() as part:
    Box(40, 30, 20)
    fillet(part.edges(), radius=3)

result = part.part
''',
    ),
]


class FewShotRepositoryImpl(FewShotRepository):
    """Implementation of few-shot repository."""

    def __init__(self, examples_path: Path | None = None) -> None:
        """
        Initialize the repository.

        Args:
            examples_path: Optional path to JSON file with additional examples.
        """
        self._examples: list[FewShotExample] = list(DEFAULT_EXAMPLES)

        if examples_path and examples_path.exists():
            self._load_examples_from_file(examples_path)

    def _load_examples_from_file(self, path: Path) -> None:
        """Load additional examples from a JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            example = FewShotExample(
                description=item["description"],
                code=item["code"],
            )
            self._examples.append(example)

    def get_random_examples(self, n: int) -> list[FewShotExample]:
        """
        Get n random few-shot examples.

        Args:
            n: Number of examples to return.

        Returns:
            List of FewShotExample objects.
        """
        if n >= len(self._examples):
            return list(self._examples)

        return random.sample(self._examples, n)

    def get_all_examples(self) -> list[FewShotExample]:
        """
        Get all available few-shot examples.

        Returns:
            List of all FewShotExample objects.
        """
        return list(self._examples)

    def add_example(self, example: FewShotExample) -> None:
        """
        Add a new few-shot example.

        Args:
            example: Example to add.
        """
        self._examples.append(example)
