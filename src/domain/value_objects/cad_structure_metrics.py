"""CAD structure metrics value objects for Drawing2CAD-style evaluation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SketchPrimitiveAccuracy:
    """
    Accuracy metrics for sketch primitives.

    Attributes:
        line: Accuracy for line primitives (0-1).
        arc: Accuracy for arc primitives (0-1).
        circle: Accuracy for circle primitives (0-1).
    """

    line: float
    arc: float
    circle: float

    def __post_init__(self) -> None:
        """Validate accuracy values are in [0, 1] range."""
        for name, value in [
            ("line", self.line),
            ("arc", self.arc),
            ("circle", self.circle),
        ]:
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} accuracy must be between 0 and 1")

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "line": self.line,
            "arc": self.arc,
            "circle": self.circle,
        }


@dataclass(frozen=True)
class ExtrusionAccuracy:
    """
    Accuracy metrics for extrusion operations.

    Attributes:
        plane: Accuracy for extrusion plane matching (0-1).
        transform: Accuracy for extrusion transform/direction (0-1).
        extent: Accuracy for extrusion extent/depth (0-1).
        overall: Overall extrusion accuracy (0-1).
    """

    plane: float
    transform: float
    extent: float
    overall: float

    def __post_init__(self) -> None:
        """Validate accuracy values are in [0, 1] range."""
        for name, value in [
            ("plane", self.plane),
            ("transform", self.transform),
            ("extent", self.extent),
            ("overall", self.overall),
        ]:
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} accuracy must be between 0 and 1")

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "plane": self.plane,
            "transform": self.transform,
            "extent": self.extent,
            "overall": self.overall,
        }


@dataclass(frozen=True)
class CadStructureMetrics:
    """
    CAD structure metrics following Drawing2CAD evaluation methodology.

    Compares structural elements of CAD models at the command and
    primitive level rather than just geometric similarity.

    Attributes:
        command_accuracy: Overall accuracy of CAD commands (0-1).
        sketch_primitive: Accuracy metrics for sketch primitives.
        extrusion: Accuracy metrics for extrusion operations.
    """

    command_accuracy: float
    sketch_primitive: SketchPrimitiveAccuracy
    extrusion: ExtrusionAccuracy

    def __post_init__(self) -> None:
        """Validate command accuracy is in [0, 1] range."""
        if not 0.0 <= self.command_accuracy <= 1.0:
            raise ValueError("command_accuracy must be between 0 and 1")

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "command_accuracy": self.command_accuracy,
            "sketch_primitive": self.sketch_primitive.to_dict(),
            "extrusion": self.extrusion.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CadStructureMetrics":
        """Deserialize from dictionary."""
        return cls(
            command_accuracy=data["command_accuracy"],
            sketch_primitive=SketchPrimitiveAccuracy(**data["sketch_primitive"]),
            extrusion=ExtrusionAccuracy(**data["extrusion"]),
        )


@dataclass(frozen=True)
class CadStructureCounts:
    """
    Counts of CAD structural elements extracted from a model.

    Used for comparing structural similarity between models.

    Attributes:
        lines: Number of linear edges.
        arcs: Number of arc edges.
        circles: Number of circular edges.
        planar_faces: Number of planar faces.
        cylindrical_faces: Number of cylindrical faces.
        conical_faces: Number of conical faces.
        spherical_faces: Number of spherical faces.
        toroidal_faces: Number of toroidal faces.
        other_faces: Number of other surface types.
    """

    lines: int
    arcs: int
    circles: int
    planar_faces: int
    cylindrical_faces: int
    conical_faces: int
    spherical_faces: int
    toroidal_faces: int
    other_faces: int

    def total_edges(self) -> int:
        """Get total number of classified edges."""
        return self.lines + self.arcs + self.circles

    def total_faces(self) -> int:
        """Get total number of faces."""
        return (
            self.planar_faces
            + self.cylindrical_faces
            + self.conical_faces
            + self.spherical_faces
            + self.toroidal_faces
            + self.other_faces
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "lines": self.lines,
            "arcs": self.arcs,
            "circles": self.circles,
            "planar_faces": self.planar_faces,
            "cylindrical_faces": self.cylindrical_faces,
            "conical_faces": self.conical_faces,
            "spherical_faces": self.spherical_faces,
            "toroidal_faces": self.toroidal_faces,
            "other_faces": self.other_faces,
        }
