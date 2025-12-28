"""
AquaBrain AutoCAD Bridge V1.0
=============================
WSL2 -> PowerShell -> COM -> AutoCAD 2026

This bridge allows AquaBrain to control AutoCAD from WSL2 Linux
by executing PowerShell scripts that use COM automation.

Features:
- Get active document info
- Read selection set area
- Add text annotations
- Draw revision clouds
- Execute AutoLISP commands

Author: AquaBrain V8.0
Date: 2025-12-04
"""

from __future__ import annotations
import subprocess
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


# ============================================================================
# CONFIGURATION
# ============================================================================

# Mock mode - set to True when AutoCAD is not available
MOCK_MODE = os.environ.get("AUTOCAD_MOCK_MODE", "false").lower() == "true"

# PowerShell execution timeout (seconds)
POWERSHELL_TIMEOUT = 30


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class AutoCADDocument:
    """Information about an AutoCAD document."""
    name: str
    path: str
    is_saved: bool
    model_space_count: int
    selection_count: int


@dataclass
class SelectionInfo:
    """Information about selected objects."""
    count: int
    total_area: float
    objects: List[Dict[str, Any]]
    bounding_box: Optional[Tuple[float, float, float, float]] = None


@dataclass
class BridgeResult:
    """Result from AutoCAD bridge operation."""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    mock_mode: bool = False


# ============================================================================
# POWERSHELL COMMAND EXECUTOR
# ============================================================================

def run_powershell(script: str, timeout: int = POWERSHELL_TIMEOUT) -> BridgeResult:
    """
    Execute a PowerShell script from WSL2.

    Args:
        script: PowerShell script to execute
        timeout: Timeout in seconds

    Returns:
        BridgeResult with success status and data/error
    """
    if MOCK_MODE:
        return BridgeResult(
            success=False,
            data={},
            error="Mock mode enabled",
            mock_mode=True
        )

    try:
        # Escape the script for PowerShell
        escaped_script = script.replace('"', '\\"').replace("'", "''")

        # Run via powershell.exe
        result = subprocess.run(
            ['powershell.exe', '-Command', script],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            return BridgeResult(
                success=False,
                data={},
                error=result.stderr or f"PowerShell exit code: {result.returncode}"
            )

        # Try to parse JSON output
        try:
            data = json.loads(result.stdout.strip())
            return BridgeResult(success=True, data=data)
        except json.JSONDecodeError:
            # Return raw output if not JSON
            return BridgeResult(
                success=True,
                data={"raw_output": result.stdout.strip()}
            )

    except subprocess.TimeoutExpired:
        return BridgeResult(
            success=False,
            data={},
            error=f"PowerShell timeout after {timeout} seconds"
        )
    except FileNotFoundError:
        return BridgeResult(
            success=False,
            data={},
            error="PowerShell not found - is this running in WSL2?"
        )
    except Exception as e:
        return BridgeResult(
            success=False,
            data={},
            error=str(e)
        )


# ============================================================================
# AUTOCAD BRIDGE FUNCTIONS
# ============================================================================

def connect_autocad() -> BridgeResult:
    """
    Connect to running AutoCAD instance.

    Returns:
        BridgeResult with connection status
    """
    script = '''
    try {
        $acad = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
        $doc = $acad.ActiveDocument
        @{
            success = $true
            version = $acad.Version
            document = $doc.Name
            path = $doc.Path
        } | ConvertTo-Json
    } catch {
        @{
            success = $false
            error = $_.Exception.Message
        } | ConvertTo-Json
    }
    '''

    result = run_powershell(script)

    if result.mock_mode:
        # Return mock connection
        return BridgeResult(
            success=True,
            data={
                "success": True,
                "version": "24.0 (AutoCAD 2026 - MOCK)",
                "document": "sump_pit_design.dwg",
                "path": "C:\\Projects\\MEP\\"
            },
            mock_mode=True
        )

    return result


def get_active_document() -> BridgeResult:
    """
    Get information about the active AutoCAD document.

    Returns:
        BridgeResult with document info
    """
    script = '''
    try {
        $acad = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
        $doc = $acad.ActiveDocument
        $modelSpace = $doc.ModelSpace
        $selSet = $doc.SelectionSets

        @{
            success = $true
            name = $doc.Name
            path = $doc.FullName
            is_saved = -not $doc.Saved
            model_space_count = $modelSpace.Count
            selection_sets = $selSet.Count
        } | ConvertTo-Json
    } catch {
        @{
            success = $false
            error = $_.Exception.Message
        } | ConvertTo-Json
    }
    '''

    result = run_powershell(script)

    if result.mock_mode:
        return BridgeResult(
            success=True,
            data={
                "success": True,
                "name": "sump_pit_design.dwg",
                "path": "C:\\Projects\\MEP\\sump_pit_design.dwg",
                "is_saved": True,
                "model_space_count": 245,
                "selection_sets": 2
            },
            mock_mode=True
        )

    return result


def get_selection_area() -> BridgeResult:
    """
    Get the total area of currently selected polylines.

    This function reads the current selection in AutoCAD and
    calculates the combined area of all selected closed polylines.

    Returns:
        BridgeResult with selection info including total area
    """
    script = '''
    try {
        $acad = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
        $doc = $acad.ActiveDocument

        # Get implicit selection (user's current selection)
        $selSet = $null
        try {
            $selSet = $doc.SelectionSets.Item("AQUABRAIN_SEL")
            $selSet.Delete()
        } catch { }

        $selSet = $doc.SelectionSets.Add("AQUABRAIN_SEL")
        $selSet.SelectOnScreen()

        $totalArea = 0.0
        $objects = @()
        $minX = [double]::MaxValue
        $minY = [double]::MaxValue
        $maxX = [double]::MinValue
        $maxY = [double]::MinValue

        foreach ($obj in $selSet) {
            $objData = @{
                type = $obj.ObjectName
                handle = $obj.Handle
            }

            # Get area for closed polylines
            if ($obj.ObjectName -eq "AcDbPolyline" -or $obj.ObjectName -eq "AcDb2dPolyline") {
                if ($obj.Closed) {
                    $area = $obj.Area
                    $totalArea += $area
                    $objData.area = $area
                    $objData.closed = $true

                    # Update bounding box
                    $bounds = $obj.GetBoundingBox([ref]$null, [ref]$null)
                    # Simplified bounding box logic
                }
            }

            $objects += $objData
        }

        # Cleanup
        $selSet.Delete()

        @{
            success = $true
            count = $objects.Count
            total_area = $totalArea
            total_area_sqm = [math]::Round($totalArea / 1000000, 2)
            objects = $objects
        } | ConvertTo-Json -Depth 3
    } catch {
        @{
            success = $false
            error = $_.Exception.Message
        } | ConvertTo-Json
    }
    '''

    result = run_powershell(script)

    if result.mock_mode:
        # Return mock selection data for sump pits
        return BridgeResult(
            success=True,
            data={
                "success": True,
                "count": 3,
                "total_area": 12500000,  # 12.5 sqm in mm^2
                "total_area_sqm": 12.5,
                "objects": [
                    {"type": "AcDbPolyline", "handle": "2A3F", "area": 5000000, "closed": True},
                    {"type": "AcDbPolyline", "handle": "2A40", "area": 4500000, "closed": True},
                    {"type": "AcDbPolyline", "handle": "2A41", "area": 3000000, "closed": True}
                ],
                "bounding_box": [1000, 1000, 5000, 4000]
            },
            mock_mode=True
        )

    return result


def add_text_annotation(
    text: str,
    point: Tuple[float, float, float],
    height: float = 250.0,
    color: int = 3  # Green by default
) -> BridgeResult:
    """
    Add MText annotation to the drawing.

    Args:
        text: The text content
        point: Insertion point (x, y, z)
        height: Text height in drawing units
        color: AutoCAD color index (1=Red, 2=Yellow, 3=Green, etc.)

    Returns:
        BridgeResult with created text info
    """
    x, y, z = point

    script = f'''
    try {{
        $acad = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
        $doc = $acad.ActiveDocument
        $modelSpace = $doc.ModelSpace

        # Create insertion point
        $insertPoint = @({x}, {y}, {z})

        # Add MText
        $mtext = $modelSpace.AddMText($insertPoint, 2000, "{text}")
        $mtext.Height = {height}
        $mtext.Color = {color}

        # Regenerate to show
        $doc.Regen(1)  # acActiveViewport

        @{{
            success = $true
            handle = $mtext.Handle
            text = "{text}"
            point = @({x}, {y}, {z})
        }} | ConvertTo-Json
    }} catch {{
        @{{
            success = $false
            error = $_.Exception.Message
        }} | ConvertTo-Json
    }}
    '''

    result = run_powershell(script)

    if result.mock_mode:
        return BridgeResult(
            success=True,
            data={
                "success": True,
                "handle": "MOCK_2B4F",
                "text": text,
                "point": [x, y, z]
            },
            mock_mode=True
        )

    return result


def draw_revision_cloud(
    points: List[Tuple[float, float]],
    color: int = 1  # Red by default
) -> BridgeResult:
    """
    Draw a revision cloud around specified points.

    Args:
        points: List of (x, y) points defining the cloud boundary
        color: AutoCAD color index

    Returns:
        BridgeResult with created cloud info
    """
    # Convert points to PowerShell array format
    points_str = ",".join([f"@({p[0]},{p[1]},0)" for p in points])

    script = f'''
    try {{
        $acad = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
        $doc = $acad.ActiveDocument
        $modelSpace = $doc.ModelSpace

        # Create polyline points (simplified - real revision cloud would use arcs)
        $points = @({points_str})
        $flatPoints = @()
        foreach ($pt in $points) {{
            $flatPoints += $pt[0]
            $flatPoints += $pt[1]
        }}

        # Add lightweight polyline
        $pline = $modelSpace.AddLightWeightPolyline($flatPoints)
        $pline.Closed = $true
        $pline.Color = {color}
        $pline.Lineweight = 50  # 0.50mm

        $doc.Regen(1)

        @{{
            success = $true
            handle = $pline.Handle
            point_count = $points.Count
        }} | ConvertTo-Json
    }} catch {{
        @{{
            success = $false
            error = $_.Exception.Message
        }} | ConvertTo-Json
    }}
    '''

    result = run_powershell(script)

    if result.mock_mode:
        return BridgeResult(
            success=True,
            data={
                "success": True,
                "handle": "MOCK_CLOUD_1",
                "point_count": len(points)
            },
            mock_mode=True
        )

    return result


def execute_lisp(command: str) -> BridgeResult:
    """
    Execute an AutoLISP command.

    Args:
        command: AutoLISP command string

    Returns:
        BridgeResult with execution result
    """
    # Escape for PowerShell
    escaped_cmd = command.replace('"', '`"').replace("'", "''")

    script = f'''
    try {{
        $acad = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
        $doc = $acad.ActiveDocument

        # Send command to AutoCAD command line
        $doc.SendCommand("{escaped_cmd}`n")

        Start-Sleep -Milliseconds 500

        @{{
            success = $true
            command = "{escaped_cmd}"
        }} | ConvertTo-Json
    }} catch {{
        @{{
            success = $false
            error = $_.Exception.Message
        }} | ConvertTo-Json
    }}
    '''

    result = run_powershell(script)

    if result.mock_mode:
        return BridgeResult(
            success=True,
            data={
                "success": True,
                "command": command,
                "mock": True
            },
            mock_mode=True
        )

    return result


def zoom_to_selection() -> BridgeResult:
    """
    Zoom to the current selection.

    Returns:
        BridgeResult with zoom status
    """
    return execute_lisp("ZOOM E ")


def highlight_objects(handles: List[str], color: int = 1) -> BridgeResult:
    """
    Highlight objects by changing their color temporarily.

    Args:
        handles: List of object handles
        color: Color index to apply

    Returns:
        BridgeResult with highlight status
    """
    handles_str = ",".join([f'"{h}"' for h in handles])

    script = f'''
    try {{
        $acad = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
        $doc = $acad.ActiveDocument

        $handles = @({handles_str})
        $highlighted = 0

        foreach ($handle in $handles) {{
            try {{
                $obj = $doc.HandleToObject($handle)
                $obj.Color = {color}
                $highlighted++
            }} catch {{ }}
        }}

        $doc.Regen(1)

        @{{
            success = $true
            highlighted_count = $highlighted
        }} | ConvertTo-Json
    }} catch {{
        @{{
            success = $false
            error = $_.Exception.Message
        }} | ConvertTo-Json
    }}
    '''

    result = run_powershell(script)

    if result.mock_mode:
        return BridgeResult(
            success=True,
            data={
                "success": True,
                "highlighted_count": len(handles)
            },
            mock_mode=True
        )

    return result


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def test_connection() -> Dict[str, Any]:
    """
    Test the AutoCAD connection and return status.

    Returns:
        Dictionary with connection status
    """
    result = connect_autocad()

    return {
        "connected": result.success,
        "mock_mode": result.mock_mode,
        "data": result.data,
        "error": result.error
    }


def get_sump_pit_selection() -> Dict[str, Any]:
    """
    Get sump pit selection info specifically.

    Returns:
        Dictionary with sump pit area data
    """
    result = get_selection_area()

    if not result.success and not result.mock_mode:
        return {
            "success": False,
            "error": result.error
        }

    data = result.data
    return {
        "success": True,
        "mock_mode": result.mock_mode,
        "pit_count": data.get("count", 0),
        "total_area_sqm": data.get("total_area_sqm", 0),
        "objects": data.get("objects", [])
    }


def annotate_verification(
    text: str,
    center_point: Tuple[float, float],
    status: str = "OK"
) -> Dict[str, Any]:
    """
    Add AquaBrain verification annotation.

    Args:
        text: Verification text
        center_point: Center point for annotation
        status: "OK" (green) or "FAIL" (red)

    Returns:
        Dictionary with annotation result
    """
    color = 3 if status == "OK" else 1  # Green for OK, Red for FAIL
    point = (center_point[0], center_point[1], 0)

    result = add_text_annotation(text, point, height=200.0, color=color)

    return {
        "success": result.success,
        "mock_mode": result.mock_mode,
        "handle": result.data.get("handle"),
        "error": result.error
    }


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    'connect_autocad',
    'get_active_document',
    'get_selection_area',
    'add_text_annotation',
    'draw_revision_cloud',
    'execute_lisp',
    'zoom_to_selection',
    'highlight_objects',
    'test_connection',
    'get_sump_pit_selection',
    'annotate_verification',
    'BridgeResult',
    'AutoCADDocument',
    'SelectionInfo',
    'MOCK_MODE',
]


# ============================================================================
# CLI TEST
# ============================================================================

if __name__ == "__main__":
    print("Testing AutoCAD Bridge...")
    print()

    # Test connection
    conn = test_connection()
    print(f"Connection: {'OK' if conn['connected'] else 'FAILED'}")
    print(f"Mock Mode: {conn['mock_mode']}")
    if conn['data']:
        print(f"Version: {conn['data'].get('version', 'N/A')}")
        print(f"Document: {conn['data'].get('document', 'N/A')}")
    print()

    # Test selection
    print("Testing selection area...")
    sel = get_sump_pit_selection()
    print(f"Pit Count: {sel.get('pit_count', 0)}")
    print(f"Total Area: {sel.get('total_area_sqm', 0)} m²")
