"""
AquaBrain Voxel Engine V2.0
===========================
High-performance voxel grid using NumPy for spatial representation.
Uses SciPy for safety margin dilation (morphological operations).

The voxel grid provides perfect synchronization between:
- World coordinates (ITM/Revit meters)
- Grid indices (numpy array i,j,k)

Formula:
    Index = int((Coordinate - Origin) / Resolution)
    Coordinate = Origin + (Index + 0.5) * Resolution

Author: AquaBrain Engineering
"""

import numpy as np
from scipy.ndimage import binary_dilation
from dataclasses import dataclass
from typing import Tuple, List, Optional, Dict, Any


@dataclass
class VoxelGrid:
    """
    Represents physical space as a mathematical matrix.
    Synchronizes between array indices (i,j,k) and world coordinates (x,y,z).

    Attributes:
        grid: NumPy array where 0=air, 1=obstacle
        origin: Bottom-left corner in real space (ITM/Revit coordinates)
        resolution: Size of each cell in meters (e.g., 0.1m = 10cm)
    """
    grid: np.ndarray
    origin: Tuple[float, float, float]
    resolution: float

    def world_to_grid(self, x: float, y: float, z: float) -> Tuple[int, int, int]:
        """
        Convert world coordinates to grid indices.

        Args:
            x, y, z: World coordinates in meters (ITM/Revit)

        Returns:
            (vx, vy, vz): Grid indices
        """
        vx = int((x - self.origin[0]) / self.resolution)
        vy = int((y - self.origin[1]) / self.resolution)
        vz = int((z - self.origin[2]) / self.resolution)
        return (vx, vy, vz)

    def grid_to_world(self, vx: int, vy: int, vz: int) -> Tuple[float, float, float]:
        """
        Convert grid index back to world coordinate (cell center).

        Args:
            vx, vy, vz: Grid indices

        Returns:
            (x, y, z): World coordinates at cell center
        """
        x = self.origin[0] + (vx + 0.5) * self.resolution
        y = self.origin[1] + (vy + 0.5) * self.resolution
        z = self.origin[2] + (vz + 0.5) * self.resolution
        return (x, y, z)

    def is_valid(self, vx: int, vy: int, vz: int) -> bool:
        """Check if grid index is within bounds."""
        shape = self.grid.shape
        return (
            0 <= vx < shape[0] and
            0 <= vy < shape[1] and
            0 <= vz < shape[2]
        )

    def is_free(self, vx: int, vy: int, vz: int) -> bool:
        """Check if voxel is unoccupied (air) and valid."""
        if not self.is_valid(vx, vy, vz):
            return False
        return self.grid[vx, vy, vz] == 0

    def get_neighbors(self, vx: int, vy: int, vz: int,
                     connectivity: int = 26) -> List[Tuple[int, int, int]]:
        """
        Get valid free neighboring voxels.

        Args:
            vx, vy, vz: Current voxel indices
            connectivity: 6 (faces only), 18 (faces+edges), or 26 (full)

        Returns:
            List of (vx, vy, vz) tuples for free neighbors
        """
        neighbors = []

        # 6-connectivity (face neighbors)
        directions = [
            (1, 0, 0), (-1, 0, 0),
            (0, 1, 0), (0, -1, 0),
            (0, 0, 1), (0, 0, -1),
        ]

        if connectivity >= 18:
            # Add edge neighbors (12 more)
            directions.extend([
                (1, 1, 0), (1, -1, 0), (-1, 1, 0), (-1, -1, 0),
                (1, 0, 1), (1, 0, -1), (-1, 0, 1), (-1, 0, -1),
                (0, 1, 1), (0, 1, -1), (0, -1, 1), (0, -1, -1),
            ])

        if connectivity >= 26:
            # Add corner neighbors (8 more)
            directions.extend([
                (1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1),
                (-1, -1, 1), (-1, 1, -1), (1, -1, -1), (-1, -1, -1),
            ])

        for dx, dy, dz in directions:
            nx, ny, nz = vx + dx, vy + dy, vz + dz
            if self.is_free(nx, ny, nz):
                neighbors.append((nx, ny, nz))

        return neighbors

    @property
    def shape(self) -> Tuple[int, int, int]:
        """Grid dimensions (nx, ny, nz)."""
        return self.grid.shape

    @property
    def occupied_count(self) -> int:
        """Number of occupied voxels."""
        return int(np.sum(self.grid))

    @property
    def free_count(self) -> int:
        """Number of free (air) voxels."""
        return int(np.prod(self.grid.shape) - np.sum(self.grid))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize grid metadata (not the full array)."""
        return {
            "resolution_m": self.resolution,
            "dimensions": list(self.grid.shape),
            "origin": list(self.origin),
            "occupied_count": self.occupied_count,
            "free_count": self.free_count,
            "total_voxels": int(np.prod(self.grid.shape)),
            "memory_mb": self.grid.nbytes / (1024 * 1024),
        }


class VoxelEngine:
    """
    High-performance voxelization engine using NumPy.

    Features:
        - Fast obstacle burning with NumPy slicing (O(1) in Python terms)
        - Safety margin dilation using SciPy morphological operations
        - Perfect world<->grid coordinate synchronization
    """

    DEFAULT_RESOLUTION = 0.2  # 20cm voxels (good balance of detail vs memory)
    DEFAULT_PADDING = 1.0     # 1m padding around project bounds

    def __init__(self, resolution: float = DEFAULT_RESOLUTION, padding: float = DEFAULT_PADDING):
        """
        Initialize the voxel engine.

        Args:
            resolution: Voxel size in meters (smaller = more detail, more memory)
            padding: Extra space around project bounds in meters
        """
        self.resolution = resolution
        self.padding = padding

    def create_grid(self, bounds_min: List[float], bounds_max: List[float]) -> VoxelGrid:
        """
        Create empty voxel grid from project bounds.

        Args:
            bounds_min: [x_min, y_min, z_min] - Project minimum corner
            bounds_max: [x_max, y_max, z_max] - Project maximum corner

        Returns:
            VoxelGrid with all cells initialized to 0 (air)
        """
        # Calculate origin (including padding)
        origin = (
            bounds_min[0] - self.padding,
            bounds_min[1] - self.padding,
            bounds_min[2] - self.padding
        )

        # Calculate required grid size
        size_x = int((bounds_max[0] + self.padding - origin[0]) / self.resolution) + 1
        size_y = int((bounds_max[1] + self.padding - origin[1]) / self.resolution) + 1
        size_z = int((bounds_max[2] + self.padding - origin[2]) / self.resolution) + 1

        # Create zero matrix (0=air, 1=obstacle)
        # Using uint8 for memory efficiency (1 byte per voxel)
        grid_data = np.zeros((size_x, size_y, size_z), dtype=np.uint8)

        return VoxelGrid(grid=grid_data, origin=origin, resolution=self.resolution)

    def burn_obstacle(self, voxel_grid: VoxelGrid,
                      obs_min: List[float], obs_max: List[float]) -> None:
        """
        Burn an obstacle (wall/column/beam) into the grid using NumPy slicing.

        This is very fast - O(1) in Python terms because NumPy handles
        the iteration in optimized C code.

        Args:
            voxel_grid: The grid to modify
            obs_min: [x_min, y_min, z_min] - Obstacle minimum corner
            obs_max: [x_max, y_max, z_max] - Obstacle maximum corner
        """
        # Convert world coordinates to grid indices
        start = voxel_grid.world_to_grid(*obs_min)
        end = voxel_grid.world_to_grid(*obs_max)

        # Protect against array bounds overflow
        sx, sy, sz = voxel_grid.grid.shape
        x0, x1 = max(0, start[0]), min(sx, end[0] + 1)
        y0, y1 = max(0, start[1]), min(sy, end[1] + 1)
        z0, z1 = max(0, start[2]), min(sz, end[2] + 1)

        # Fast burn using NumPy slicing
        voxel_grid.grid[x0:x1, y0:y1, z0:z1] = 1

    def burn_obstacles_batch(self, voxel_grid: VoxelGrid,
                              obstacles: List[Dict[str, List[float]]]) -> int:
        """
        Burn multiple obstacles efficiently.

        Args:
            voxel_grid: The grid to modify
            obstacles: List of dicts with 'min' and 'max' keys

        Returns:
            Number of obstacles burned
        """
        count = 0
        for obs in obstacles:
            if 'min' in obs and 'max' in obs:
                self.burn_obstacle(voxel_grid, obs['min'], obs['max'])
                count += 1
        return count

    def apply_safety_dilation(self, voxel_grid: VoxelGrid, iterations: int = 1) -> None:
        """
        Apply safety margin by dilating (expanding) obstacles.

        Uses SciPy's binary_dilation with 26-connected structure.
        Each iteration expands obstacles by ~1 voxel in all directions,
        creating a safety buffer equal to (iterations * resolution) meters.

        Args:
            voxel_grid: The grid to modify (in-place)
            iterations: Number of dilation iterations (1 = resolution meters buffer)
        """
        if iterations <= 0:
            return

        # 26-connected dilation structure (3x3x3 cube)
        structure = np.ones((3, 3, 3), dtype=bool)

        # Apply dilation (expands obstacles)
        dilated = binary_dilation(
            voxel_grid.grid,
            structure=structure,
            iterations=iterations
        )

        # Update grid (convert back to uint8)
        voxel_grid.grid = dilated.astype(np.uint8)

    def apply_custom_dilation(self, voxel_grid: VoxelGrid,
                               margin_meters: float) -> None:
        """
        Apply safety margin with specific distance in meters.

        Args:
            voxel_grid: The grid to modify
            margin_meters: Safety margin in meters
        """
        iterations = max(1, int(margin_meters / self.resolution))
        self.apply_safety_dilation(voxel_grid, iterations)

    def get_slice(self, voxel_grid: VoxelGrid,
                  axis: str, index: int) -> np.ndarray:
        """
        Get a 2D slice of the grid for visualization.

        Args:
            voxel_grid: The grid to slice
            axis: 'x', 'y', or 'z' (perpendicular axis)
            index: Slice index along that axis

        Returns:
            2D numpy array of the slice
        """
        if axis == 'z':
            return voxel_grid.grid[:, :, index]
        elif axis == 'y':
            return voxel_grid.grid[:, index, :]
        elif axis == 'x':
            return voxel_grid.grid[index, :, :]
        else:
            raise ValueError(f"Invalid axis: {axis}. Use 'x', 'y', or 'z'")


# Singleton instance for convenience
voxel_engine = VoxelEngine()
