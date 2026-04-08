"""Tests for domain value objects."""

from pathlib import Path

import pytest

from domain.value_objects.cad_code import CadCode
from domain.value_objects.euler_characteristic import EulerCharacteristic
from domain.value_objects.multiview_image import MultiviewImage


class TestCadCode:
    """Tests for CadCode value object."""

    def test_create_valid_cad_code(self) -> None:
        code = "from build123d import *\nBox(10, 10, 10)"
        cad_code = CadCode(code=code)
        assert cad_code.code == code

    def test_create_empty_code_raises_error(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            CadCode(code="")

    def test_create_whitespace_code_raises_error(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            CadCode(code="   ")

    def test_to_dict(self) -> None:
        code = "Box(10, 10, 10)"
        cad_code = CadCode(code=code)
        assert cad_code.to_dict() == {"code": code}

    def test_from_dict(self) -> None:
        data = {"code": "Box(10, 10, 10)"}
        cad_code = CadCode.from_dict(data)
        assert cad_code.code == data["code"]

    def test_immutability(self) -> None:
        cad_code = CadCode(code="Box(10, 10, 10)")
        with pytest.raises(AttributeError):
            cad_code.code = "Cylinder(5, 20)"  # type: ignore


class TestMultiviewImage:
    """Tests for MultiviewImage value object."""

    def test_create_valid_multiview_image(self) -> None:
        image = MultiviewImage(
            front_view=Path("/tmp/front.png"),
            top_view=Path("/tmp/top.png"),
            side_view=Path("/tmp/side.png"),
            isometric_view=Path("/tmp/iso.png"),
        )
        assert image.front_view == Path("/tmp/front.png")

    def test_get_all_paths(self) -> None:
        image = MultiviewImage(
            front_view=Path("/tmp/front.png"),
            top_view=Path("/tmp/top.png"),
            side_view=Path("/tmp/side.png"),
            isometric_view=Path("/tmp/iso.png"),
        )
        paths = image.get_all_paths()
        assert len(paths) == 4

    def test_to_dict(self) -> None:
        image = MultiviewImage(
            front_view=Path("/tmp/front.png"),
            top_view=Path("/tmp/top.png"),
            side_view=Path("/tmp/side.png"),
            isometric_view=Path("/tmp/iso.png"),
        )
        data = image.to_dict()
        assert data["front_view"] == "/tmp/front.png"


class TestEulerCharacteristic:
    """Tests for EulerCharacteristic value object."""

    def test_create_valid_euler(self) -> None:
        euler = EulerCharacteristic(value=2, vertices=8, edges=12, faces=6)
        assert euler.value == 2

    def test_genus_calculation(self) -> None:
        sphere = EulerCharacteristic(value=2)
        assert sphere.genus() == 0

        torus = EulerCharacteristic(value=0)
        assert torus.genus() == 1

    def test_to_dict(self) -> None:
        euler = EulerCharacteristic(value=2, vertices=8, edges=12, faces=6)
        data = euler.to_dict()
        assert data["value"] == 2
        assert data["vertices"] == 8
