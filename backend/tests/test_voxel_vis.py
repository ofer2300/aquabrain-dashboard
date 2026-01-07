"""
Voxel Engine Visualization Test
===============================
Proof of Sync: Demonstrates perfect synchronization between
world coordinates (ITM/Revit) and grid indices (NumPy).

This script:
1. Creates a voxel grid from project bounds
2. Burns a concrete column into the grid
3. Applies safety dilation
4. Visualizes a horizontal slice with real-world coordinates
"""

import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.voxel_engine import VoxelEngine, VoxelGrid


def print_slice_visualization(grid_obj: VoxelGrid, z_index: int) -> None:
    """
    Print a horizontal slice (Top View) of the grid with coordinates.

    Args:
        grid_obj: The VoxelGrid to visualize
        z_index: Z-index to slice at
    """
    matrix = grid_obj.grid[:, :, z_index]
    nx, ny = matrix.shape

    # Get real-world elevation
    _, _, world_z = grid_obj.grid_to_world(0, 0, z_index)

    print(f"\n{'='*60}")
    print(f"  GRID SLICE AT Z-INDEX {z_index}")
    print(f"  Real World Elevation: {world_z:.2f}m")
    print(f"  Grid Shape: {nx} x {ny}")
    print(f"{'='*60}")

    # Legend
    print(f"\n  Legend: ## = Obstacle  .. = Air\n")

    # Print Y axis (from top to bottom in visual, high Y to low Y)
    for y in range(ny - 1, -1, -1):
        # Get real-world Y coordinate
        _, world_y, _ = grid_obj.grid_to_world(0, y, 0)
        row_str = ""
        for x in range(nx):
            val = matrix[x, y]
            char = "##" if val == 1 else ".."
            row_str += char
        print(f"  Y={world_y:6.1f} | {row_str}")

    # Print X axis ruler
    print("  " + " " * 10 + "-" * (nx * 2))

    # Print X coordinate labels (every 2 columns to save space)
    x_coords = []
    for x in range(0, nx, 2):
        world_x, _, _ = grid_obj.grid_to_world(x, 0, 0)
        x_coords.append(f"{world_x:.0f}")
    print("  X Axis:     " + "   ".join(x_coords))


def print_grid_info(grid_obj: VoxelGrid, label: str = "") -> None:
    """Print grid statistics."""
    info = grid_obj.to_dict()
    print(f"\n--- Grid Info{f' ({label})' if label else ''} ---")
    print(f"  Dimensions: {info['dimensions']}")
    print(f"  Resolution: {info['resolution_m']}m per voxel")
    print(f"  Origin: {info['origin']}")
    print(f"  Total voxels: {info['total_voxels']:,}")
    print(f"  Occupied: {info['occupied_count']:,}")
    print(f"  Free: {info['free_count']:,}")
    print(f"  Memory: {info['memory_mb']:.2f} MB")


def run_simulation():
    """Main simulation demonstrating coordinate synchronization."""

    print("\n" + "="*60)
    print("  AQUABRAIN VOXEL ENGINE - PROOF OF SYNC")
    print("="*60)

    # 1. Define project bounds (simulated ITM coordinates)
    # Imagine a small room: X=100-105m, Y=200-205m, Z=0-3m
    bounds_min = [100.0, 200.0, 0.0]
    bounds_max = [105.0, 205.0, 3.0]

    print(f"\n1. PROJECT BOUNDS")
    print(f"   Min: {bounds_min}")
    print(f"   Max: {bounds_max}")

    # 2. Initialize engine with 0.5m resolution (for clear visualization)
    engine = VoxelEngine(resolution=0.5, padding=0.0)
    vgrid = engine.create_grid(bounds_min, bounds_max)

    print(f"\n2. GRID CREATED")
    print(f"   Resolution: {engine.resolution}m")
    print_grid_info(vgrid, "Initial")

    # 3. Verify coordinate sync: test a known point
    test_world = (102.5, 202.5, 1.5)  # Center of room
    test_grid = vgrid.world_to_grid(*test_world)
    back_to_world = vgrid.grid_to_world(*test_grid)

    print(f"\n3. COORDINATE SYNC TEST")
    print(f"   World -> Grid: {test_world} -> {test_grid}")
    print(f"   Grid -> World: {test_grid} -> {back_to_world}")
    print(f"   Sync OK: {all(abs(a - b) < engine.resolution for a, b in zip(test_world, back_to_world))}")

    # 4. Create a concrete column in the center
    # Column at X=102-103, Y=202-203, Z=0-3 (full height)
    col_min = [102.0, 202.0, 0.0]
    col_max = [103.0, 203.0, 3.0]

    print(f"\n4. BURNING COLUMN")
    print(f"   Column Min: {col_min}")
    print(f"   Column Max: {col_max}")

    engine.burn_obstacle(vgrid, col_min, col_max)
    print_grid_info(vgrid, "After Column")

    # 5. Visualize BEFORE dilation
    print("\n5. VISUALIZATION - BEFORE DILATION")
    print_slice_visualization(vgrid, z_index=2)

    # 6. Apply safety dilation
    print(f"\n6. APPLYING SAFETY DILATION (1 iteration = {engine.resolution}m buffer)")
    engine.apply_safety_dilation(vgrid, iterations=1)
    print_grid_info(vgrid, "After Dilation")

    # 7. Visualize AFTER dilation
    print("\n7. VISUALIZATION - AFTER DILATION")
    print_slice_visualization(vgrid, z_index=2)

    # 8. Summary
    print("\n" + "="*60)
    print("  SYNC VERIFICATION COMPLETE")
    print("="*60)
    print("""
  The visualization shows:
  - The concrete column (##) at coordinates X=102-103, Y=202-203
  - After dilation, the column expanded by 1 voxel (0.5m) in all directions
  - This creates a safety buffer for pipe routing

  Key Insight:
  - Grid index [4,4] corresponds to world coordinate ~(102, 202)
  - Each step in the grid = exactly {res}m in the real world
  - SciPy dilation expands obstacles uniformly in all directions
""".format(res=engine.resolution))

    return vgrid


def test_coordinate_accuracy():
    """Test coordinate conversion accuracy."""
    print("\n--- COORDINATE ACCURACY TEST ---")

    engine = VoxelEngine(resolution=0.1, padding=0.0)
    vgrid = engine.create_grid([0.0, 0.0, 0.0], [10.0, 10.0, 5.0])

    test_cases = [
        (0.0, 0.0, 0.0),
        (5.0, 5.0, 2.5),
        (9.9, 9.9, 4.9),
        (2.35, 7.81, 1.23),
    ]

    for world in test_cases:
        grid = vgrid.world_to_grid(*world)
        back = vgrid.grid_to_world(*grid)
        error = tuple(abs(a - b) for a, b in zip(world, back))
        max_error = max(error)
        status = "PASS" if max_error < engine.resolution else "FAIL"
        print(f"  {world} -> {grid} -> {back} | Error: {max_error:.3f}m [{status}]")


if __name__ == "__main__":
    vgrid = run_simulation()
    test_coordinate_accuracy()
