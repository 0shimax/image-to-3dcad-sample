"""CAD renderer service interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from domain.value_objects.cad_code import CadCode
from domain.value_objects.euler_characteristic import EulerCharacteristic
from domain.value_objects.multiview_image import MultiviewImage


class CadRendererService(ABC):
    """
    Abstract service for rendering CAD code to images.

    This service executes build123d code and renders the resulting
    3D model to multiview images.
    """

    @abstractmethod
    async def render(
        self,
        cad_code: CadCode,
        output_dir: Path,
        individual_id: str,
    ) -> MultiviewImage:
        """
        Render CAD code to multiview images.

        Args:
            cad_code: CAD code to render.
            output_dir: Directory to save rendered images.
            individual_id: ID of the individual for naming files.

        Returns:
            MultiviewImage containing paths to rendered views.

        Raises:
            CadRenderError: If rendering fails.
        """
        pass

    @abstractmethod
    async def calculate_euler_characteristic(
        self,
        cad_code: CadCode,
    ) -> EulerCharacteristic:
        """
        Calculate the Euler characteristic of a CAD model.

        Args:
            cad_code: CAD code to analyze.

        Returns:
            EulerCharacteristic of the model.

        Raises:
            CadRenderError: If calculation fails.
        """
        pass

    @abstractmethod
    async def export_step(
        self,
        cad_code: CadCode,
        output_path: Path,
    ) -> Path:
        """
        Export CAD code to STEP file format.

        Args:
            cad_code: CAD code to export.
            output_path: Path for the STEP file.

        Returns:
            Path to the exported STEP file.

        Raises:
            CadRenderError: If export fails.
        """
        pass

    @abstractmethod
    async def validate_code(
        self,
        cad_code: CadCode,
    ) -> tuple[bool, str | None]:
        """
        Validate that CAD code can be executed without errors.

        Args:
            cad_code: CAD code to validate.

        Returns:
            Tuple of (is_valid, error_message).
            If valid, error_message is None.
        """
        pass
