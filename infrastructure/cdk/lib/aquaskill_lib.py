"""
AquaSkill Code Interpreter Library
Python 3.11 library for Bedrock Agent Code Interpreter

This module provides hydraulic calculations, NFPA validation, voxelization,
and A* routing for fire sprinkler system design.

Author: AquaBrain V10.0 Platinum
"""
import numpy as np
import math
import json
import heapq
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


# =============================================================================
# CONSTANTS & PIPE DATA
# =============================================================================

C_FACTOR = 120  # Hazen-Williams C factor for Black Steel

# Schedule 40 pipe internal diameters (inches)
PIPE_SCH40: Dict[float, float] = {
    0.75: 0.824,
    1.0: 1.049,
    1.25: 1.380,
    1.5: 1.610,
    2.0: 2.067,
    2.5: 2.469,
    3.0: 3.068,
    4.0: 4.026,
    6.0: 6.065,
    8.0: 7.981,
}

# Fitting equivalent lengths (feet) by pipe diameter
FITTING_EQUIV_LENGTHS = {
    'elbow_90': {1: 2.5, 1.25: 3, 1.5: 4, 2: 5, 2.5: 6, 3: 7, 4: 10, 6: 14},
    'elbow_45': {1: 1.2, 1.25: 1.5, 1.5: 2, 2: 2.5, 2.5: 3, 3: 3.5, 4: 5, 6: 7},
    'tee_flow': {1: 0.5, 1.25: 0.75, 1.5: 1, 2: 1.5, 2.5: 2, 3: 2.5, 4: 3, 6: 5},
    'tee_side': {1: 5, 1.25: 6, 1.5: 8, 2: 10, 2.5: 12, 3: 15, 4: 20, 6: 30},
    'gate_valve': {1: 0.5, 1.25: 0.6, 1.5: 0.8, 2: 1, 2.5: 1.2, 3: 1.5, 4: 2, 6: 3},
    'check_valve': {1: 5, 1.25: 6, 1.5: 7, 2: 10, 2.5: 12, 3: 15, 4: 18, 6: 25},
}

# NFPA 13 Design Tables
NFPA_DESIGN_TABLES = {
    'Light': {
        'density_gpm_sqft': 0.10,
        'design_area_sqft': 1500,
        'max_coverage_sqft': 225,
        'max_spacing_ft': 15.0,
        'min_spacing_ft': 6.0,
        'hose_stream_gpm': 100,
        'duration_min': 30,
    },
    'Ordinary Group 1': {
        'density_gpm_sqft': 0.15,
        'design_area_sqft': 1500,
        'max_coverage_sqft': 130,
        'max_spacing_ft': 15.0,
        'min_spacing_ft': 6.0,
        'hose_stream_gpm': 250,
        'duration_min': 60,
    },
    'Ordinary Group 2': {
        'density_gpm_sqft': 0.20,
        'design_area_sqft': 1500,
        'max_coverage_sqft': 130,
        'max_spacing_ft': 15.0,
        'min_spacing_ft': 6.0,
        'hose_stream_gpm': 250,
        'duration_min': 60,
    },
    'Extra Group 1': {
        'density_gpm_sqft': 0.30,
        'design_area_sqft': 2500,
        'max_coverage_sqft': 100,
        'max_spacing_ft': 12.0,
        'min_spacing_ft': 6.0,
        'hose_stream_gpm': 500,
        'duration_min': 90,
    },
    'Extra Group 2': {
        'density_gpm_sqft': 0.40,
        'design_area_sqft': 2500,
        'max_coverage_sqft': 100,
        'max_spacing_ft': 12.0,
        'min_spacing_ft': 6.0,
        'hose_stream_gpm': 500,
        'duration_min': 120,
    },
}


# =============================================================================
# DATA CLASSES
# =============================================================================

class TrafficLight(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


@dataclass
class HydraulicResult:
    """Result of hydraulic calculation"""
    loss_psi: float
    velocity_fps: float
    flow_gpm: float
    diameter_inch: float
    length_ft: float
    velocity_compliant: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    """Result of NFPA validation"""
    status: TrafficLight
    violations: List[str]
    warnings: List[str]
    compliant: bool

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['status'] = self.status.value
        return result


@dataclass
class PipeSegment:
    """Pipe segment for hydraulic path analysis"""
    id: str
    diameter_inch: float
    length_ft: float
    flow_gpm: float
    elevation_ft: float = 0
    c_factor: int = 120
    fittings: List[Dict] = None

    def __post_init__(self):
        if self.fittings is None:
            self.fittings = []


# =============================================================================
# HYDRAULIC CALCULATIONS
# =============================================================================

def hazen_williams_calc(flow_gpm: float, diameter_inch: float, length_ft: float,
                        c_factor: int = C_FACTOR) -> HydraulicResult:
    """
    Calculates friction loss (PSI) and velocity (FPS) using Hazen-Williams formula.

    Formula: P = (4.52 * Q^1.85) / (C^1.85 * d^4.87) * L
    Velocity: V = (0.4085 * Q) / d^2

    Args:
        flow_gpm: Flow rate in gallons per minute
        diameter_inch: Nominal pipe diameter in inches
        length_ft: Pipe length in feet
        c_factor: Hazen-Williams coefficient (default 120 for black steel)

    Returns:
        HydraulicResult with loss_psi, velocity_fps, and compliance status
    """
    # Get actual internal diameter from Schedule 40 table
    d_actual = PIPE_SCH40.get(diameter_inch, diameter_inch)

    if d_actual <= 0 or flow_gpm <= 0:
        return HydraulicResult(
            loss_psi=0, velocity_fps=0, flow_gpm=flow_gpm,
            diameter_inch=diameter_inch, length_ft=length_ft, velocity_compliant=True
        )

    # Friction Loss: P = (4.52 * Q^1.85) / (C^1.85 * d^4.87) * L
    friction_loss = (4.52 * (flow_gpm ** 1.85) /
                    ((c_factor ** 1.85) * (d_actual ** 4.87))) * length_ft

    # Velocity: V = (0.4085 * Q) / d^2
    velocity = (0.4085 * flow_gpm) / (d_actual ** 2)

    # NFPA 13 recommends max velocity of 20 fps
    velocity_compliant = velocity <= 20.0

    return HydraulicResult(
        loss_psi=round(friction_loss, 3),
        velocity_fps=round(velocity, 2),
        flow_gpm=flow_gpm,
        diameter_inch=diameter_inch,
        length_ft=length_ft,
        velocity_compliant=velocity_compliant
    )


def calculate_fitting_equiv_length(fitting_type: str, diameter_inch: float) -> float:
    """Get equivalent length for a fitting based on pipe diameter"""
    if fitting_type not in FITTING_EQUIV_LENGTHS:
        return 0

    fitting_table = FITTING_EQUIV_LENGTHS[fitting_type]
    closest_dia = min(fitting_table.keys(), key=lambda x: abs(x - diameter_inch))
    return fitting_table[closest_dia]


def analyze_hydraulic_path(segments: List[PipeSegment],
                           remote_pressure_psi: float = 7.0,
                           hose_stream_gpm: float = 250.0) -> Dict[str, Any]:
    """
    Analyzes complete hydraulic path from remote area to water supply.

    Args:
        segments: List of PipeSegment objects from remote to supply
        remote_pressure_psi: Required pressure at most remote sprinkler
        hose_stream_gpm: Hose stream allowance per NFPA 13

    Returns:
        Dict with total pressure required, segment breakdown, and traffic light
    """
    total_friction_loss = 0
    total_elevation_loss = 0
    segment_results = []
    max_velocity = 0

    for segment in segments:
        # Calculate equivalent length for fittings
        fittings_length = 0
        for fitting in segment.fittings:
            fittings_length += calculate_fitting_equiv_length(
                fitting.get('type', ''),
                segment.diameter_inch
            ) * fitting.get('quantity', 1)

        total_length = segment.length_ft + fittings_length

        # Calculate hydraulics
        result = hazen_williams_calc(
            segment.flow_gpm,
            segment.diameter_inch,
            total_length,
            segment.c_factor
        )

        total_friction_loss += result.loss_psi

        # Elevation loss (0.433 psi per foot)
        elev_loss = segment.elevation_ft * 0.433
        total_elevation_loss += elev_loss

        max_velocity = max(max_velocity, result.velocity_fps)

        segment_results.append({
            'segment_id': segment.id,
            'friction_loss_psi': result.loss_psi,
            'velocity_fps': result.velocity_fps,
            'elevation_loss_psi': round(elev_loss, 2),
            'compliant': result.velocity_compliant,
        })

    # Total pressure required
    total_pressure = remote_pressure_psi + total_friction_loss + total_elevation_loss

    # Determine traffic light
    if max_velocity > 25 or total_pressure > 150:
        traffic_light = TrafficLight.RED
    elif max_velocity > 20 or total_pressure > 120:
        traffic_light = TrafficLight.YELLOW
    else:
        traffic_light = TrafficLight.GREEN

    # Calculate total demand
    final_flow = segments[-1].flow_gpm if segments else 0
    total_demand = final_flow + hose_stream_gpm

    return {
        'total_pressure_required_psi': round(total_pressure, 2),
        'total_demand_gpm': round(total_demand, 1),
        'friction_loss_psi': round(total_friction_loss, 2),
        'elevation_loss_psi': round(total_elevation_loss, 2),
        'max_velocity_fps': round(max_velocity, 2),
        'segment_results': segment_results,
        'traffic_light': traffic_light.value,
    }


def size_pipe_for_flow(flow_gpm: float, max_velocity: float = 20.0) -> float:
    """
    Determines minimum pipe diameter for given flow and max velocity.

    Args:
        flow_gpm: Required flow rate
        max_velocity: Maximum allowed velocity (default 20 fps per NFPA 13)

    Returns:
        Nominal pipe diameter in inches
    """
    for nominal, actual in sorted(PIPE_SCH40.items()):
        velocity = (0.4085 * flow_gpm) / (actual ** 2)
        if velocity <= max_velocity:
            return nominal

    # Return largest available if none fit
    return max(PIPE_SCH40.keys())


# =============================================================================
# NFPA VALIDATION
# =============================================================================

def validate_nfpa_spacing(sprinkler_coords: List[Tuple[float, float, float]],
                          hazard_class: str = 'Light') -> ValidationResult:
    """
    Validates spacing between sprinklers per NFPA 13.

    Args:
        sprinkler_coords: List of (x, y, z) coordinates in feet
        hazard_class: Occupancy hazard classification

    Returns:
        ValidationResult with violations and traffic light status
    """
    criteria = NFPA_DESIGN_TABLES.get(hazard_class, NFPA_DESIGN_TABLES['Light'])
    min_dist = criteria['min_spacing_ft']
    max_dist = criteria['max_spacing_ft']

    violations = []
    warnings = []
    coords = np.array(sprinkler_coords)

    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            # Calculate 2D distance (ignore Z for spacing check)
            dist = np.linalg.norm(coords[i][:2] - coords[j][:2])

            if dist < min_dist:
                violations.append(
                    f"Cold Soldering Risk: Spacing {dist:.2f}ft < {min_dist}ft "
                    f"between sprinkler {i} and {j}"
                )
            elif dist > max_dist:
                violations.append(
                    f"Coverage Gap: Spacing {dist:.2f}ft > {max_dist}ft "
                    f"between sprinkler {i} and {j}"
                )

    # Determine status
    if violations:
        status = TrafficLight.RED
    elif warnings:
        status = TrafficLight.YELLOW
    else:
        status = TrafficLight.GREEN

    return ValidationResult(
        status=status,
        violations=violations,
        warnings=warnings,
        compliant=len(violations) == 0
    )


def validate_deflector_distance(sprinkler_positions: List[Dict],
                                 ceiling_type: str = 'smooth') -> ValidationResult:
    """
    Validates sprinkler deflector distance to ceiling per NFPA 13 Section 8.6.2.

    Args:
        sprinkler_positions: List of dicts with 'id' and 'deflector_to_ceiling_inch'
        ceiling_type: Type of ceiling construction

    Returns:
        ValidationResult with violations
    """
    min_distance = 1.0  # inches
    max_distance = 12.0  # inches for standard spray

    if ceiling_type == 'smooth':
        max_distance = 6.0  # Recommended for smooth ceiling

    violations = []
    warnings = []

    for pos in sprinkler_positions:
        deflector_dist = pos.get('deflector_to_ceiling_inch', 0)
        sprinkler_id = pos.get('id', 'unknown')

        if deflector_dist < min_distance:
            violations.append(
                f"Sprinkler {sprinkler_id}: Deflector distance {deflector_dist}\" "
                f"below minimum {min_distance}\" (NFPA 13 Section 8.6.2)"
            )
        elif deflector_dist > max_distance:
            violations.append(
                f"Sprinkler {sprinkler_id}: Deflector distance {deflector_dist}\" "
                f"exceeds maximum {max_distance}\" (NFPA 13 Section 8.6.2)"
            )

    status = TrafficLight.RED if violations else TrafficLight.GREEN

    return ValidationResult(
        status=status,
        violations=violations,
        warnings=warnings,
        compliant=len(violations) == 0
    )


def calculate_design_demand(area_sqft: float, hazard_class: str = 'Light') -> Dict[str, float]:
    """
    Calculates system design demand per NFPA 13.

    Args:
        area_sqft: Total protected area in square feet
        hazard_class: Occupancy hazard classification

    Returns:
        Dict with demand_gpm, hose_stream_gpm, duration_min, total_water_gallons
    """
    criteria = NFPA_DESIGN_TABLES.get(hazard_class, NFPA_DESIGN_TABLES['Light'])

    design_area = min(area_sqft, criteria['design_area_sqft'])
    demand_gpm = design_area * criteria['density_gpm_sqft']
    hose_stream = criteria['hose_stream_gpm']
    duration = criteria['duration_min']

    # Total water supply required
    total_water = (demand_gpm + hose_stream) * duration

    return {
        'design_area_sqft': design_area,
        'density_gpm_sqft': criteria['density_gpm_sqft'],
        'demand_gpm': round(demand_gpm, 1),
        'hose_stream_gpm': hose_stream,
        'total_demand_gpm': round(demand_gpm + hose_stream, 1),
        'duration_min': duration,
        'total_water_gallons': round(total_water, 0),
    }


# =============================================================================
# VOXELIZATION & ROUTING
# =============================================================================

def voxelize_obstacles(dimensions: Tuple[int, int, int],
                       obstacles: List[Dict]) -> np.ndarray:
    """
    Creates a boolean grid for A* routing.

    Args:
        dimensions: (L, W, H) in voxel units
        obstacles: List of bounding boxes with 'start' and 'end' coordinates

    Returns:
        3D numpy array where 1 = occupied, 0 = free
    """
    grid = np.zeros(dimensions, dtype=np.int8)

    for obs in obstacles:
        x1, y1, z1 = obs['start']
        x2, y2, z2 = obs['end']
        grid[x1:x2, y1:y2, z1:z2] = 1  # Mark occupied

    return grid


def astar_3d(grid: np.ndarray, start: Tuple[int, int, int],
             goal: Tuple[int, int, int]) -> Optional[List[Tuple[int, int, int]]]:
    """
    A* pathfinding algorithm for 3D grid.

    Args:
        grid: 3D occupancy grid (1 = blocked, 0 = free)
        start: Starting coordinate (x, y, z)
        goal: Goal coordinate (x, y, z)

    Returns:
        List of coordinates forming the path, or None if no path found
    """
    def heuristic(a: Tuple, b: Tuple) -> float:
        return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))

    def neighbors(pos: Tuple) -> List[Tuple]:
        """Get valid neighbors (6-connected)"""
        dirs = [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]
        result = []
        for d in dirs:
            n = (pos[0]+d[0], pos[1]+d[1], pos[2]+d[2])
            if (0 <= n[0] < grid.shape[0] and
                0 <= n[1] < grid.shape[1] and
                0 <= n[2] < grid.shape[2] and
                grid[n] == 0):
                result.append(n)
        return result

    # Priority queue: (f_score, counter, position)
    counter = 0
    open_set = [(heuristic(start, goal), counter, start)]
    came_from = {}
    g_score = {start: 0}

    while open_set:
        _, _, current = heapq.heappop(open_set)

        if current == goal:
            # Reconstruct path
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            return path[::-1]

        for neighbor in neighbors(current):
            tentative_g = g_score[current] + 1

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor, goal)
                counter += 1
                heapq.heappush(open_set, (f_score, counter, neighbor))

    return None  # No path found


def optimize_pipe_path(path: List[Tuple[int, int, int]],
                       voxel_size_ft: float = 0.328) -> Dict[str, Any]:
    """
    Optimizes a voxel path into pipe segments.

    Args:
        path: List of voxel coordinates
        voxel_size_ft: Size of each voxel in feet (default 10cm = 0.328ft)

    Returns:
        Dict with optimized segments and total length
    """
    if not path or len(path) < 2:
        return {'segments': [], 'total_length_ft': 0}

    segments = []
    current_dir = None
    segment_start = path[0]

    for i in range(1, len(path)):
        # Determine direction
        dx = path[i][0] - path[i-1][0]
        dy = path[i][1] - path[i-1][1]
        dz = path[i][2] - path[i-1][2]
        new_dir = (dx, dy, dz)

        if new_dir != current_dir:
            if current_dir is not None:
                # End current segment
                length = math.sqrt(
                    (path[i-1][0] - segment_start[0]) ** 2 +
                    (path[i-1][1] - segment_start[1]) ** 2 +
                    (path[i-1][2] - segment_start[2]) ** 2
                ) * voxel_size_ft

                segments.append({
                    'start': segment_start,
                    'end': path[i-1],
                    'length_ft': round(length, 2),
                    'direction': current_dir,
                })

            segment_start = path[i-1]
            current_dir = new_dir

    # Add final segment
    if current_dir is not None:
        length = math.sqrt(
            (path[-1][0] - segment_start[0]) ** 2 +
            (path[-1][1] - segment_start[1]) ** 2 +
            (path[-1][2] - segment_start[2]) ** 2
        ) * voxel_size_ft

        segments.append({
            'start': segment_start,
            'end': path[-1],
            'length_ft': round(length, 2),
            'direction': current_dir,
        })

    total_length = sum(s['length_ft'] for s in segments)

    return {
        'segments': segments,
        'total_length_ft': round(total_length, 2),
        'segment_count': len(segments),
    }


# =============================================================================
# BILL OF MATERIALS
# =============================================================================

def generate_bom(pipe_segments: List[Dict], sprinkler_count: int,
                 fittings: List[Dict] = None) -> Dict[str, Any]:
    """
    Generates Bill of Materials for LOD 500 fabrication.

    Args:
        pipe_segments: List of pipe segment dicts with 'diameter_inch' and 'length_ft'
        sprinkler_count: Total number of sprinkler heads
        fittings: Optional list of fitting dicts

    Returns:
        BOM dict with totals and breakdowns
    """
    # Aggregate pipe by diameter
    pipe_breakdown = {}
    total_pipe_length = 0

    for segment in pipe_segments:
        dia = segment.get('diameter_inch', 1)
        length = segment.get('length_ft', 0)

        key = f"{dia}_inch"
        pipe_breakdown[key] = pipe_breakdown.get(key, 0) + length
        total_pipe_length += length

    # Round all values
    for key in pipe_breakdown:
        pipe_breakdown[key] = round(pipe_breakdown[key], 1)

    # Count fittings by type
    fitting_breakdown = {}
    if fittings:
        for fitting in fittings:
            f_type = fitting.get('type', 'unknown')
            fitting_breakdown[f_type] = fitting_breakdown.get(f_type, 0) + 1

    total_fittings = sum(fitting_breakdown.values())

    return {
        'total_pipe_length_ft': round(total_pipe_length, 1),
        'pipe_breakdown': pipe_breakdown,
        'sprinkler_count': sprinkler_count,
        'fitting_count': total_fittings,
        'fitting_breakdown': fitting_breakdown,
        'generated_at': 'UTC_TIMESTAMP',
        'lod_level': 500,
    }


# =============================================================================
# MASTER EXECUTION WRAPPER
# =============================================================================

def run_pipeline(input_json: str) -> str:
    """
    Master execution wrapper for AquaSkill pipeline.

    Args:
        input_json: JSON string with pipeline inputs

    Returns:
        JSON string with pipeline results
    """
    data = json.loads(input_json)
    results = {
        'hydraulics': [],
        'validation': [],
        'bom': None,
        'status': 'GREEN',
        'errors': [],
    }

    try:
        # 1. Run Hydraulics
        if 'pipes' in data:
            for pipe in data['pipes']:
                res = hazen_williams_calc(
                    pipe.get('flow', 0),
                    pipe.get('diameter', 1),
                    pipe.get('length', 10)
                )
                if not res.velocity_compliant:
                    results['status'] = 'RED'
                    results['errors'].append(
                        f"CRITICAL: High velocity {res.velocity_fps} fps in pipe {pipe.get('id', 'unknown')}"
                    )
                results['hydraulics'].append(res.to_dict())

        # 2. Run Spacing Validation
        if 'sprinklers' in data:
            hazard_class = data.get('hazard_class', 'Light')
            spacing_result = validate_nfpa_spacing(data['sprinklers'], hazard_class)
            results['validation'].append(spacing_result.to_dict())

            if spacing_result.status == TrafficLight.RED:
                results['status'] = 'RED'
                results['errors'].extend(spacing_result.violations)

        # 3. Generate BOM
        if 'pipes' in data:
            sprinkler_count = len(data.get('sprinklers', []))
            results['bom'] = generate_bom(
                data['pipes'],
                sprinkler_count,
                data.get('fittings', [])
            )

        # 4. Calculate Design Demand
        if 'area_sqft' in data:
            hazard_class = data.get('hazard_class', 'Light')
            results['design_demand'] = calculate_design_demand(
                data['area_sqft'],
                hazard_class
            )

    except Exception as e:
        results['status'] = 'RED'
        results['errors'].append(f"Pipeline error: {str(e)}")

    return json.dumps(results, indent=2)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == '__main__':
    # Test hydraulic calculation
    result = hazen_williams_calc(100, 2.0, 100)
    print(f"Hydraulic Test: {result}")

    # Test spacing validation
    sprinklers = [(0, 0, 10), (10, 0, 10), (20, 0, 10)]
    spacing_result = validate_nfpa_spacing(sprinklers, 'Light')
    print(f"Spacing Test: {spacing_result}")

    # Test full pipeline
    test_input = json.dumps({
        'pipes': [
            {'id': 'P1', 'flow': 50, 'diameter': 1.5, 'length': 20},
            {'id': 'P2', 'flow': 100, 'diameter': 2.0, 'length': 50},
        ],
        'sprinklers': [(0, 0, 10), (12, 0, 10), (24, 0, 10)],
        'hazard_class': 'Light',
        'area_sqft': 5000,
    })

    pipeline_result = run_pipeline(test_input)
    print(f"Pipeline Result:\n{pipeline_result}")
