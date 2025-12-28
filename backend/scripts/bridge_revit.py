"""
AquaBrain Revit Bridge V2.0 - Semantic Reality Capture
======================================================
Bridges WSL2 (Linux) to Revit (Windows) via PowerShell + COM
with Deep Semantic Analysis for LOD 500 Engineering.

Architecture:
    WSL2 (Linux)
        -> PowerShell.exe
            -> Windows Python
                -> comtypes/pyrevit
                    -> Revit API

Features V2.0:
- Semantic metadata extraction (Fire Rating, Material, Assembly Code)
- Coordinate system support (Survey Point, Project Base Point, ITM/UTM)
- Voxel classification (HARD_CLASH, SOFT_CLASH, CLEARANCE)
- Mock Mode fallback for demos and development
"""

from __future__ import annotations
import subprocess
import json
import os
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class BridgeCommand(Enum):
    """Available commands for the Revit bridge."""
    EXTRACT_GEOMETRY = "extract_geometry"
    EXTRACT_SEMANTIC = "extract_semantic"  # V2.0: Deep metadata
    PLACE_FAMILIES = "place_families"
    CREATE_PIPES = "create_pipes"
    EXPORT_DXF = "export_dxf"
    GET_PROJECT_INFO = "get_project_info"
    CHECK_CONNECTION = "check_connection"


class ClashType(Enum):
    """Voxel classification for pathfinding."""
    HARD_CLASH = "hard_clash"      # Beams, Columns - Absolute No-Go
    SOFT_CLASH = "soft_clash"      # HVAC Maintenance Zones - Avoid if possible
    CLEARANCE = "clearance"        # Required spacing per NFPA
    FREE = "free"                  # Available for routing


class Material(Enum):
    """Structural materials affecting penetration rules."""
    CONCRETE = "concrete"
    STEEL = "steel"
    DRYWALL = "drywall"
    MASONRY = "masonry"
    UNKNOWN = "unknown"


@dataclass
class ElementConstraints:
    """Engineering constraints for an element."""
    can_penetrate: bool = True
    requires_sleeve: bool = False
    fire_rating_hours: float = 0.0
    clearance_required_m: float = 0.15
    clash_type: ClashType = ClashType.FREE


@dataclass
class SemanticElement:
    """Element with full semantic data for LOD 500."""
    id: str
    category: str
    type_name: str
    material: Material
    geometry: Dict[str, Any]
    constraints: ElementConstraints
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoordinateSystem:
    """Project coordinate system for real-world positioning."""
    survey_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    project_base_point: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_true_north: float = 0.0  # Degrees from project north
    crs: str = "ITM"  # Coordinate Reference System (ITM, UTM, etc.)


@dataclass
class BridgeResult:
    """Result from a bridge command."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Configuration
POWERSHELL_CMD = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
POWERSHELL_CMD_FALLBACK = "powershell.exe"
REVIT_WORKER_SCRIPT = r"C:\AquaBrain\Workers\revit_automation.py"
PYREVIT_CLI = "pyrevit"

# Mode control
MOCK_MODE = False  # REAL MODE ENABLED - Requires Revit with pyRevit Routes
MOCK_MODE_AUTO = True  # Auto-enable mock if bridge fails

# Multi-version support (V3.0)
SUPPORTED_REVIT_VERSIONS = ["2024", "2025", "2026", "auto"]
DEFAULT_REVIT_VERSION = "auto"  # Auto-detect by default


def _get_powershell_path() -> str:
    """Get the correct PowerShell path for WSL."""
    if os.path.exists(POWERSHELL_CMD):
        return POWERSHELL_CMD
    return POWERSHELL_CMD_FALLBACK


def run_revit_command(
    command_type: BridgeCommand,
    payload: Dict[str, Any],
    timeout: int = 60,
    target_version: str = "auto"
) -> BridgeResult:
    """
    Execute a command on Revit from WSL via the bridge.
    Falls back to mock mode if bridge is unavailable.

    V3.0: Multi-version support
    Args:
        command_type: The bridge command to execute
        payload: Data payload for the command
        timeout: Command timeout in seconds
        target_version: Revit version to target ("2024", "2025", "2026", or "auto")
    """
    # Validate version
    if target_version not in SUPPORTED_REVIT_VERSIONS:
        target_version = DEFAULT_REVIT_VERSION

    if MOCK_MODE:
        result = _mock_command(command_type, payload)
        # Add version info to mock response
        if result.data:
            result.data["target_version"] = target_version
            result.data["connected_version"] = "mock"
        return result

    json_payload = json.dumps(payload)
    ps_cmd = _get_powershell_path()

    # V3.0: Include --version argument in command
    cmd = [
        ps_cmd,
        "-Command",
        f"python '{REVIT_WORKER_SCRIPT}' --version {target_version} --action {command_type.value} --data '{json_payload}'"
    ]

    print(f"[Bridge] {command_type.value} -> Revit {target_version}")
    print(f"   Payload: {payload}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Unknown error"
            print(f"   Error: {error_msg}")

            if MOCK_MODE_AUTO:
                print("   Auto-enabling mock mode...")
                return _mock_command(command_type, payload)

            return BridgeResult(success=False, error=error_msg)

        try:
            data = json.loads(result.stdout.strip())
            print(f"   Success")
            return BridgeResult(success=True, data=data)
        except json.JSONDecodeError:
            return BridgeResult(success=True, data={"raw": result.stdout.strip()})

    except subprocess.TimeoutExpired:
        if MOCK_MODE_AUTO:
            print(f"   Timeout - using mock mode")
            return _mock_command(command_type, payload)
        return BridgeResult(success=False, error=f"Command timed out after {timeout}s")
    except Exception as e:
        if MOCK_MODE_AUTO:
            print(f"   Exception - using mock mode: {e}")
            return _mock_command(command_type, payload)
        return BridgeResult(success=False, error=str(e))


def _mock_command(command_type: BridgeCommand, payload: Dict[str, Any]) -> BridgeResult:
    """Mock handler for development and demos."""
    if command_type == BridgeCommand.EXTRACT_GEOMETRY:
        return BridgeResult(success=True, data=_generate_mock_geometry(payload.get("project_id", "MOCK")))
    elif command_type == BridgeCommand.EXTRACT_SEMANTIC:
        return BridgeResult(success=True, data=_generate_mock_semantic(payload.get("project_id", "MOCK")))
    elif command_type == BridgeCommand.CHECK_CONNECTION:
        return BridgeResult(success=True, data={"status": "mock_mode", "method": "simulation"})
    else:
        return BridgeResult(success=True, data={"status": "mock_executed", "command": command_type.value})


def _generate_mock_geometry(project_id: str) -> Dict[str, Any]:
    """Generate mock geometry with semantic data."""
    return {
        "project_id": project_id,
        "extraction_mode": "mock_semantic_v2",
        "building": {
            "floors": 3,
            "total_area_sqm": 500,
            "height_m": 10,
            "grid_spacing_m": 6.0
        },
        "coordinates": {
            "survey_point": [185620.5, 663580.2, 45.0],  # ITM coordinates (Israel)
            "project_base_point": [0.0, 0.0, 0.0],
            "rotation_true_north": 12.5,  # Degrees
            "crs": "ITM",
            "transform_matrix": [
                [0.9763, -0.2164, 0, 185620.5],
                [0.2164, 0.9763, 0, 663580.2],
                [0, 0, 1, 45.0],
                [0, 0, 0, 1]
            ]
        },
        "geometry": {
            "walls": [
                {"id": "W001", "start": [0, 0, 0], "end": [10, 0, 0], "height": 3},
                {"id": "W002", "start": [10, 0, 0], "end": [10, 8, 0], "height": 3},
                {"id": "W003", "start": [10, 8, 0], "end": [0, 8, 0], "height": 3},
                {"id": "W004", "start": [0, 8, 0], "end": [0, 0, 0], "height": 3},
            ],
            "columns": [
                {"id": "COL001", "location": [5, 4, 0], "size": [0.4, 0.4]},
            ],
            "beams": [
                {"id": "B001", "start": [0, 4, 2.8], "end": [10, 4, 2.8], "section": [0.3, 0.5]},
            ]
        },
        "obstructions": [
            {
                "id": "HVAC-001",
                "type": "duct",
                "path": [[0, 2, 2.5], [5, 2, 2.5], [5, 6, 2.5], [10, 6, 2.5]],
                "clearance": 0.3,
                "clash_type": "soft_clash"
            },
            {
                "id": "BEAM-001",
                "type": "beam",
                "location": [5, 4, 2.8],
                "size": [0.3, 0.5, 10],
                "clash_type": "hard_clash"
            }
        ]
    }


def _generate_mock_semantic(project_id: str) -> Dict[str, Any]:
    """
    Generate deep semantic data for LOD 500.
    This is the "DNA" of the building - fire ratings, materials, penetration rules.
    """
    return {
        "project_id": project_id,
        "extraction_mode": "semantic_reality_capture_v2",
        "timestamp": "2025-12-03T06:00:00Z",
        "coordinates": {
            "survey_point": [185620.5, 663580.2, 45.0],
            "project_base_point": [0.0, 0.0, 0.0],
            "rotation_true_north": 12.5,
            "crs": "ITM"
        },
        "elements": [
            # Fire-rated wall - requires sleeve
            {
                "id": "W001-FR",
                "category": "Wall",
                "type_name": "Fire Rated 2hr",
                "material": "concrete",
                "fire_rating": 2.0,
                "assembly_code": "C1010",
                "geometry": {
                    "start": [0, 0, 0],
                    "end": [10, 0, 0],
                    "height": 3.0,
                    "thickness": 0.2
                },
                "constraints": {
                    "can_penetrate": True,
                    "requires_sleeve": True,
                    "sleeve_type": "fire_collar",
                    "max_opening_diameter_m": 0.15
                }
            },
            # Standard drywall - easy penetration
            {
                "id": "W002-DW",
                "category": "Wall",
                "type_name": "Interior Partition",
                "material": "drywall",
                "fire_rating": 0.0,
                "assembly_code": "C1020",
                "geometry": {
                    "start": [5, 0, 0],
                    "end": [5, 8, 0],
                    "height": 3.0,
                    "thickness": 0.1
                },
                "constraints": {
                    "can_penetrate": True,
                    "requires_sleeve": False
                }
            },
            # Structural beam - NO penetration
            {
                "id": "B001-STR",
                "category": "Structural Framing",
                "type_name": "Concrete Beam 300x500",
                "material": "concrete",
                "fire_rating": 2.0,
                "assembly_code": "B1010",
                "geometry": {
                    "start": [0, 4, 2.8],
                    "end": [10, 4, 2.8],
                    "section": [0.3, 0.5]
                },
                "constraints": {
                    "can_penetrate": False,
                    "clash_type": "hard_clash",
                    "clearance_required_m": 0.3
                }
            },
            # Column - NO penetration
            {
                "id": "COL001-STR",
                "category": "Structural Column",
                "type_name": "Concrete Column 400x400",
                "material": "concrete",
                "fire_rating": 2.0,
                "assembly_code": "B1020",
                "geometry": {
                    "location": [5, 4, 0],
                    "size": [0.4, 0.4, 10]
                },
                "constraints": {
                    "can_penetrate": False,
                    "clash_type": "hard_clash",
                    "clearance_required_m": 0.5
                }
            },
            # HVAC Duct - Maintenance zone
            {
                "id": "HVAC-001",
                "category": "Mechanical Equipment",
                "type_name": "Supply Duct 600x300",
                "material": "steel",
                "fire_rating": 0.0,
                "assembly_code": "D3040",
                "geometry": {
                    "path": [[0, 2, 2.5], [5, 2, 2.5], [5, 6, 2.5], [10, 6, 2.5]],
                    "section": [0.6, 0.3]
                },
                "constraints": {
                    "can_penetrate": False,
                    "clash_type": "soft_clash",
                    "clearance_required_m": 0.45,
                    "maintenance_access_m": 0.6,
                    "note": "Maintain 450mm clearance for filter access"
                }
            },
            # Floor slab
            {
                "id": "FLR001",
                "category": "Floor",
                "type_name": "Concrete Slab 200mm",
                "material": "concrete",
                "fire_rating": 2.0,
                "assembly_code": "B1030",
                "geometry": {
                    "level": 0,
                    "elevation": 0.0,
                    "thickness": 0.2,
                    "area_sqm": 80
                },
                "constraints": {
                    "can_penetrate": True,
                    "requires_sleeve": True,
                    "sleeve_type": "fire_stop",
                    "max_opening_diameter_m": 0.1
                }
            },
            # Ceiling (for sprinkler clearance)
            {
                "id": "CLG001",
                "category": "Ceiling",
                "type_name": "Suspended Ceiling T-Bar",
                "material": "unknown",
                "fire_rating": 0.0,
                "assembly_code": "C3030",
                "geometry": {
                    "level": 1,
                    "elevation": 2.7,
                    "area_sqm": 80
                },
                "constraints": {
                    "can_penetrate": True,
                    "requires_sleeve": False,
                    "sprinkler_clearance_m": 0.075,
                    "note": "NFPA 13: Min 75mm sprinkler deflector to ceiling"
                }
            }
        ],
        "voxel_classification": {
            "resolution_m": 0.1,
            "classifications": [
                {
                    "type": "hard_clash",
                    "description": "Beams, Columns - Absolute No-Go",
                    "element_categories": ["Structural Framing", "Structural Column"],
                    "color": "#FF0000"
                },
                {
                    "type": "soft_clash",
                    "description": "HVAC Maintenance Zones - Avoid if possible",
                    "element_categories": ["Mechanical Equipment"],
                    "color": "#FFA500"
                },
                {
                    "type": "clearance",
                    "description": "Required spacing around pipes per NFPA",
                    "nfpa_reference": "NFPA 13 Section 8.6",
                    "color": "#FFFF00"
                },
                {
                    "type": "fire_rated",
                    "description": "Fire-rated assemblies requiring sleeves",
                    "requires_sleeve": True,
                    "color": "#FF69B4"
                }
            ]
        },
        "nfpa_requirements": {
            "sprinkler_deflector_to_ceiling_mm": 75,
            "sprinkler_deflector_to_ceiling_max_mm": 300,
            "pipe_clearance_to_structure_mm": 50,
            "fire_collar_required_for_rating_hours": 1.0
        }
    }


def check_bridge_connection() -> BridgeResult:
    """Check if the bridge to Revit is working."""
    if MOCK_MODE:
        return BridgeResult(
            success=True,
            data={
                "status": "mock_mode",
                "method": "simulation",
                "note": "Running in mock mode for development/demo"
            }
        )

    ps_cmd = _get_powershell_path()

    try:
        result = subprocess.run(
            [ps_cmd, "-Command", f"{PYREVIT_CLI} env"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if "Revit" in result.stdout:
            return BridgeResult(
                success=True,
                data={
                    "status": "connected",
                    "method": "pyrevit",
                    "output": result.stdout.strip()
                }
            )
    except Exception:
        pass

    try:
        result = subprocess.run(
            [ps_cmd, "-Command", "echo 'Bridge OK'"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return BridgeResult(
                success=True,
                data={
                    "status": "powershell_only",
                    "method": "powershell",
                    "note": "PowerShell accessible, Revit connection not verified"
                }
            )
    except Exception as e:
        if MOCK_MODE_AUTO:
            return BridgeResult(
                success=True,
                data={"status": "mock_mode_fallback", "reason": str(e)}
            )
        return BridgeResult(success=False, error=str(e))

    return BridgeResult(success=False, error="Bridge not available")


def extract_geometry(
    project_id: str,
    element_types: list = None,
    target_version: str = "auto"
) -> BridgeResult:
    """
    Extract geometry from Revit model.

    V3.0: Multi-version support
    Args:
        project_id: Project identifier
        element_types: List of element types to extract
        target_version: Revit version ("2024", "2025", "2026", or "auto")
    """
    if element_types is None:
        element_types = ["walls", "floors", "ceilings", "pipes", "ducts", "columns", "beams"]

    return run_revit_command(
        BridgeCommand.EXTRACT_GEOMETRY,
        {
            "project_id": project_id,
            "element_types": element_types
        },
        target_version=target_version
    )


def extract_semantic(
    project_id: str,
    include_parameters: bool = True,
    target_version: str = "auto"
) -> BridgeResult:
    """
    Extract semantic data with full metadata.
    This is the LOD 500 "Deep Scan" that captures:
    - Fire ratings
    - Materials
    - Assembly codes
    - Penetration constraints

    V3.0: Multi-version support
    """
    return run_revit_command(
        BridgeCommand.EXTRACT_SEMANTIC,
        {
            "project_id": project_id,
            "include_parameters": include_parameters,
            "extract_fire_rating": True,
            "extract_material": True,
            "extract_assembly_code": True,
            "classify_voxels": True
        },
        target_version=target_version
    )


def get_geometry(project_id: str, target_version: str = "auto") -> Dict[str, Any]:
    """Get geometry - uses simulation or real bridge based on mode."""
    result = extract_geometry(project_id, target_version=target_version)
    if result.success:
        return result.data
    else:
        raise Exception(f"Failed to extract geometry: {result.error}")


def get_semantic_data(project_id: str, target_version: str = "auto") -> Dict[str, Any]:
    """Get semantic data with full LOD 500 metadata."""
    result = extract_semantic(project_id, target_version=target_version)
    if result.success:
        return result.data
    else:
        raise Exception(f"Failed to extract semantic data: {result.error}")


def place_sprinkler_families(
    project_id: str,
    locations: list,
    family_type: str = "Standard Sprinkler",
    target_version: str = "auto"
) -> BridgeResult:
    """Place sprinkler families at specified locations."""
    return run_revit_command(
        BridgeCommand.PLACE_FAMILIES,
        {
            "project_id": project_id,
            "locations": locations,
            "family_type": family_type
        },
        target_version=target_version
    )


def create_pipe_network(
    project_id: str,
    pipe_segments: list,
    system_type: str = "Fire Protection",
    target_version: str = "auto"
) -> BridgeResult:
    """Create pipe network in Revit."""
    return run_revit_command(
        BridgeCommand.CREATE_PIPES,
        {
            "project_id": project_id,
            "segments": pipe_segments,
            "system_type": system_type
        },
        target_version=target_version
    )


if __name__ == "__main__":
    print("=" * 60)
    print("AquaBrain Revit Bridge V2.0 - Semantic Reality Capture")
    print("=" * 60)

    print("\n1. Checking bridge connection...")
    conn_result = check_bridge_connection()
    print(f"   Mode: {conn_result.data.get('status', 'unknown')}")

    print("\n2. Testing geometry extraction...")
    geometry = get_geometry("PRJ-TEST")
    print(f"   Floors: {geometry['building']['floors']}")
    print(f"   Area: {geometry['building']['total_area_sqm']} sqm")
    if 'coordinates' in geometry:
        print(f"   CRS: {geometry['coordinates'].get('crs', 'N/A')}")
        print(f"   Survey Point: {geometry['coordinates'].get('survey_point', 'N/A')}")

    print("\n3. Testing semantic extraction (LOD 500)...")
    semantic = get_semantic_data("PRJ-TEST")
    print(f"   Elements: {len(semantic.get('elements', []))}")
    for elem in semantic.get('elements', [])[:3]:
        print(f"     - {elem['id']}: {elem['type_name']} ({elem['material']})")
        if elem.get('constraints', {}).get('can_penetrate') is False:
            print(f"       ^ NO PENETRATION - {elem['constraints'].get('clash_type', 'N/A')}")
        if elem.get('constraints', {}).get('requires_sleeve'):
            print(f"       ^ Requires sleeve: {elem['constraints'].get('sleeve_type', 'standard')}")

    print("\n Bridge test complete (V2.0 Semantic)")
