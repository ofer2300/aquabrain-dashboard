"""
AquaBrain Voxelizer Service V1.0
================================
Converts 3D geometry into a voxel grid for pathfinding.

The voxel grid allows the A* algorithm to navigate 3D space
while avoiding obstacles (beams, columns, ducts, etc.).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional, Set
import math


@dataclass
class BoundingBox:
    """3D Axis-Aligned Bounding Box."""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    @property
    def size(self) -> Tuple[float, float, float]:
        """Get dimensions."""
        return (
            self.max_x - self.min_x,
            self.max_y - self.min_y,
            self.max_z - self.min_z
        )

    @property
    def center(self) -> Tuple[float, float, float]:
        """Get center point."""
        return (
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
            (self.min_z + self.max_z) / 2
        )


@dataclass
class VoxelGrid:
    """
    3D Voxel Grid for spatial analysis.

    Attributes:
        resolution: Size of each voxel in meters
        dimensions: (x, y, z) count of voxels
        origin: World coordinates of grid origin
        occupied: Set of (x, y, z) indices that are blocked
        weights: Optional weight for each voxel (for path cost)
    """
    resolution: float
    dimensions: Tuple[int, int, int]
    origin: Tuple[float, float, float]
    occupied: Set[Tuple[int, int, int]] = field(default_factory=set)
    weights: Dict[Tuple[int, int, int], float] = field(default_factory=dict)

    def is_valid(self, x: int, y: int, z: int) -> bool:
        """Check if voxel index is within grid bounds."""
        return (
            0 <= x < self.dimensions[0] and
            0 <= y < self.dimensions[1] and
            0 <= z < self.dimensions[2]
        )

    def is_free(self, x: int, y: int, z: int) -> bool:
        """Check if voxel is unoccupied and valid."""
        return self.is_valid(x, y, z) and (x, y, z) not in self.occupied

    def world_to_voxel(self, world_x: float, world_y: float, world_z: float) -> Tuple[int, int, int]:
        """Convert world coordinates to voxel indices."""
        return (
            int((world_x - self.origin[0]) / self.resolution),
            int((world_y - self.origin[1]) / self.resolution),
            int((world_z - self.origin[2]) / self.resolution)
        )

    def voxel_to_world(self, vx: int, vy: int, vz: int) -> Tuple[float, float, float]:
        """Convert voxel indices to world coordinates (center of voxel)."""
        return (
            self.origin[0] + (vx + 0.5) * self.resolution,
            self.origin[1] + (vy + 0.5) * self.resolution,
            self.origin[2] + (vz + 0.5) * self.resolution
        )

    def get_weight(self, x: int, y: int, z: int) -> float:
        """Get traversal weight for voxel (default 1.0)."""
        return self.weights.get((x, y, z), 1.0)

    def get_neighbors(self, x: int, y: int, z: int, diagonal: bool = True) -> List[Tuple[int, int, int]]:
        """Get valid neighboring voxels."""
        neighbors = []

        # 6-connectivity (faces)
        directions = [
            (1, 0, 0), (-1, 0, 0),
            (0, 1, 0), (0, -1, 0),
            (0, 0, 1), (0, 0, -1),
        ]

        # Add 26-connectivity (corners and edges) if diagonal
        if diagonal:
            directions.extend([
                (1, 1, 0), (1, -1, 0), (-1, 1, 0), (-1, -1, 0),
                (1, 0, 1), (1, 0, -1), (-1, 0, 1), (-1, 0, -1),
                (0, 1, 1), (0, 1, -1), (0, -1, 1), (0, -1, -1),
                (1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1),
                (-1, -1, 1), (-1, 1, -1), (1, -1, -1), (-1, -1, -1),
            ])

        for dx, dy, dz in directions:
            nx, ny, nz = x + dx, y + dy, z + dz
            if self.is_free(nx, ny, nz):
                neighbors.append((nx, ny, nz))

        return neighbors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "resolution_m": self.resolution,
            "dimensions": list(self.dimensions),
            "origin": list(self.origin),
            "occupied_count": len(self.occupied),
            "total_voxels": self.dimensions[0] * self.dimensions[1] * self.dimensions[2],
            "free_voxels": (
                self.dimensions[0] * self.dimensions[1] * self.dimensions[2]
                - len(self.occupied)
            ),
        }


class Voxelizer:
    """
    Converts geometry data into a voxel grid.

    The voxelizer takes geometry from Revit (walls, floors, beams, etc.)
    and creates a navigable 3D grid for the A* pathfinder.
    """

    DEFAULT_RESOLUTION = 0.1  # 10cm voxels
    CLEARANCE_MARGIN = 0.15   # 15cm clearance around obstacles

    def __init__(self, resolution: float = DEFAULT_RESOLUTION):
        """Initialize voxelizer with resolution in meters."""
        self.resolution = resolution

    def voxelize_geometry(self, geometry_data: Dict[str, Any]) -> VoxelGrid:
        """
        Convert geometry data to voxel grid.

        Args:
            geometry_data: Geometry extracted from Revit

        Returns:
            VoxelGrid ready for pathfinding
        """
        # Calculate bounding box of the building
        building = geometry_data.get("building", {})
        bounds = self._calculate_bounds(geometry_data)

        # Calculate grid dimensions
        size_x = bounds.max_x - bounds.min_x
        size_y = bounds.max_y - bounds.min_y
        size_z = bounds.max_z - bounds.min_z

        dim_x = max(1, int(math.ceil(size_x / self.resolution)))
        dim_y = max(1, int(math.ceil(size_y / self.resolution)))
        dim_z = max(1, int(math.ceil(size_z / self.resolution)))

        # Create grid
        grid = VoxelGrid(
            resolution=self.resolution,
            dimensions=(dim_x, dim_y, dim_z),
            origin=(bounds.min_x, bounds.min_y, bounds.min_z),
        )

        # Mark obstacles as occupied
        self._voxelize_obstructions(grid, geometry_data.get("obstructions", []))
        self._voxelize_structure(grid, geometry_data.get("geometry", {}))

        return grid

    def _calculate_bounds(self, geometry_data: Dict) -> BoundingBox:
        """Calculate bounding box of all geometry."""
        building = geometry_data.get("building", {})

        # Default bounds based on building size
        total_area = building.get("total_area_sqm", 100)
        side = math.sqrt(total_area)
        height = building.get("height_m", 3)

        return BoundingBox(
            min_x=0,
            min_y=0,
            min_z=0,
            max_x=side,
            max_y=side,
            max_z=height,
        )

    def _voxelize_obstructions(self, grid: VoxelGrid, obstructions: List[Dict]):
        """Mark obstruction volumes as occupied."""
        for obs in obstructions:
            obs_type = obs.get("type", "")
            clearance = obs.get("clearance", self.CLEARANCE_MARGIN)

            if "path" in obs:
                # Line-based obstruction (duct, pipe)
                self._voxelize_path(grid, obs["path"], clearance)
            elif "location" in obs and "size" in obs:
                # Box-based obstruction (beam, column)
                self._voxelize_box(grid, obs["location"], obs["size"], clearance)

    def _voxelize_structure(self, grid: VoxelGrid, geometry: Dict):
        """Mark structural elements as occupied."""
        # Mark walls
        for wall in geometry.get("walls", []):
            if "start" in wall and "end" in wall:
                path = [wall["start"], wall["end"]]
                height = wall.get("height", 3)
                self._voxelize_path(grid, path, 0.15, height)

        # Mark columns
        for col in geometry.get("columns", []):
            if "location" in col:
                size = col.get("size", [0.4, 0.4])
                self._voxelize_box(grid, col["location"], [*size, 10], 0.1)

    def _voxelize_path(
        self,
        grid: VoxelGrid,
        path: List[List[float]],
        radius: float,
        height: Optional[float] = None
    ):
        """Voxelize a path (for pipes, ducts)."""
        if len(path) < 2:
            return

        for i in range(len(path) - 1):
            start = path[i]
            end = path[i + 1]
            self._voxelize_line(grid, start, end, radius)

    def _voxelize_line(
        self,
        grid: VoxelGrid,
        start: List[float],
        end: List[float],
        radius: float
    ):
        """Voxelize a line segment with radius."""
        # Convert to voxel space
        v_start = grid.world_to_voxel(*start[:3])
        v_end = grid.world_to_voxel(*end[:3])

        # Bresenham-like 3D line drawing with thickness
        dx = abs(v_end[0] - v_start[0])
        dy = abs(v_end[1] - v_start[1])
        dz = abs(v_end[2] - v_start[2])

        steps = max(dx, dy, dz, 1)
        radius_voxels = int(math.ceil(radius / grid.resolution))

        for step in range(steps + 1):
            t = step / steps if steps > 0 else 0
            cx = int(v_start[0] + t * (v_end[0] - v_start[0]))
            cy = int(v_start[1] + t * (v_end[1] - v_start[1]))
            cz = int(v_start[2] + t * (v_end[2] - v_start[2]))

            # Mark voxels within radius
            for rx in range(-radius_voxels, radius_voxels + 1):
                for ry in range(-radius_voxels, radius_voxels + 1):
                    for rz in range(-radius_voxels, radius_voxels + 1):
                        if rx*rx + ry*ry + rz*rz <= radius_voxels*radius_voxels:
                            vx, vy, vz = cx + rx, cy + ry, cz + rz
                            if grid.is_valid(vx, vy, vz):
                                grid.occupied.add((vx, vy, vz))

    def _voxelize_box(
        self,
        grid: VoxelGrid,
        location: List[float],
        size: List[float],
        margin: float
    ):
        """Voxelize an axis-aligned box."""
        # Add margin
        half_x = (size[0] / 2) + margin
        half_y = (size[1] / 2) + margin
        half_z = (size[2] / 2) + margin if len(size) > 2 else margin

        min_corner = [
            location[0] - half_x,
            location[1] - half_y,
            location[2] - half_z if len(location) > 2 else 0,
        ]
        max_corner = [
            location[0] + half_x,
            location[1] + half_y,
            location[2] + half_z if len(location) > 2 else half_z * 2,
        ]

        v_min = grid.world_to_voxel(*min_corner)
        v_max = grid.world_to_voxel(*max_corner)

        for vx in range(v_min[0], v_max[0] + 1):
            for vy in range(v_min[1], v_max[1] + 1):
                for vz in range(v_min[2], v_max[2] + 1):
                    if grid.is_valid(vx, vy, vz):
                        grid.occupied.add((vx, vy, vz))


# Singleton instance
voxelizer = Voxelizer()
