"""
AquaBrain A* Pathfinder Service V1.0
====================================
3D A* pathfinding for optimal pipe routing.

This module finds the shortest path through a voxel grid
while avoiding obstacles and respecting engineering constraints.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional, Set
from heapq import heappush, heappop
import math

from .voxelizer import VoxelGrid


@dataclass
class PipeRoute:
    """
    Calculated pipe route.

    Attributes:
        waypoints: List of (x, y, z) world coordinates
        total_length_m: Total route length in meters
        turn_count: Number of direction changes
        elevation_changes: Number of vertical level changes
        cost: Path cost (lower is better)
    """
    waypoints: List[Tuple[float, float, float]]
    total_length_m: float
    turn_count: int = 0
    elevation_changes: int = 0
    cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "waypoints": [list(w) for w in self.waypoints],
            "total_length_m": round(self.total_length_m, 2),
            "turn_count": self.turn_count,
            "elevation_changes": self.elevation_changes,
            "cost": round(self.cost, 2),
        }


@dataclass
class PathNode:
    """Node in the A* search graph."""
    position: Tuple[int, int, int]
    g_cost: float  # Cost from start
    h_cost: float  # Heuristic cost to goal
    parent: Optional[PathNode] = None

    @property
    def f_cost(self) -> float:
        """Total cost (g + h)."""
        return self.g_cost + self.h_cost

    def __lt__(self, other: PathNode) -> bool:
        """For heap comparison."""
        return self.f_cost < other.f_cost


class AStarPathfinder:
    """
    A* Pathfinding for pipe routing.

    Features:
    - 3D pathfinding through voxel space
    - Obstacle avoidance
    - Turn minimization (straighter paths preferred)
    - Elevation change penalties
    - Support for weighted regions
    """

    # Cost weights
    TURN_PENALTY = 2.0          # Extra cost for each direction change
    ELEVATION_PENALTY = 3.0     # Extra cost for vertical changes
    DIAGONAL_COST = 1.414       # sqrt(2) for diagonal movement
    VERTICAL_COST = 1.0         # Cost for vertical movement

    def __init__(self):
        """Initialize pathfinder."""
        pass

    def find_path(
        self,
        grid: VoxelGrid,
        start_world: Tuple[float, float, float],
        end_world: Tuple[float, float, float],
        prefer_straight: bool = True,
    ) -> Optional[PipeRoute]:
        """
        Find optimal path between two points.

        Args:
            grid: VoxelGrid with obstacles marked
            start_world: Start point in world coordinates
            end_world: End point in world coordinates
            prefer_straight: Penalize turns if True

        Returns:
            PipeRoute if path found, None otherwise
        """
        # Convert to voxel coordinates
        start = grid.world_to_voxel(*start_world)
        end = grid.world_to_voxel(*end_world)

        # Validate start and end
        if not grid.is_free(*start):
            # Try to find nearest free voxel
            start = self._find_nearest_free(grid, start)
            if start is None:
                return None

        if not grid.is_free(*end):
            end = self._find_nearest_free(grid, end)
            if end is None:
                return None

        # A* search
        path = self._astar(grid, start, end, prefer_straight)

        if path is None:
            return None

        # Convert path to world coordinates
        waypoints = [grid.voxel_to_world(*p) for p in path]

        # Simplify path (remove unnecessary waypoints)
        waypoints = self._simplify_path(waypoints)

        # Calculate metrics
        total_length = self._calculate_length(waypoints)
        turn_count = self._count_turns(path)
        elevation_changes = self._count_elevation_changes(path)

        return PipeRoute(
            waypoints=waypoints,
            total_length_m=total_length,
            turn_count=turn_count,
            elevation_changes=elevation_changes,
            cost=total_length + turn_count * self.TURN_PENALTY + elevation_changes * self.ELEVATION_PENALTY,
        )

    def _astar(
        self,
        grid: VoxelGrid,
        start: Tuple[int, int, int],
        end: Tuple[int, int, int],
        prefer_straight: bool,
    ) -> Optional[List[Tuple[int, int, int]]]:
        """Core A* algorithm implementation."""
        open_set: List[PathNode] = []
        closed_set: Set[Tuple[int, int, int]] = set()

        # Initialize start node
        start_node = PathNode(
            position=start,
            g_cost=0,
            h_cost=self._heuristic(start, end),
        )
        heappush(open_set, start_node)

        # Track best path to each node
        came_from: Dict[Tuple[int, int, int], PathNode] = {start: start_node}

        iterations = 0
        max_iterations = 100000  # Prevent infinite loops

        while open_set and iterations < max_iterations:
            iterations += 1

            # Get node with lowest f_cost
            current = heappop(open_set)

            # Check if we reached the goal
            if current.position == end:
                return self._reconstruct_path(current)

            closed_set.add(current.position)

            # Explore neighbors
            for neighbor_pos in grid.get_neighbors(*current.position, diagonal=True):
                if neighbor_pos in closed_set:
                    continue

                # Calculate movement cost
                move_cost = self._movement_cost(
                    current.position, neighbor_pos, current.parent, grid
                )

                if prefer_straight and current.parent:
                    # Add turn penalty
                    if self._is_turn(current.parent.position, current.position, neighbor_pos):
                        move_cost += self.TURN_PENALTY

                new_g_cost = current.g_cost + move_cost

                # Check if this is a better path
                existing = came_from.get(neighbor_pos)
                if existing is None or new_g_cost < existing.g_cost:
                    neighbor_node = PathNode(
                        position=neighbor_pos,
                        g_cost=new_g_cost,
                        h_cost=self._heuristic(neighbor_pos, end),
                        parent=current,
                    )
                    came_from[neighbor_pos] = neighbor_node
                    heappush(open_set, neighbor_node)

        return None  # No path found

    def _heuristic(self, a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
        """Euclidean distance heuristic."""
        return math.sqrt(
            (a[0] - b[0]) ** 2 +
            (a[1] - b[1]) ** 2 +
            (a[2] - b[2]) ** 2
        )

    def _movement_cost(
        self,
        from_pos: Tuple[int, int, int],
        to_pos: Tuple[int, int, int],
        parent: Optional[PathNode],
        grid: VoxelGrid,
    ) -> float:
        """Calculate cost of moving between voxels."""
        dx = abs(to_pos[0] - from_pos[0])
        dy = abs(to_pos[1] - from_pos[1])
        dz = abs(to_pos[2] - from_pos[2])

        # Base cost based on distance
        diagonal_moves = min(dx, dy)
        straight_moves = abs(dx - dy)
        vertical_moves = dz

        base_cost = (
            diagonal_moves * self.DIAGONAL_COST +
            straight_moves * 1.0 +
            vertical_moves * self.VERTICAL_COST
        )

        # Apply voxel weight
        weight = grid.get_weight(*to_pos)
        base_cost *= weight

        # Elevation change penalty
        if dz > 0:
            base_cost += self.ELEVATION_PENALTY

        return base_cost

    def _is_turn(
        self,
        prev: Tuple[int, int, int],
        current: Tuple[int, int, int],
        next_pos: Tuple[int, int, int],
    ) -> bool:
        """Check if movement from prev->current->next is a turn."""
        dir1 = (
            current[0] - prev[0],
            current[1] - prev[1],
            current[2] - prev[2],
        )
        dir2 = (
            next_pos[0] - current[0],
            next_pos[1] - current[1],
            next_pos[2] - current[2],
        )
        return dir1 != dir2

    def _reconstruct_path(self, node: PathNode) -> List[Tuple[int, int, int]]:
        """Reconstruct path from end node."""
        path = []
        current = node
        while current:
            path.append(current.position)
            current = current.parent
        return list(reversed(path))

    def _find_nearest_free(
        self,
        grid: VoxelGrid,
        pos: Tuple[int, int, int],
        max_radius: int = 10,
    ) -> Optional[Tuple[int, int, int]]:
        """Find nearest free voxel to a blocked position."""
        for r in range(1, max_radius + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    for dz in range(-r, r + 1):
                        if abs(dx) == r or abs(dy) == r or abs(dz) == r:
                            test = (pos[0] + dx, pos[1] + dy, pos[2] + dz)
                            if grid.is_free(*test):
                                return test
        return None

    def _simplify_path(
        self,
        waypoints: List[Tuple[float, float, float]],
    ) -> List[Tuple[float, float, float]]:
        """Remove unnecessary waypoints (points on the same line)."""
        if len(waypoints) <= 2:
            return waypoints

        simplified = [waypoints[0]]

        for i in range(1, len(waypoints) - 1):
            prev = simplified[-1]
            current = waypoints[i]
            next_wp = waypoints[i + 1]

            # Check if current is on line between prev and next
            if not self._is_collinear(prev, current, next_wp):
                simplified.append(current)

        simplified.append(waypoints[-1])
        return simplified

    def _is_collinear(
        self,
        a: Tuple[float, float, float],
        b: Tuple[float, float, float],
        c: Tuple[float, float, float],
        tolerance: float = 0.01,
    ) -> bool:
        """Check if three points are collinear."""
        # Vector AB and AC
        ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])

        # Cross product
        cross = (
            ab[1] * ac[2] - ab[2] * ac[1],
            ab[2] * ac[0] - ab[0] * ac[2],
            ab[0] * ac[1] - ab[1] * ac[0],
        )

        # Magnitude of cross product
        mag = math.sqrt(cross[0]**2 + cross[1]**2 + cross[2]**2)

        return mag < tolerance

    def _calculate_length(self, waypoints: List[Tuple[float, float, float]]) -> float:
        """Calculate total path length."""
        total = 0.0
        for i in range(len(waypoints) - 1):
            a, b = waypoints[i], waypoints[i + 1]
            total += math.sqrt(
                (b[0] - a[0]) ** 2 +
                (b[1] - a[1]) ** 2 +
                (b[2] - a[2]) ** 2
            )
        return total

    def _count_turns(self, path: List[Tuple[int, int, int]]) -> int:
        """Count direction changes in path."""
        if len(path) < 3:
            return 0

        turns = 0
        for i in range(1, len(path) - 1):
            if self._is_turn(path[i - 1], path[i], path[i + 1]):
                turns += 1
        return turns

    def _count_elevation_changes(self, path: List[Tuple[int, int, int]]) -> int:
        """Count vertical level changes."""
        if len(path) < 2:
            return 0

        changes = 0
        for i in range(1, len(path)):
            if path[i][2] != path[i - 1][2]:
                changes += 1
        return changes


# Singleton instance
pathfinder = AStarPathfinder()
