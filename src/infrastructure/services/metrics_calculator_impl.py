"""Metrics calculator service implementation."""

import asyncio
import math
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from domain.services.metrics_calculator import (
    EvaluationMetrics,
    MetricsCalculatorService,
)
from domain.value_objects.cad_structure_metrics import (
    CadStructureCounts,
    CadStructureMetrics,
    ExtrusionAccuracy,
    SketchPrimitiveAccuracy,
)


class MetricsCalculatorServiceImpl(MetricsCalculatorService):
    """Implementation of metrics calculator service."""

    def __init__(
        self,
        num_sample_points: int = 10000,
        voxel_resolution: int = 64,
    ) -> None:
        """
        Initialize the service.

        Args:
            num_sample_points: Number of points for point cloud sampling.
            voxel_resolution: Resolution for voxelization (IoU/DSC).
        """
        self._num_sample_points = num_sample_points
        self._voxel_resolution = voxel_resolution

    async def calculate(
        self,
        generated_step_path: Path,
        ground_truth_step_path: Path,
    ) -> EvaluationMetrics:
        """
        Calculate all evaluation metrics.

        Args:
            generated_step_path: Path to generated STEP file.
            ground_truth_step_path: Path to ground truth STEP file.

        Returns:
            EvaluationMetrics containing all calculated metrics.
        """
        loop = asyncio.get_running_loop()

        # Load each STEP file once (concurrent)
        (gen_points, gen_euler), (gt_points, gt_euler) = await asyncio.gather(
            loop.run_in_executor(None, self._load_and_sample, generated_step_path),
            loop.run_in_executor(None, self._load_and_sample, ground_truth_step_path),
        )

        # Normalize and align once
        gen_points, gt_points = self._normalize_and_align(gen_points, gt_points)

        # Build KD-trees once for PCD and HDD
        gen_tree = cKDTree(gen_points)
        gt_tree = cKDTree(gt_points)
        gen_to_gt_dists, _ = gt_tree.query(gen_points)
        gt_to_gen_dists, _ = gen_tree.query(gt_points)

        pcd = float(np.mean(gen_to_gt_dists) + np.mean(gt_to_gen_dists))
        hdd = float(max(np.max(gen_to_gt_dists), np.max(gt_to_gen_dists)))

        # Voxelize once for IoU and DSC
        gen_voxels = self._voxelize_from_points(gen_points)
        gt_voxels = self._voxelize_from_points(gt_points)

        intersection = np.sum(gen_voxels & gt_voxels)
        union = np.sum(gen_voxels | gt_voxels)
        gen_sum = np.sum(gen_voxels)
        gt_sum = np.sum(gt_voxels)

        iou = float(intersection / union) if union > 0 else 0.0
        dsc = (
            float(2 * intersection / (gen_sum + gt_sum))
            if (gen_sum + gt_sum) > 0
            else 0.0
        )

        topology_error, topology_correct = await self.calculate_topology_metrics(
            gen_euler, gt_euler
        )

        cad_structure = await self.calculate_cad_structure_metrics(
            generated_step_path, ground_truth_step_path
        )

        return EvaluationMetrics(
            pcd=pcd,
            hdd=hdd,
            iou=iou,
            dsc=dsc,
            topology_error=topology_error,
            topology_correct=topology_correct,
            generated_euler=gen_euler,
            ground_truth_euler=gt_euler,
            cad_structure=cad_structure,
        )

    async def calculate_point_cloud_distance(
        self,
        generated_step_path: Path,
        ground_truth_step_path: Path,
    ) -> float:
        """
        Calculate Point Cloud Distance (PCD).

        Chamfer distance between point clouds.

        Args:
            generated_step_path: Path to generated STEP file.
            ground_truth_step_path: Path to ground truth STEP file.

        Returns:
            Point Cloud Distance value.
        """
        loop = asyncio.get_running_loop()

        gen_points, _ = await loop.run_in_executor(
            None, self._load_and_sample, generated_step_path
        )
        gt_points, _ = await loop.run_in_executor(
            None, self._load_and_sample, ground_truth_step_path
        )

        gen_points, gt_points = self._normalize_and_align(gen_points, gt_points)

        gen_tree = cKDTree(gen_points)
        gt_tree = cKDTree(gt_points)

        gen_to_gt_dists, _ = gt_tree.query(gen_points)
        gt_to_gen_dists, _ = gen_tree.query(gt_points)

        chamfer = np.mean(gen_to_gt_dists) + np.mean(gt_to_gen_dists)

        return float(chamfer)

    async def calculate_hausdorff_distance(
        self,
        generated_step_path: Path,
        ground_truth_step_path: Path,
    ) -> float:
        """
        Calculate Hausdorff Distance (HDD).

        Args:
            generated_step_path: Path to generated STEP file.
            ground_truth_step_path: Path to ground truth STEP file.

        Returns:
            Hausdorff Distance value.
        """
        loop = asyncio.get_running_loop()

        gen_points, _ = await loop.run_in_executor(
            None, self._load_and_sample, generated_step_path
        )
        gt_points, _ = await loop.run_in_executor(
            None, self._load_and_sample, ground_truth_step_path
        )

        gen_points, gt_points = self._normalize_and_align(gen_points, gt_points)

        gen_tree = cKDTree(gen_points)
        gt_tree = cKDTree(gt_points)

        gen_to_gt_dists, _ = gt_tree.query(gen_points)
        gt_to_gen_dists, _ = gen_tree.query(gt_points)

        hausdorff = max(np.max(gen_to_gt_dists), np.max(gt_to_gen_dists))

        return float(hausdorff)

    async def calculate_iou(
        self,
        generated_step_path: Path,
        ground_truth_step_path: Path,
    ) -> float:
        """
        Calculate Intersection over Union (IoU).

        Args:
            generated_step_path: Path to generated STEP file.
            ground_truth_step_path: Path to ground truth STEP file.

        Returns:
            IoU value between 0 and 1.
        """
        loop = asyncio.get_running_loop()

        gen_voxels = await loop.run_in_executor(None, self._voxelize, generated_step_path)
        gt_voxels = await loop.run_in_executor(
            None, self._voxelize, ground_truth_step_path
        )

        intersection = np.sum(gen_voxels & gt_voxels)
        union = np.sum(gen_voxels | gt_voxels)

        if union == 0:
            return 0.0

        return float(intersection / union)

    async def calculate_dice_coefficient(
        self,
        generated_step_path: Path,
        ground_truth_step_path: Path,
    ) -> float:
        """
        Calculate Dice Similarity Coefficient (DSC).

        Args:
            generated_step_path: Path to generated STEP file.
            ground_truth_step_path: Path to ground truth STEP file.

        Returns:
            DSC value between 0 and 1.
        """
        loop = asyncio.get_running_loop()

        gen_voxels = await loop.run_in_executor(None, self._voxelize, generated_step_path)
        gt_voxels = await loop.run_in_executor(
            None, self._voxelize, ground_truth_step_path
        )

        intersection = np.sum(gen_voxels & gt_voxels)
        gen_sum = np.sum(gen_voxels)
        gt_sum = np.sum(gt_voxels)

        if gen_sum + gt_sum == 0:
            return 0.0

        return float(2 * intersection / (gen_sum + gt_sum))

    async def calculate_topology_metrics(
        self,
        generated_euler: int | None,
        ground_truth_euler: int | None,
    ) -> tuple[int | None, float | None]:
        """
        Calculate topology metrics.

        Args:
            generated_euler: Euler characteristic of generated model (or None).
            ground_truth_euler: Euler characteristic of ground truth (or None).

        Returns:
            Tuple of (topology_error, topology_correct).
            - topology_error: Absolute difference |gen - gt|, or None if not calculable
            - topology_correct: Binary indicator (1.0=correct, 0.0=incorrect), or None if not calculable
        """
        # If either Euler characteristic is None, cannot calculate topology metrics
        if generated_euler is None or ground_truth_euler is None:
            return None, None

        # Calculate topology metrics
        # Terr: absolute difference |gen - gt|
        # Tcorr: binary indicator (1.0 = correct, 0.0 = incorrect)
        topology_error = abs(generated_euler - ground_truth_euler)
        topology_correct = 1.0 if generated_euler == ground_truth_euler else 0.0

        return topology_error, topology_correct

    def _load_and_sample(self, step_path: Path) -> tuple[np.ndarray, int]:
        """
        Load STEP file and sample points from surface.

        Args:
            step_path: Path to STEP file.

        Returns:
            Tuple of (point_cloud, euler_characteristic).
        """
        try:
            from OCP.BRep import BRep_Tool
            from OCP.BRepMesh import BRepMesh_IncrementalMesh
            from OCP.IFSelect import IFSelect_RetDone
            from OCP.STEPControl import STEPControl_Reader
            from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX
            from OCP.TopExp import TopExp_Explorer
            from OCP.TopLoc import TopLoc_Location
            from OCP.TopoDS import TopoDS
            from OCP.TopTools import TopTools_IndexedMapOfShape

            reader = STEPControl_Reader()
            status = reader.ReadFile(str(step_path))

            if status != IFSelect_RetDone:
                raise ValueError(f"Failed to read STEP file: {step_path}")

            reader.TransferRoots()
            shape = reader.OneShape()

            mesh = BRepMesh_IncrementalMesh(shape, 0.1, False, 0.5, True)
            mesh.Perform()

            points = []
            explorer = TopExp_Explorer(shape, TopAbs_FACE)

            while explorer.More():
                face_shape = explorer.Current()
                face = TopoDS.Face_s(face_shape)
                location = TopLoc_Location()
                triangulation = BRep_Tool.Triangulation_s(face, location)

                if triangulation:
                    for i in range(1, triangulation.NbNodes() + 1):
                        pnt = triangulation.Node(i)
                        points.append([pnt.X(), pnt.Y(), pnt.Z()])

                explorer.Next()

            # Count unique vertices, edges, faces using IndexedMapOfShape
            # to avoid duplicate counting (same element shared by multiple faces)
            vertex_map = TopTools_IndexedMapOfShape()
            edge_map = TopTools_IndexedMapOfShape()
            face_map = TopTools_IndexedMapOfShape()

            explorer = TopExp_Explorer(shape, TopAbs_VERTEX)
            while explorer.More():
                vertex_map.Add(explorer.Current())
                explorer.Next()

            explorer = TopExp_Explorer(shape, TopAbs_EDGE)
            while explorer.More():
                edge_map.Add(explorer.Current())
                explorer.Next()

            explorer = TopExp_Explorer(shape, TopAbs_FACE)
            while explorer.More():
                face_map.Add(explorer.Current())
                explorer.Next()

            vertices = vertex_map.Extent()
            edges = edge_map.Extent()
            faces = face_map.Extent()
            euler = vertices - edges + faces

            if len(points) == 0:
                return np.zeros((1, 3)), euler

            points = np.array(points)

            if len(points) > self._num_sample_points:
                indices = np.random.choice(
                    len(points), self._num_sample_points, replace=False
                )
                points = points[indices]
            elif len(points) < self._num_sample_points:
                indices = np.random.choice(
                    len(points), self._num_sample_points, replace=True
                )
                points = points[indices]

            return points, euler

        except Exception as e:
            print(f"Error loading STEP file {step_path}: {e}")
            raise ValueError(f"Failed to load STEP file {step_path}: {e}")

    def _normalize_and_align(
        self,
        points1: np.ndarray,
        points2: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Normalize point clouds and align using ICP.

        Args:
            points1: First point cloud.
            points2: Second point cloud.

        Returns:
            Tuple of aligned point clouds.
        """
        centroid1 = np.mean(points1, axis=0)
        centroid2 = np.mean(points2, axis=0)

        points1_centered = points1 - centroid1
        points2_centered = points2 - centroid2

        scale1 = np.max(np.linalg.norm(points1_centered, axis=1))
        scale2 = np.max(np.linalg.norm(points2_centered, axis=1))

        if scale1 > 0:
            points1_normalized = points1_centered / scale1
        else:
            points1_normalized = points1_centered

        if scale2 > 0:
            points2_normalized = points2_centered / scale2
        else:
            points2_normalized = points2_centered

        try:
            points1_aligned = self._icp(points1_normalized, points2_normalized)
            return points1_aligned, points2_normalized
        except Exception:
            return points1_normalized, points2_normalized

    def _icp(
        self,
        source: np.ndarray,
        target: np.ndarray,
        max_iterations: int = 50,
        tolerance: float = 1e-6,
    ) -> np.ndarray:
        """
        Simple ICP alignment.

        Args:
            source: Source point cloud.
            target: Target point cloud.
            max_iterations: Maximum number of iterations.
            tolerance: Convergence tolerance.

        Returns:
            Aligned source point cloud.
        """
        source_aligned = source.copy()
        target_tree = cKDTree(target)

        for _ in range(max_iterations):
            _, indices = target_tree.query(source_aligned)
            target_matched = target[indices]

            source_centroid = np.mean(source_aligned, axis=0)
            target_centroid = np.mean(target_matched, axis=0)

            source_centered = source_aligned - source_centroid
            target_centered = target_matched - target_centroid

            H = source_centered.T @ target_centered
            U, _, Vt = np.linalg.svd(H)
            R = Vt.T @ U.T

            if np.linalg.det(R) < 0:
                Vt[-1, :] *= -1
                R = Vt.T @ U.T

            t = target_centroid - R @ source_centroid

            source_new = (R @ source_aligned.T).T + t

            error = np.mean(np.linalg.norm(source_new - source_aligned, axis=1))
            source_aligned = source_new

            if error < tolerance:
                break

        return source_aligned

    def _voxelize(self, step_path: Path) -> np.ndarray:
        """Voxelize a STEP file (loads from disk)."""
        points, _ = self._load_and_sample(step_path)
        return self._voxelize_from_points(points)

    def _voxelize_from_points(self, points: np.ndarray) -> np.ndarray:
        """Voxelize from pre-loaded point cloud."""
        min_coords = np.min(points, axis=0)
        max_coords = np.max(points, axis=0)

        range_coords = max_coords - min_coords
        range_coords[range_coords == 0] = 1

        normalized = (points - min_coords) / range_coords
        voxel_indices = (normalized * (self._voxel_resolution - 1)).astype(int)
        voxel_indices = np.clip(voxel_indices, 0, self._voxel_resolution - 1)

        voxels = np.zeros(
            (self._voxel_resolution,) * 3,
            dtype=bool,
        )

        # NumPy advanced indexing instead of Python loop
        voxels[
            voxel_indices[:, 0],
            voxel_indices[:, 1],
            voxel_indices[:, 2],
        ] = True

        return voxels

    async def calculate_cad_structure_metrics(
        self,
        generated_step_path: Path,
        ground_truth_step_path: Path,
    ) -> CadStructureMetrics:
        """
        Calculate Drawing2CAD-style CAD structure metrics.

        Args:
            generated_step_path: Path to generated STEP file.
            ground_truth_step_path: Path to ground truth STEP file.

        Returns:
            CadStructureMetrics with command, sketch, and extrusion accuracy.
        """
        loop = asyncio.get_running_loop()

        gen_counts = await loop.run_in_executor(
            None, self._extract_cad_structure, generated_step_path
        )
        gt_counts = await loop.run_in_executor(
            None, self._extract_cad_structure, ground_truth_step_path
        )

        line_acc = self._calculate_count_accuracy(gen_counts.lines, gt_counts.lines)
        arc_acc = self._calculate_count_accuracy(gen_counts.arcs, gt_counts.arcs)
        circle_acc = self._calculate_count_accuracy(gen_counts.circles, gt_counts.circles)

        plane_acc = self._calculate_count_accuracy(
            gen_counts.planar_faces, gt_counts.planar_faces
        )

        cylindrical_acc = self._calculate_count_accuracy(
            gen_counts.cylindrical_faces, gt_counts.cylindrical_faces
        )
        conical_acc = self._calculate_count_accuracy(
            gen_counts.conical_faces, gt_counts.conical_faces
        )
        transform_acc = (cylindrical_acc + conical_acc) / 2.0

        extent_acc = self._calculate_count_accuracy(
            gen_counts.total_faces(), gt_counts.total_faces()
        )

        extrusion_overall = (plane_acc + transform_acc + extent_acc) / 3.0

        total_gen = gen_counts.total_edges() + gen_counts.total_faces()
        total_gt = gt_counts.total_edges() + gt_counts.total_faces()
        command_acc = self._calculate_count_accuracy(total_gen, total_gt)

        return CadStructureMetrics(
            command_accuracy=command_acc,
            sketch_primitive=SketchPrimitiveAccuracy(
                line=line_acc,
                arc=arc_acc,
                circle=circle_acc,
            ),
            extrusion=ExtrusionAccuracy(
                plane=plane_acc,
                transform=transform_acc,
                extent=extent_acc,
                overall=extrusion_overall,
            ),
        )

    def _extract_cad_structure(self, step_path: Path) -> CadStructureCounts:
        """
        Extract CAD structural elements from STEP file.

        Args:
            step_path: Path to STEP file.

        Returns:
            CadStructureCounts with element counts.
        """
        try:
            from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
            from OCP.GeomAbs import (
                GeomAbs_Circle,
                GeomAbs_Cone,
                GeomAbs_Cylinder,
                GeomAbs_Ellipse,
                GeomAbs_Line,
                GeomAbs_Plane,
                GeomAbs_Sphere,
                GeomAbs_Torus,
            )
            from OCP.IFSelect import IFSelect_RetDone
            from OCP.STEPControl import STEPControl_Reader
            from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
            from OCP.TopExp import TopExp_Explorer
            from OCP.TopoDS import TopoDS

            reader = STEPControl_Reader()
            status = reader.ReadFile(str(step_path))

            if status != IFSelect_RetDone:
                return self._empty_counts()

            reader.TransferRoots()
            shape = reader.OneShape()

            lines = 0
            arcs = 0
            circles = 0

            edge_explorer = TopExp_Explorer(shape, TopAbs_EDGE)
            while edge_explorer.More():
                edge = TopoDS.Edge_s(edge_explorer.Current())
                try:
                    adaptor = BRepAdaptor_Curve(edge)
                    curve_type = adaptor.GetType()

                    if curve_type == GeomAbs_Line:
                        lines += 1
                    elif curve_type == GeomAbs_Circle:
                        first = adaptor.FirstParameter()
                        last = adaptor.LastParameter()
                        if abs(last - first - 2 * math.pi) < 0.01:
                            circles += 1
                        else:
                            arcs += 1
                    elif curve_type == GeomAbs_Ellipse:
                        arcs += 1
                except Exception:
                    pass
                edge_explorer.Next()

            planar = 0
            cylindrical = 0
            conical = 0
            spherical = 0
            toroidal = 0
            other = 0

            face_explorer = TopExp_Explorer(shape, TopAbs_FACE)
            while face_explorer.More():
                face = TopoDS.Face_s(face_explorer.Current())
                try:
                    adaptor = BRepAdaptor_Surface(face)
                    surface_type = adaptor.GetType()

                    if surface_type == GeomAbs_Plane:
                        planar += 1
                    elif surface_type == GeomAbs_Cylinder:
                        cylindrical += 1
                    elif surface_type == GeomAbs_Cone:
                        conical += 1
                    elif surface_type == GeomAbs_Sphere:
                        spherical += 1
                    elif surface_type == GeomAbs_Torus:
                        toroidal += 1
                    else:
                        other += 1
                except Exception:
                    other += 1
                face_explorer.Next()

            return CadStructureCounts(
                lines=lines,
                arcs=arcs,
                circles=circles,
                planar_faces=planar,
                cylindrical_faces=cylindrical,
                conical_faces=conical,
                spherical_faces=spherical,
                toroidal_faces=toroidal,
                other_faces=other,
            )

        except Exception as e:
            print(f"Error extracting CAD structure from {step_path}: {e}")
            raise ValueError(f"Failed to extract CAD structure from {step_path}: {e}")

    def _empty_counts(self) -> CadStructureCounts:
        """Return empty structure counts."""
        return CadStructureCounts(
            lines=0,
            arcs=0,
            circles=0,
            planar_faces=0,
            cylindrical_faces=0,
            conical_faces=0,
            spherical_faces=0,
            toroidal_faces=0,
            other_faces=0,
        )

    def _calculate_count_accuracy(self, generated: int, ground_truth: int) -> float:
        """
        Calculate accuracy based on count comparison.

        Uses 1 - |gen - gt| / max(gen, gt, 1) formula.

        Args:
            generated: Count from generated model.
            ground_truth: Count from ground truth model.

        Returns:
            Accuracy value between 0 and 1.
        """
        if generated == 0 and ground_truth == 0:
            return 1.0

        max_count = max(generated, ground_truth, 1)
        accuracy = 1.0 - abs(generated - ground_truth) / max_count

        return max(0.0, accuracy)
