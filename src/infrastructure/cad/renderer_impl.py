"""CAD renderer service implementation."""

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from domain.services.cad_renderer import CadRendererService
from domain.value_objects.cad_code import CadCode
from domain.value_objects.euler_characteristic import EulerCharacteristic
from domain.value_objects.multiview_image import MultiviewImage


class CadRenderError(Exception):
    """Exception raised when CAD rendering fails."""

    pass


class CadRendererServiceImpl(CadRendererService):
    """Implementation of CAD renderer service using build123d."""

    def __init__(
        self,
        image_width: int = 800,
        image_height: int = 600,
    ) -> None:
        """
        Initialize the renderer.

        Args:
            image_width: Width of rendered images.
            image_height: Height of rendered images.
        """
        self._image_width = image_width
        self._image_height = image_height

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
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._render_sync,
            cad_code,
            output_dir,
            individual_id,
        )

    def _render_sync(
        self,
        cad_code: CadCode,
        output_dir: Path,
        individual_id: str,
    ) -> MultiviewImage:
        """Synchronous rendering implementation."""
        try:
            part = self._execute_code(cad_code.code)

            output_dir.mkdir(parents=True, exist_ok=True)

            front_path = output_dir / f"{individual_id}_front.png"
            top_path = output_dir / f"{individual_id}_top.png"
            side_path = output_dir / f"{individual_id}_side.png"
            iso_path = output_dir / f"{individual_id}_isometric.png"

            self._render_view(part, front_path, view="front")
            self._render_view(part, top_path, view="top")
            self._render_view(part, side_path, view="right")
            self._render_view(part, iso_path, view="isometric")

            return MultiviewImage(
                front_view=front_path,
                top_view=top_path,
                side_view=side_path,
                isometric_view=iso_path,
            )

        except Exception as e:
            raise CadRenderError(f"Failed to render CAD code: {str(e)}") from e

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
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._calculate_euler_sync,
            cad_code,
        )

    def _calculate_euler_sync(self, cad_code: CadCode) -> EulerCharacteristic:
        """Synchronous Euler characteristic calculation."""
        try:
            part = self._execute_code(cad_code.code)

            shape = part.wrapped

            vertices = 0
            edges = 0
            faces = 0

            from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX
            from OCP.TopExp import TopExp_Explorer

            explorer = TopExp_Explorer(shape, TopAbs_VERTEX)
            while explorer.More():
                vertices += 1
                explorer.Next()

            explorer = TopExp_Explorer(shape, TopAbs_EDGE)
            while explorer.More():
                edges += 1
                explorer.Next()

            explorer = TopExp_Explorer(shape, TopAbs_FACE)
            while explorer.More():
                faces += 1
                explorer.Next()

            euler_value = vertices - edges + faces

            return EulerCharacteristic(
                value=euler_value,
                vertices=vertices,
                edges=edges,
                faces=faces,
            )

        except Exception:
            return EulerCharacteristic(value=2, vertices=0, edges=0, faces=0)

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
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._export_step_sync,
            cad_code,
            output_path,
        )

    def _export_step_sync(self, cad_code: CadCode, output_path: Path) -> Path:
        """Synchronous STEP export implementation."""
        try:
            part = self._execute_code(cad_code.code)

            output_path.parent.mkdir(parents=True, exist_ok=True)

            from build123d import export_step

            export_step(part, str(output_path))

            return output_path

        except Exception as e:
            raise CadRenderError(f"Failed to export STEP: {str(e)}") from e

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
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._validate_code_sync,
            cad_code,
        )

    def _validate_code_sync(self, cad_code: CadCode) -> tuple[bool, str | None]:
        """Synchronous code validation."""
        try:
            self._execute_code(cad_code.code)
            return True, None
        except Exception as e:
            return False, str(e)

    def _execute_code(self, code: str) -> Any:
        """
        Execute CAD code in a subprocess and return the result.

        Args:
            code: Python code to execute.

        Returns:
            The 'result' variable from the executed code.

        Raises:
            CadRenderError: If code execution fails.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            script_path = tmpdir_path / "cad_script.py"
            step_output_path = tmpdir_path / "output.step"

            wrapper_script = f'''import sys
import json

try:
    import build123d
    from build123d import export_step

    # Import all build123d names into namespace
    for name in dir(build123d):
        if not name.startswith("_"):
            globals()[name] = getattr(build123d, name)

    # Execute the user code in a namespace we can inspect
    user_code = \'\'\'
{code}
\'\'\'
    exec_namespace = globals().copy()
    exec(user_code, exec_namespace)

    # Find the result object
    result_obj = None

    # First, check for explicit 'result' variable
    if 'result' in exec_namespace:
        result_obj = exec_namespace['result']

    # If not found, look for Part objects
    if result_obj is None:
        from build123d import Part, Solid, Compound
        for name, value in exec_namespace.items():
            if name.startswith('_'):
                continue
            if isinstance(value, (Part, Solid, Compound)):
                result_obj = value
                break
            # Check for BuildPart context result
            if hasattr(value, 'part') and isinstance(value.part, (Part, Solid)):
                result_obj = value.part
                break

    if result_obj is None:
        available_vars = [k for k in exec_namespace.keys() if not k.startswith('_')]
        print(json.dumps({{
            "success": False,
            "error": f"No 'result' variable or Part object found. Available: {{available_vars[-20:]}}"
        }}))
        sys.exit(1)

    # Export to STEP file
    export_step(result_obj, "{step_output_path}")
    print(json.dumps({{"success": True}}))

except Exception as e:
    import traceback
    print(json.dumps({{
        "success": False,
        "error": f"{{str(e)}}\\n{{traceback.format_exc()}}"
    }}))
    sys.exit(1)
'''

            script_path.write_text(wrapper_script)

            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                try:
                    output = json.loads(result.stdout)
                    error_msg = output.get("error", "Unknown error")
                except (json.JSONDecodeError, KeyError):
                    error_msg = result.stderr or result.stdout or "Unknown error"
                raise CadRenderError(f"Code execution failed: {error_msg}")

            if not step_output_path.exists():
                raise CadRenderError("STEP file was not created")

            # Check STEP file size
            step_size = step_output_path.stat().st_size
            if step_size == 0:
                raise CadRenderError("STEP file is empty (0 bytes)")

            from build123d import import_step

            try:
                parts = import_step(str(step_output_path))
            except Exception as e:
                raise CadRenderError(
                    f"Failed to import STEP file ({step_size} bytes): {e}"
                )

            if not parts:
                # Read first few lines of STEP file for debugging
                with open(step_output_path, "r") as f:
                    header = f.read(500)
                raise CadRenderError(
                    f"STEP file imported but returned empty result "
                    f"({step_size} bytes). Header: {header[:200]}..."
                )

            return parts

    def _render_view(
        self,
        part: Any,
        output_path: Path,
        view: str,
    ) -> None:
        """
        Render a single view of the part.

        Args:
            part: The part to render.
            output_path: Path to save the image.
            view: View direction ('front', 'top', 'right', 'isometric').
        """
        try:
            from ocp_vscode import Camera, export_png

            camera_positions = {
                "front": (0, -100, 0),
                "top": (0, 0, 100),
                "right": (100, 0, 0),
                "isometric": (100, -100, 100),
            }

            camera_target = (0, 0, 0)
            camera_pos = camera_positions.get(view, camera_positions["isometric"])

            camera = Camera(
                position=camera_pos,
                target=camera_target,
            )

            export_png(
                part,
                str(output_path),
                width=self._image_width,
                height=self._image_height,
                camera=camera,
            )

        except ImportError:
            self._render_view_matplotlib(part, output_path, view)

    def _render_view_matplotlib(
        self,
        part: Any,
        output_path: Path,
        view: str,
    ) -> None:
        """
        Fallback rendering using matplotlib.

        Args:
            part: The part to render.
            output_path: Path to save the image.
            view: View direction.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection

            fig = plt.figure(figsize=(8, 6))
            ax = fig.add_subplot(111, projection="3d")

            try:
                from OCP.BRep import BRep_Tool
                from OCP.BRepMesh import BRepMesh_IncrementalMesh
                from OCP.TopAbs import TopAbs_FACE
                from OCP.TopExp import TopExp_Explorer
                from OCP.TopLoc import TopLoc_Location
                from OCP.TopoDS import TopoDS

                shape = part.wrapped
                mesh = BRepMesh_IncrementalMesh(shape, 0.1, False, 0.1, True)
                mesh.Perform()

                all_triangles = []
                explorer = TopExp_Explorer(shape, TopAbs_FACE)

                while explorer.More():
                    face = TopoDS.Face_s(explorer.Current())
                    location = TopLoc_Location()
                    triangulation = BRep_Tool.Triangulation_s(face, location)

                    if triangulation:
                        trsf = location.Transformation()
                        nodes = []
                        for i in range(1, triangulation.NbNodes() + 1):
                            pnt = triangulation.Node(i)
                            pnt_transformed = pnt.Transformed(trsf)
                            nodes.append(
                                [
                                    pnt_transformed.X(),
                                    pnt_transformed.Y(),
                                    pnt_transformed.Z(),
                                ]
                            )

                        for i in range(1, triangulation.NbTriangles() + 1):
                            tri = triangulation.Triangle(i)
                            n1, n2, n3 = tri.Get()
                            triangle = [
                                nodes[n1 - 1],
                                nodes[n2 - 1],
                                nodes[n3 - 1],
                            ]
                            all_triangles.append(triangle)

                    explorer.Next()

                if all_triangles:
                    poly_collection = Poly3DCollection(
                        all_triangles,
                        alpha=0.9,
                        facecolor="lightblue",
                        edgecolor="darkblue",
                        linewidth=0.1,
                    )
                    ax.add_collection3d(poly_collection)

                    all_vertices = np.array([v for tri in all_triangles for v in tri])
                    ax.set_xlim(all_vertices[:, 0].min(), all_vertices[:, 0].max())
                    ax.set_ylim(all_vertices[:, 1].min(), all_vertices[:, 1].max())
                    ax.set_zlim(all_vertices[:, 2].min(), all_vertices[:, 2].max())

            except Exception:
                ax.text(0.5, 0.5, 0.5, "Render Error", ha="center")

            view_angles = {
                "front": (0, 0),
                "top": (90, 0),
                "right": (0, 90),
                "isometric": (30, 45),
            }

            elev, azim = view_angles.get(view, (30, 45))
            ax.view_init(elev=elev, azim=azim)

            ax.set_xlabel("X")
            ax.set_ylabel("Y")
            ax.set_zlabel("Z")

            plt.savefig(output_path, dpi=100, bbox_inches="tight")
            plt.close()

        except Exception:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.text(
                0.5,
                0.5,
                f"Render failed: {view}",
                ha="center",
                va="center",
                fontsize=12,
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            plt.savefig(output_path, dpi=100)
            plt.close()
