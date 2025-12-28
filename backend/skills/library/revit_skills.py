"""
AquaBrain Revit Skills V4.0 - PLATINUM Edition
===============================================
HTTP-based Revit control via pyRevit Routes API.

This module transforms Revit from a standalone application
into an obedient limb of the AquaBrain OS.

Features:
- Direct HTTP communication with Revit
- Script execution in IronPython context
- Transaction management
- Model queries and element manipulation
- Automatic fallback to Mock mode when Revit unavailable

Architecture:
    WSL2 (AquaBrain) --> HTTP --> Windows (pyRevit Routes) --> Revit API

Endpoints:
    /api                 - Routes API info
    /sessioninfo         - Active session/document info
    /exec                - Execute IronPython script
    /exec2               - Execute with enhanced output
"""

from __future__ import annotations
import os
import sys
import json
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import traceback

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from skills.base import (
    AquaSkill, ExecutionResult, ExecutionStatus,
    SkillMetadata, SkillCategory, InputSchema, InputField, FieldType,
    register_skill
)


# =============================================================================
# CONFIGURATION
# =============================================================================

ROUTES_HOST = "localhost"  # Windows host from WSL perspective
ROUTES_PORT = 48884        # pyRevit Routes default port
ROUTES_TIMEOUT = 30        # HTTP timeout in seconds
MOCK_MODE = True           # Fallback when Revit unavailable


def get_windows_host() -> str:
    """Get Windows host IP from WSL."""
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=5
        )
        for line in result.stdout.split("\n"):
            if "default via" in line:
                return line.split()[2]
    except:
        pass
    return "localhost"


def get_routes_endpoint() -> str:
    """Get the full Routes API endpoint."""
    host = get_windows_host()
    return f"http://{host}:{ROUTES_PORT}"


# =============================================================================
# ROUTES API CLIENT
# =============================================================================

class RoutesClient:
    """
    HTTP Client for pyRevit Routes API.
    Handles communication between AquaBrain and Revit.
    """

    def __init__(self, host: str = None, port: int = ROUTES_PORT):
        self.host = host or get_windows_host()
        self.port = port
        self.base_url = f"http://{self.host}:{self.port}"
        self._mock_mode = MOCK_MODE

    def _http_request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
        timeout: int = ROUTES_TIMEOUT
    ) -> Tuple[bool, dict]:
        """
        Make HTTP request via curl (cross-platform).

        Returns:
            (success, response_data)
        """
        url = f"{self.base_url}{path}"

        # Build curl command
        cmd = ["curl", "-s", "-X", method, url]

        if data:
            cmd.extend([
                "-H", "Content-Type: application/json",
                "-d", json.dumps(data)
            ])

        cmd.extend(["--connect-timeout", str(timeout)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )

            if result.returncode != 0:
                return False, {"error": result.stderr or "Connection failed"}

            if not result.stdout.strip():
                return False, {"error": "Empty response"}

            try:
                return True, json.loads(result.stdout)
            except json.JSONDecodeError:
                # Raw text response
                return True, {"result": result.stdout.strip()}

        except subprocess.TimeoutExpired:
            return False, {"error": "Request timed out"}
        except Exception as e:
            return False, {"error": str(e)}

    def is_available(self) -> bool:
        """Check if Routes server is responding."""
        success, response = self._http_request("GET", "/pyrevit/routes/api")
        return success and "error" not in response

    def get_session_info(self) -> dict:
        """Get current Revit session information."""
        success, response = self._http_request("GET", "/pyrevit/routes/sessioninfo")
        if success:
            return response
        return {"error": response.get("error", "Unknown error")}

    def execute_script(self, script: str, engine: str = "ironpython") -> dict:
        """
        Execute an IronPython script in Revit context.

        Args:
            script: Python code to execute
            engine: Script engine (ironpython, cpython)

        Returns:
            Execution result with output
        """
        # Use exec2 for enhanced output
        payload = {
            "script": script,
            "engine": engine
        }

        success, response = self._http_request("POST", "/pyrevit/routes/exec2", payload)

        if success:
            return {
                "success": True,
                "output": response.get("output", response.get("result", "")),
                "result": response
            }
        else:
            return {
                "success": False,
                "error": response.get("error", "Execution failed"),
                "result": response
            }

    def call_route(self, route: str, payload: Optional[dict] = None) -> dict:
        """
        Call a custom pyRevit route.

        Args:
            route: Route path (e.g., "/my-extension/my-route")
            payload: Optional JSON payload

        Returns:
            Route response
        """
        method = "POST" if payload else "GET"
        success, response = self._http_request(method, route, payload)

        return {
            "success": success,
            "data": response
        }


# Global client instance
_routes_client: Optional[RoutesClient] = None


def get_routes_client() -> RoutesClient:
    """Get or create the global Routes client."""
    global _routes_client
    if _routes_client is None:
        _routes_client = RoutesClient()
    return _routes_client


# =============================================================================
# HELPER: REVIT SCRIPT BUILDER
# =============================================================================

class RevitScriptBuilder:
    """Builds IronPython scripts for Revit execution."""

    @staticmethod
    def open_project(file_path: str) -> str:
        """Script to open a Revit project."""
        return f'''
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *

app = __revit__.Application
doc_path = r"{file_path}"

try:
    # Open document
    doc = app.OpenDocumentFile(doc_path)
    print("SUCCESS: Opened project: " + doc.Title)
except Exception as e:
    print("ERROR: " + str(e))
'''

    @staticmethod
    def extract_lod500() -> str:
        """Script to extract LOD 500 data from active document."""
        return '''
import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
import json

doc = __revit__.ActiveUIDocument.Document

def get_element_data(elem):
    """Extract full LOD 500 data from element."""
    data = {
        "id": elem.Id.IntegerValue,
        "category": elem.Category.Name if elem.Category else "Unknown",
        "type_name": elem.Name,
        "location": None,
        "parameters": {},
        "geometry": None
    }

    # Location
    if elem.Location:
        if isinstance(elem.Location, LocationPoint):
            pt = elem.Location.Point
            data["location"] = [pt.X, pt.Y, pt.Z]
        elif isinstance(elem.Location, LocationCurve):
            curve = elem.Location.Curve
            data["location"] = {
                "start": [curve.GetEndPoint(0).X, curve.GetEndPoint(0).Y, curve.GetEndPoint(0).Z],
                "end": [curve.GetEndPoint(1).X, curve.GetEndPoint(1).Y, curve.GetEndPoint(1).Z]
            }

    # Parameters (LOD 500 semantic data)
    for param in elem.Parameters:
        if param.HasValue:
            try:
                if param.StorageType == StorageType.String:
                    data["parameters"][param.Definition.Name] = param.AsString()
                elif param.StorageType == StorageType.Double:
                    data["parameters"][param.Definition.Name] = param.AsDouble()
                elif param.StorageType == StorageType.Integer:
                    data["parameters"][param.Definition.Name] = param.AsInteger()
            except:
                pass

    # Fire rating extraction
    fire_param = elem.LookupParameter("Fire Rating")
    if fire_param and fire_param.HasValue:
        data["fire_rating"] = fire_param.AsString()

    # Material extraction
    mat_param = elem.LookupParameter("Structural Material")
    if mat_param and mat_param.HasValue:
        data["material"] = mat_param.AsValueString()

    return data

# Collect all relevant elements
result = {
    "project_id": doc.Title,
    "elements": [],
    "summary": {}
}

categories = [
    BuiltInCategory.OST_Walls,
    BuiltInCategory.OST_Floors,
    BuiltInCategory.OST_Columns,
    BuiltInCategory.OST_StructuralFraming,
    BuiltInCategory.OST_PipeCurves,
    BuiltInCategory.OST_Sprinklers,
    BuiltInCategory.OST_MechanicalEquipment,
    BuiltInCategory.OST_DuctCurves
]

for cat in categories:
    collector = FilteredElementCollector(doc).OfCategory(cat).WhereElementIsNotElementType()
    for elem in collector:
        try:
            result["elements"].append(get_element_data(elem))
        except:
            pass

result["summary"]["total_elements"] = len(result["elements"])
result["summary"]["extraction_time"] = str(System.DateTime.Now)

print("LOD500_DATA:" + json.dumps(result))
'''

    @staticmethod
    def create_pipes(pipe_data: List[dict]) -> str:
        """Script to create pipe elements in Revit."""
        pipe_json = json.dumps(pipe_data)
        return f'''
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Plumbing import *
import json

doc = __revit__.ActiveUIDocument.Document
pipes_data = json.loads('{pipe_json}')

# Get pipe type
pipe_types = FilteredElementCollector(doc).OfClass(PipeType).ToElements()
pipe_type = pipe_types[0] if pipe_types else None

# Get level
levels = FilteredElementCollector(doc).OfClass(Level).ToElements()
level = levels[0] if levels else None

# Get pipe system type
sys_types = FilteredElementCollector(doc).OfClass(PipingSystemType).ToElements()
sys_type = sys_types[0] if sys_types else None

if not (pipe_type and level and sys_type):
    print("ERROR: Missing required types")
else:
    t = Transaction(doc, "AquaBrain - Create Pipes")
    t.Start()

    created = 0
    for pipe_data in pipes_data:
        try:
            start = XYZ(pipe_data["start"][0], pipe_data["start"][1], pipe_data["start"][2])
            end = XYZ(pipe_data["end"][0], pipe_data["end"][1], pipe_data["end"][2])

            pipe = Pipe.Create(doc, sys_type.Id, pipe_type.Id, level.Id, start, end)

            # Set diameter
            if "diameter" in pipe_data:
                diameter_param = pipe.get_Parameter(BuiltInParameter.RBS_PIPE_DIAMETER_PARAM)
                if diameter_param:
                    diameter_param.Set(pipe_data["diameter"])

            created += 1
        except Exception as e:
            print("Warning: " + str(e))

    t.Commit()
    print("SUCCESS: Created " + str(created) + " pipes")
'''

    @staticmethod
    def auto_tag(category_name: str) -> str:
        """Script to automatically tag elements."""
        return f'''
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view = uidoc.ActiveView

# Find category
category_name = "{category_name}"
category = None
for cat in doc.Settings.Categories:
    if cat.Name == category_name:
        category = cat
        break

if not category:
    print("ERROR: Category not found: " + category_name)
else:
    # Get tag type
    tag_types = FilteredElementCollector(doc).OfClass(FamilySymbol).OfCategory(BuiltInCategory.OST_PipeTags).ToElements()
    tag_type = tag_types[0] if tag_types else None

    if not tag_type:
        print("ERROR: No tag type found")
    else:
        t = Transaction(doc, "AquaBrain - Auto Tag")
        t.Start()

        collector = FilteredElementCollector(doc, view.Id).OfCategoryId(category.Id).WhereElementIsNotElementType()
        tagged = 0

        for elem in collector:
            try:
                ref = Reference(elem)
                loc = elem.Location
                if isinstance(loc, LocationPoint):
                    pt = loc.Point
                elif isinstance(loc, LocationCurve):
                    pt = loc.Curve.Evaluate(0.5, True)
                else:
                    continue

                IndependentTag.Create(doc, view.Id, ref, False, TagMode.TM_ADDBY_CATEGORY, TagOrientation.Horizontal, pt)
                tagged += 1
            except:
                pass

        t.Commit()
        print("SUCCESS: Tagged " + str(tagged) + " elements")
'''

    @staticmethod
    def export_navisworks(export_path: str) -> str:
        """Script to export to Navisworks NWC."""
        return f'''
import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document
export_path = r"{export_path}"

try:
    options = NavisworksExportOptions()
    options.ExportScope = NavisworksExportScope.Model
    options.Coordinates = NavisworksCoordinates.Shared

    doc.Export(System.IO.Path.GetDirectoryName(export_path),
               System.IO.Path.GetFileNameWithoutExtension(export_path),
               options)

    print("SUCCESS: Exported to " + export_path)
except Exception as e:
    print("ERROR: " + str(e))
'''


# =============================================================================
# MOCK DATA GENERATORS
# =============================================================================

class MockRevitData:
    """Generates realistic mock data when Revit is unavailable."""

    @staticmethod
    def lod500_extraction(project_id: str) -> dict:
        """Generate mock LOD 500 extraction data."""
        return {
            "project_id": project_id,
            "extraction_mode": "MOCK_SIMULATION",
            "timestamp": datetime.now().isoformat(),
            "building": {
                "floors": 3,
                "total_area_sqm": 1500,
                "height_m": 12,
                "ceiling_height_m": 2.7
            },
            "coordinates": {
                "survey_point": [180000.0, 650000.0, 0.0],
                "project_base_point": [0.0, 0.0, 0.0],
                "rotation_true_north": 15.5,
                "crs": "ITM"
            },
            "elements": [
                {
                    "id": "WALL-001",
                    "category": "Wall",
                    "type_name": "Concrete 250mm",
                    "material": "Concrete B-30",
                    "fire_rating": 2.0,
                    "assembly_code": "B2010",
                    "geometry": {"start": [0, 0, 0], "end": [10, 0, 3]}
                },
                {
                    "id": "BEAM-001",
                    "category": "Structural Framing",
                    "type_name": "IPE 300",
                    "material": "Steel S235",
                    "fire_rating": 1.5,
                    "assembly_code": "B1020",
                    "geometry": {"start": [0, 0, 2.7], "end": [10, 0, 2.7]}
                },
                {
                    "id": "DUCT-001",
                    "category": "Duct",
                    "type_name": "Rectangular Duct 400x300",
                    "material": "Galvanized Steel",
                    "geometry": {"path": [[0, 2, 2.5], [10, 2, 2.5]]}
                }
            ],
            "obstructions": [
                {"type": "duct", "path": [[0, 2, 2.5], [10, 2, 2.5]], "clearance": 0.15},
                {"type": "beam", "location": [5, 0, 2.4], "size": [0.3, 10, 0.4]}
            ],
            "summary": {
                "total_elements": 3,
                "categories": ["Wall", "Structural Framing", "Duct"],
                "has_fire_ratings": True,
                "has_materials": True
            }
        }

    @staticmethod
    def pipe_creation_result(pipe_count: int) -> dict:
        """Generate mock pipe creation result."""
        return {
            "success": True,
            "created_count": pipe_count,
            "message": f"[MOCK] Created {pipe_count} pipe segments",
            "elements_created": [
                {"id": f"PIPE-{i:04d}", "length_m": 3.0 + (i * 0.5)}
                for i in range(pipe_count)
            ]
        }

    @staticmethod
    def tagging_result(element_count: int) -> dict:
        """Generate mock tagging result."""
        return {
            "success": True,
            "tagged_count": element_count,
            "message": f"[MOCK] Tagged {element_count} elements"
        }


# =============================================================================
# SKILL: OPEN PROJECT
# =============================================================================

@register_skill
class Skill_OpenProject(AquaSkill):
    """Open a Revit project file via Routes API."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="Open Revit Project",
            description="Opens a .rvt project file in Revit via Routes API",
            category=SkillCategory.REVIT,
            icon="FolderOpen",
            color="#FF6B00",
            tags=["revit", "project", "open", "routes"],
            requires_revit=True
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="file_path",
                label="Project File Path",
                type=FieldType.TEXT,
                required=True,
                placeholder="C:\\Projects\\MyProject.rvt",
                description="Full Windows path to .rvt file"
            )
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        file_path = inputs.get("file_path", "")

        client = get_routes_client()

        if not client.is_available():
            # Mock mode
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"[MOCK] Opened project: {file_path}",
                output={"project": file_path, "mock_mode": True}
            )

        # Execute via Routes
        script = RevitScriptBuilder.open_project(file_path)
        result = client.execute_script(script)

        if result.get("success"):
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"Opened project: {file_path}",
                output=result
            )
        else:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="Failed to open project",
                error=result.get("error", "Unknown error")
            )


# =============================================================================
# SKILL: EXTRACT LOD 500
# =============================================================================

@register_skill
class Skill_ExtractLOD500(AquaSkill):
    """Extract LOD 500 data from active Revit document."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="Extract LOD 500 Data",
            description="Extracts full semantic geometry, fire ratings, materials, and assembly codes from Revit",
            category=SkillCategory.REVIT,
            icon="Database",
            color="#00D4AA",
            tags=["revit", "lod500", "extraction", "geometry", "bim"],
            requires_revit=True,
            estimated_duration_sec=30
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="project_id",
                label="Project ID",
                type=FieldType.TEXT,
                required=False,
                default="active",
                description="Project identifier (uses active document if 'active')"
            ),
            InputField(
                name="include_geometry",
                label="Include Detailed Geometry",
                type=FieldType.BOOLEAN,
                required=False,
                default=True
            )
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        project_id = inputs.get("project_id", "active")

        client = get_routes_client()

        if not client.is_available():
            # Mock mode - return realistic simulation data
            mock_data = MockRevitData.lod500_extraction(project_id)
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"[MOCK] Extracted LOD 500 data for {project_id}",
                output=mock_data,
                metrics={"element_count": len(mock_data["elements"]), "mock_mode": True}
            )

        # Execute via Routes
        script = RevitScriptBuilder.extract_lod500()
        result = client.execute_script(script)

        if result.get("success"):
            output_text = result.get("output", "")
            # Parse LOD500_DATA from output
            if "LOD500_DATA:" in output_text:
                json_str = output_text.split("LOD500_DATA:")[1].strip()
                lod_data = json.loads(json_str)
            else:
                lod_data = {"raw_output": output_text}

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message="Extracted LOD 500 data",
                output=lod_data,
                metrics={"element_count": len(lod_data.get("elements", []))}
            )
        else:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="Failed to extract LOD 500 data",
                error=result.get("error", "Unknown error")
            )


# =============================================================================
# SKILL: HYDRAULIC CALCULATION (INTEGRATION)
# =============================================================================

@register_skill
class Skill_HydraulicCalc(AquaSkill):
    """Perform Hazen-Williams hydraulic calculations on extracted geometry."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="Hydraulic Calculation",
            description="Hazen-Williams pressure loss and velocity calculation for sprinkler systems",
            category=SkillCategory.HYDRAULICS,
            icon="Droplets",
            color="#0088FF",
            tags=["hydraulics", "hazen-williams", "nfpa13", "pressure"],
            requires_revit=False
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="flow_gpm", label="Flow Rate (GPM)", type=FieldType.NUMBER, required=True, default=150),
            InputField(name="diameter_inch", label="Pipe Diameter (in)", type=FieldType.NUMBER, required=True, default=2.0),
            InputField(name="length_ft", label="Pipe Length (ft)", type=FieldType.NUMBER, required=True, default=100),
            InputField(name="c_factor", label="C Factor", type=FieldType.NUMBER, required=False, default=120),
            InputField(
                name="hazard_class",
                label="Hazard Classification",
                type=FieldType.SELECT,
                required=False,
                default="ordinary_1",
                options=[
                    {"value": "light", "label": "Light Hazard"},
                    {"value": "ordinary_1", "label": "Ordinary Hazard Group 1"},
                    {"value": "ordinary_2", "label": "Ordinary Hazard Group 2"},
                    {"value": "extra_1", "label": "Extra Hazard Group 1"},
                    {"value": "extra_2", "label": "Extra Hazard Group 2"}
                ]
            )
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        try:
            from modules.hydraulics import HydraulicCalculator, PipeData

            calc = HydraulicCalculator()
            pipe = PipeData(
                flow_gpm=float(inputs.get("flow_gpm", 150)),
                diameter_inch=float(inputs.get("diameter_inch", 2.0)),
                length_ft=float(inputs.get("length_ft", 100)),
                c_factor=int(inputs.get("c_factor", 120)),
                use_nominal=True,
                schedule="40"
            )

            result = calc.calculate(pipe)

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"Pressure Loss: {result.pressure_loss_psi:.2f} PSI | Velocity: {result.velocity_fps:.2f} fps",
                output={
                    "pressure_loss_psi": round(result.pressure_loss_psi, 3),
                    "velocity_fps": round(result.velocity_fps, 2),
                    "actual_diameter": result.actual_diameter,
                    "velocity_ok": result.velocity_ok,
                    "compliant": result.velocity_ok and result.velocity_fps <= 32
                }
            )

        except ImportError:
            # Fallback calculation if hydraulics module unavailable
            Q = float(inputs.get("flow_gpm", 150))
            d = float(inputs.get("diameter_inch", 2.0))
            L = float(inputs.get("length_ft", 100))
            C = int(inputs.get("c_factor", 120))

            # Hazen-Williams formula
            P = 4.52 * (Q ** 1.85) / (C ** 1.85 * d ** 4.87) * L
            V = 0.4085 * Q / (d ** 2)

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"Pressure Loss: {P:.2f} PSI | Velocity: {V:.2f} fps",
                output={
                    "pressure_loss_psi": round(P, 3),
                    "velocity_fps": round(V, 2),
                    "velocity_ok": V <= 20,
                    "compliant": V <= 32
                }
            )


# =============================================================================
# SKILL: GENERATE MODEL
# =============================================================================

@register_skill
class Skill_GenerateModel(AquaSkill):
    """Generate pipe elements in Revit from calculated layout."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="Generate Pipe Model",
            description="Creates pipe elements in Revit based on AquaBrain calculated layout",
            category=SkillCategory.REVIT,
            icon="PenTool",
            color="#FF00AA",
            tags=["revit", "pipes", "model", "generation", "lod500"],
            requires_revit=True,
            estimated_duration_sec=60
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="pipe_layout",
                label="Pipe Layout Data",
                type=FieldType.JSON,
                required=True,
                description="JSON array of pipe segments [{start: [x,y,z], end: [x,y,z], diameter: float}]"
            )
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        pipe_layout = inputs.get("pipe_layout", [])

        if isinstance(pipe_layout, str):
            try:
                pipe_layout = json.loads(pipe_layout)
            except:
                pipe_layout = []

        if not pipe_layout:
            # Generate sample layout for demo
            pipe_layout = [
                {"start": [0, 0, 2.7], "end": [10, 0, 2.7], "diameter": 0.0508},  # 2" main
                {"start": [2, 0, 2.7], "end": [2, 6, 2.7], "diameter": 0.0381},   # 1.5" branch
                {"start": [5, 0, 2.7], "end": [5, 6, 2.7], "diameter": 0.0381},
                {"start": [8, 0, 2.7], "end": [8, 6, 2.7], "diameter": 0.0381},
            ]

        client = get_routes_client()

        if not client.is_available():
            # Mock mode
            mock_result = MockRevitData.pipe_creation_result(len(pipe_layout))
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=mock_result["message"],
                output=mock_result
            )

        # Execute via Routes
        script = RevitScriptBuilder.create_pipes(pipe_layout)
        result = client.execute_script(script)

        if result.get("success") and "SUCCESS" in result.get("output", ""):
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"Created {len(pipe_layout)} pipe segments in Revit",
                output={"created_count": len(pipe_layout), "result": result}
            )
        else:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="Failed to create pipes",
                error=result.get("error") or result.get("output", "Unknown error")
            )


# =============================================================================
# SKILL: AUTO TAG
# =============================================================================

@register_skill
class Skill_AutoTag(AquaSkill):
    """Automatically tag elements in the active view."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="Auto Tag Elements",
            description="Automatically places tags on elements in the active view",
            category=SkillCategory.REVIT,
            icon="Tag",
            color="#FFD700",
            tags=["revit", "tagging", "documentation", "automation"],
            requires_revit=True
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="category",
                label="Category to Tag",
                type=FieldType.SELECT,
                required=True,
                options=[
                    {"value": "Pipes", "label": "Pipes"},
                    {"value": "Pipe Fittings", "label": "Pipe Fittings"},
                    {"value": "Sprinklers", "label": "Sprinklers"},
                    {"value": "Ducts", "label": "Ducts"},
                    {"value": "Mechanical Equipment", "label": "Mechanical Equipment"}
                ]
            )
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        category = inputs.get("category", "Pipes")

        client = get_routes_client()

        if not client.is_available():
            mock_result = MockRevitData.tagging_result(25)
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=mock_result["message"],
                output=mock_result
            )

        script = RevitScriptBuilder.auto_tag(category)
        result = client.execute_script(script)

        if result.get("success") and "SUCCESS" in result.get("output", ""):
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"Tagged {category} elements",
                output=result
            )
        else:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message=f"Failed to tag {category}",
                error=result.get("error") or result.get("output", "Unknown error")
            )


# =============================================================================
# SKILL: CLASH NAVISWORKS
# =============================================================================

@register_skill
class Skill_ClashNavis(AquaSkill):
    """Export to Navisworks for clash detection."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="Export to Navisworks",
            description="Exports model to NWC format for Navisworks clash detection",
            category=SkillCategory.REVIT,
            icon="AlertTriangle",
            color="#FF4444",
            tags=["revit", "navisworks", "clash", "export", "coordination"],
            requires_revit=True,
            estimated_duration_sec=120
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="export_path",
                label="Export Path",
                type=FieldType.TEXT,
                required=True,
                placeholder="C:\\Exports\\model.nwc",
                description="Full path for NWC export file"
            )
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        export_path = inputs.get("export_path", "C:\\Exports\\model.nwc")

        client = get_routes_client()

        if not client.is_available():
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"[MOCK] Exported to {export_path}",
                output={"export_path": export_path, "mock_mode": True}
            )

        script = RevitScriptBuilder.export_navisworks(export_path)
        result = client.execute_script(script)

        if result.get("success") and "SUCCESS" in result.get("output", ""):
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"Exported to {export_path}",
                output=result
            )
        else:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="Navisworks export failed",
                error=result.get("error") or result.get("output", "Unknown error")
            )


# =============================================================================
# SKILL: DIRECT SCRIPT EXECUTION
# =============================================================================

@register_skill
class Skill_RevitExecute(AquaSkill):
    """Execute arbitrary IronPython script in Revit."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="Execute Revit Script",
            description="Runs custom IronPython code directly in Revit context via Routes API",
            category=SkillCategory.REVIT,
            icon="Terminal",
            color="#9B59B6",
            tags=["revit", "script", "ironpython", "advanced"],
            requires_revit=True
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="script",
                label="IronPython Script",
                type=FieldType.TEXTAREA,
                required=True,
                placeholder='print("Hello from Revit!")',
                description="IronPython code to execute in Revit context"
            )
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        script = inputs.get("script", "")

        if not script.strip():
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="Empty script provided",
                error="Script cannot be empty"
            )

        client = get_routes_client()

        if not client.is_available():
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message="[MOCK] Script execution simulated",
                output={"mock_mode": True, "script_length": len(script)}
            )

        result = client.execute_script(script)

        if result.get("success"):
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message="Script executed successfully",
                output=result
            )
        else:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="Script execution failed",
                error=result.get("error", "Unknown error")
            )


# =============================================================================
# UTILITY: CALL REVIT ROUTE
# =============================================================================

def call_revit_route(route: str, payload: Optional[dict] = None) -> dict:
    """
    Universal function to call any pyRevit route.

    Args:
        route: Route path (e.g., "/v1/execute")
        payload: Optional JSON payload

    Returns:
        Response dictionary
    """
    client = get_routes_client()

    if not client.is_available():
        return {
            "success": False,
            "mock_mode": True,
            "message": "Routes server unavailable - Revit not running or pyRevit not loaded"
        }

    return client.call_route(route, payload)


def revit_execute(script: str) -> dict:
    """
    Convenience function to execute a script in Revit.

    Args:
        script: IronPython script to execute

    Returns:
        Execution result
    """
    client = get_routes_client()
    return client.execute_script(script)


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Client
    "RoutesClient",
    "get_routes_client",
    "get_routes_endpoint",

    # Script Builder
    "RevitScriptBuilder",

    # Mock Data
    "MockRevitData",

    # Skills
    "Skill_OpenProject",
    "Skill_ExtractLOD500",
    "Skill_HydraulicCalc",
    "Skill_GenerateModel",
    "Skill_AutoTag",
    "Skill_ClashNavis",
    "Skill_RevitExecute",

    # Utilities
    "call_revit_route",
    "revit_execute"
]
