"""Euler characteristic value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EulerCharacteristic:
    """
    Value object representing the Euler characteristic of a 3D object.

    The Euler characteristic χ = V - E + F, where:
    - V = number of vertices
    - E = number of edges
    - F = number of faces

    For solid objects, χ = 2 - 2g where g is the genus (number of holes).
    A sphere has χ = 2, a torus has χ = 0.

    Attributes:
        value: The Euler characteristic value.
        vertices: Number of vertices.
        edges: Number of edges.
        faces: Number of faces.
    """

    value: int
    vertices: int = 0
    edges: int = 0
    faces: int = 0

    def genus(self) -> int:
        """
        Calculate the genus (number of holes) from Euler characteristic.

        Returns:
            The genus of the object.
        """
        return (2 - self.value) // 2

    def to_dict(self) -> dict:
        """
        Serialize to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "value": self.value,
            "vertices": self.vertices,
            "edges": self.edges,
            "faces": self.faces,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EulerCharacteristic":
        """
        Create EulerCharacteristic from dictionary.

        Args:
            data: Dictionary containing Euler characteristic data.

        Returns:
            EulerCharacteristic instance.
        """
        return cls(
            value=data["value"],
            vertices=data.get("vertices", 0),
            edges=data.get("edges", 0),
            faces=data.get("faces", 0),
        )
