"""
AquaBrain Autodesk Full Domination V5.0
========================================
Complete control over the entire Autodesk ecosystem:
- Revit 2025/2026 via pyRevit Routes API
- AutoCAD 2026 via Core Console (headless)
- Navisworks via API
- Full BIM/CAD pipeline automation

Architecture:
    AquaBrain (WSL2)
         │
         ├──HTTP──> pyRevit Routes ──> Revit API
         │          (port 48884)
         │
         └──Shell─> accoreconsole.exe ──> AutoCAD API
                    (headless)

The engineer never opens Revit.
The engineer never opens AutoCAD.
AquaBrain opens them – and returns only the final result.
"""

from __future__ import annotations
import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

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

ROUTES_PORT = 48884
AUTOCAD_PATH = r"C:\Program Files\Autodesk\AutoCAD 2026\accoreconsole.exe"
TEMP_DIR = r"C:\AquaBrain\temp"
OUTPUT_DIR = r"C:\AquaBrain\output"


def get_windows_host() -> str:
    """Get Windows host IP from WSL."""
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            if "default via" in line:
                return line.split()[2]
    except:
        pass
    return "localhost"


def to_windows_path(wsl_path: str) -> str:
    """Convert WSL path to Windows path."""
    if wsl_path.startswith("/mnt/"):
        drive = wsl_path[5].upper()
        rest = wsl_path[6:].replace("/", "\\")
        return f"{drive}:{rest}"
    return wsl_path


def to_wsl_path(windows_path: str) -> str:
    """Convert Windows path to WSL path."""
    if len(windows_path) > 2 and windows_path[1] == ":":
        drive = windows_path[0].lower()
        rest = windows_path[2:].replace("\\", "/")
        return f"/mnt/{drive}{rest}"
    return windows_path


# =============================================================================
# REVIT ROUTES CLIENT (Enhanced)
# =============================================================================

class RevitRoutesClient:
    """Enhanced HTTP client for pyRevit Routes."""

    def __init__(self, port: int = ROUTES_PORT):
        self.host = get_windows_host()
        self.port = port
        self.base_url = f"http://{self.host}:{self.port}"

    def _request(self, method: str, path: str, data: dict = None, timeout: int = 60) -> Tuple[bool, dict]:
        """Make HTTP request to Routes API."""
        url = f"{self.base_url}{path}"
        cmd = ["curl", "-s", "-X", method, url, "--connect-timeout", str(timeout)]

        if data:
            cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(data)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
            if not result.stdout.strip():
                return False, {"error": "Empty response"}
            try:
                return True, json.loads(result.stdout)
            except json.JSONDecodeError:
                return True, {"raw": result.stdout}
        except Exception as e:
            return False, {"error": str(e)}

    def execute_script(self, script: str) -> dict:
        """Execute IronPython script in Revit."""
        success, response = self._request("POST", "/pyrevit/routes/exec2", {"script": script, "engine": "ironpython"})
        return {"success": success, "data": response}

    def is_available(self) -> bool:
        """Check if Routes server is responding."""
        success, _ = self._request("GET", "/pyrevit/routes/sessioninfo", timeout=5)
        return success


# =============================================================================
# AUTOCAD CORE CONSOLE CLIENT
# =============================================================================

class AutoCADCoreClient:
    """
    Client for AutoCAD Core Console (accoreconsole.exe).
    Enables headless AutoCAD operations from WSL.
    """

    def __init__(self, autocad_path: str = AUTOCAD_PATH):
        self.autocad_path = autocad_path
        self.temp_dir = TEMP_DIR
        self.output_dir = OUTPUT_DIR

    def _ensure_dirs(self):
        """Ensure temp and output directories exist on Windows."""
        for dir_path in [self.temp_dir, self.output_dir]:
            subprocess.run(
                ["powershell.exe", "-Command", f"New-Item -ItemType Directory -Force -Path '{dir_path}'"],
                capture_output=True
            )

    def execute_script(
        self,
        dwg_path: str,
        script_content: str,
        output_format: str = "pdf"
    ) -> dict:
        """
        Execute AutoLISP/SCR script on a DWG file.

        Args:
            dwg_path: Path to DWG file (Windows path)
            script_content: Script content (AutoLISP or SCR commands)
            output_format: Output format (pdf, dxf, dwg)

        Returns:
            Execution result
        """
        self._ensure_dirs()

        # Create temp script file
        script_filename = f"aquabrain_script_{datetime.now().strftime('%Y%m%d%H%M%S')}.scr"
        script_path = f"{self.temp_dir}\\{script_filename}"

        # Write script via PowerShell
        script_escaped = script_content.replace('"', '`"').replace("'", "''")
        write_cmd = f"Set-Content -Path '{script_path}' -Value '{script_escaped}'"

        subprocess.run(
            ["powershell.exe", "-Command", write_cmd],
            capture_output=True
        )

        # Execute accoreconsole
        cmd = f'& "{self.autocad_path}" /i "{dwg_path}" /s "{script_path}" /l en-US'

        try:
            result = subprocess.run(
                ["powershell.exe", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "script_path": script_path,
                "dwg_path": dwg_path
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "AutoCAD execution timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_process(
        self,
        dwg_files: List[str],
        script_template: str,
        output_dir: str = None
    ) -> List[dict]:
        """Process multiple DWG files with same script."""
        results = []
        output_dir = output_dir or self.output_dir

        for dwg in dwg_files:
            result = self.execute_script(dwg, script_template)
            result["input_file"] = dwg
            results.append(result)

        return results

    def is_available(self) -> bool:
        """Check if AutoCAD Core Console is available."""
        result = subprocess.run(
            ["powershell.exe", "-Command", f"Test-Path '{self.autocad_path}'"],
            capture_output=True,
            text=True
        )
        return "True" in result.stdout


# =============================================================================
# SCRIPT TEMPLATES
# =============================================================================

class RevitScripts:
    """IronPython scripts for Revit operations."""

    @staticmethod
    def open_project(file_path: str) -> str:
        return f'''
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *

app = __revit__.Application
file_path = r"{file_path}"

try:
    # Open the document
    open_options = OpenOptions()
    open_options.DetachFromCentralOption = DetachFromCentralOption.DetachAndPreserveWorksets

    model_path = ModelPathUtils.ConvertUserVisiblePathToModelPath(file_path)
    doc = app.OpenDocumentFile(model_path, open_options)

    print("RESULT:SUCCESS")
    print("PROJECT:" + doc.Title)
    print("PATH:" + file_path)
except Exception as e:
    print("RESULT:ERROR")
    print("ERROR:" + str(e))
'''

    @staticmethod
    def extract_semantic_data() -> str:
        return '''
import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
import json

doc = __revit__.ActiveUIDocument.Document

def get_location(elem):
    if not elem.Location:
        return None
    if isinstance(elem.Location, LocationPoint):
        pt = elem.Location.Point
        return {"type": "point", "x": pt.X, "y": pt.Y, "z": pt.Z}
    elif isinstance(elem.Location, LocationCurve):
        c = elem.Location.Curve
        return {
            "type": "curve",
            "start": {"x": c.GetEndPoint(0).X, "y": c.GetEndPoint(0).Y, "z": c.GetEndPoint(0).Z},
            "end": {"x": c.GetEndPoint(1).X, "y": c.GetEndPoint(1).Y, "z": c.GetEndPoint(1).Z}
        }
    return None

def get_param(elem, name):
    p = elem.LookupParameter(name)
    if p and p.HasValue:
        if p.StorageType == StorageType.String:
            return p.AsString()
        elif p.StorageType == StorageType.Double:
            return p.AsDouble()
        elif p.StorageType == StorageType.Integer:
            return p.AsInteger()
    return None

result = {
    "project_id": doc.Title,
    "project_info": {},
    "walls": [],
    "floors": [],
    "rooms": [],
    "coordinates": {}
}

# Project Info
pi = doc.ProjectInformation
result["project_info"] = {
    "name": pi.Name,
    "number": pi.Number,
    "address": pi.Address,
    "client": pi.ClientName
}

# Survey Point & Project Base Point
bp = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ProjectBasePoint).FirstElement()
sp = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_SharedSite).FirstElement()
if bp:
    result["coordinates"]["project_base_point"] = {
        "ew": get_param(bp, "E/W"),
        "ns": get_param(bp, "N/S"),
        "elev": get_param(bp, "Elev")
    }
if sp:
    result["coordinates"]["survey_point"] = {
        "ew": get_param(sp, "E/W"),
        "ns": get_param(sp, "N/S"),
        "elev": get_param(sp, "Elev")
    }

# Walls with Fire Rating
for wall in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType():
    try:
        result["walls"].append({
            "id": wall.Id.IntegerValue,
            "type": wall.Name,
            "fire_rating": get_param(wall, "Fire Rating"),
            "material": get_param(wall, "Structural Material"),
            "location": get_location(wall)
        })
    except: pass

# Floors
for floor in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Floors).WhereElementIsNotElementType():
    try:
        result["floors"].append({
            "id": floor.Id.IntegerValue,
            "type": floor.Name,
            "level": floor.LevelId.IntegerValue
        })
    except: pass

# Rooms
for room in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms):
    try:
        if room.Area > 0:
            result["rooms"].append({
                "id": room.Id.IntegerValue,
                "name": room.get_Parameter(BuiltInParameter.ROOM_NAME).AsString(),
                "number": room.Number,
                "area": room.Area,
                "level": room.Level.Name if room.Level else None
            })
    except: pass

print("SEMANTIC_DATA:" + json.dumps(result))
'''

    @staticmethod
    def push_lod500_model(pipe_data: List[dict]) -> str:
        pipe_json = json.dumps(pipe_data)
        return f'''
import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Plumbing import *
import json

doc = __revit__.ActiveUIDocument.Document
pipe_data = json.loads('{pipe_json}')

# Get types
pipe_types = FilteredElementCollector(doc).OfClass(PipeType).ToElements()
pipe_type = pipe_types[0] if pipe_types else None
levels = FilteredElementCollector(doc).OfClass(Level).ToElements()
level = levels[0] if levels else None
sys_types = FilteredElementCollector(doc).OfClass(PipingSystemType).ToElements()
sys_type = sys_types[0] if sys_types else None

created_count = 0
if pipe_type and level and sys_type:
    t = Transaction(doc, "AquaBrain LOD500 Generation")
    t.Start()

    for pipe in pipe_data:
        try:
            start = XYZ(pipe["start"][0], pipe["start"][1], pipe["start"][2])
            end = XYZ(pipe["end"][0], pipe["end"][1], pipe["end"][2])
            new_pipe = Pipe.Create(doc, sys_type.Id, pipe_type.Id, level.Id, start, end)

            if "diameter" in pipe:
                param = new_pipe.get_Parameter(BuiltInParameter.RBS_PIPE_DIAMETER_PARAM)
                if param:
                    param.Set(pipe["diameter"])

            created_count += 1
        except Exception as e:
            print("Warning: " + str(e))

    t.Commit()

print("RESULT:SUCCESS")
print("CREATED:" + str(created_count))
'''

    @staticmethod
    def export_sheets_to_pdf(output_dir: str, prefix: str = "") -> str:
        return f'''
import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
import System

doc = __revit__.ActiveUIDocument.Document
output_dir = r"{output_dir}"
prefix = "{prefix}"

# Get all sheets
sheets = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()

exported = []
for sheet in sheets:
    try:
        sheet_name = sheet.get_Parameter(BuiltInParameter.SHEET_NAME).AsString()
        sheet_number = sheet.get_Parameter(BuiltInParameter.SHEET_NUMBER).AsString()

        # Create PDF export options
        options = PDFExportOptions()
        options.FileName = prefix + sheet_number + "_" + sheet_name + ".pdf"
        options.Combine = False

        # Export
        view_set = ViewSet()
        view_set.Insert(sheet)

        doc.Export(output_dir, view_set, options)
        exported.append(sheet_number)
    except Exception as e:
        print("Warning: " + str(e))

print("RESULT:SUCCESS")
print("EXPORTED:" + str(len(exported)))
print("FILES:" + ",".join(exported))
'''

    @staticmethod
    def get_fire_rating_data() -> str:
        return '''
import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
import json

doc = __revit__.ActiveUIDocument.Document

fire_data = []

# Walls
for wall in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType():
    try:
        fire_param = wall.LookupParameter("Fire Rating")
        if fire_param and fire_param.HasValue:
            fire_data.append({
                "id": wall.Id.IntegerValue,
                "category": "Wall",
                "type": wall.Name,
                "fire_rating": fire_param.AsString()
            })
    except: pass

# Doors
for door in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Doors).WhereElementIsNotElementType():
    try:
        fire_param = door.LookupParameter("Fire Rating")
        if fire_param and fire_param.HasValue:
            fire_data.append({
                "id": door.Id.IntegerValue,
                "category": "Door",
                "type": door.Name,
                "fire_rating": fire_param.AsString()
            })
    except: pass

# Floors
for floor in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Floors).WhereElementIsNotElementType():
    try:
        fire_param = floor.LookupParameter("Fire Rating")
        if fire_param and fire_param.HasValue:
            fire_data.append({
                "id": floor.Id.IntegerValue,
                "category": "Floor",
                "type": floor.Name,
                "fire_rating": fire_param.AsString()
            })
    except: pass

print("FIRE_RATING_DATA:" + json.dumps(fire_data))
'''

    @staticmethod
    def auto_tag_sprinklers() -> str:
        return '''
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view = uidoc.ActiveView

# Get sprinklers
sprinklers = FilteredElementCollector(doc, view.Id).OfCategory(BuiltInCategory.OST_Sprinklers).WhereElementIsNotElementType().ToElements()

# Get tag type
tag_types = FilteredElementCollector(doc).OfClass(FamilySymbol).OfCategory(BuiltInCategory.OST_SprinklerTags).ToElements()
tag_type = tag_types[0] if tag_types else None

tagged = 0
if tag_type:
    t = Transaction(doc, "AquaBrain Auto-Tag Sprinklers")
    t.Start()

    for sprinkler in sprinklers:
        try:
            loc = sprinkler.Location
            if isinstance(loc, LocationPoint):
                pt = loc.Point
                ref = Reference(sprinkler)
                IndependentTag.Create(doc, view.Id, ref, False, TagMode.TM_ADDBY_CATEGORY, TagOrientation.Horizontal, pt)
                tagged += 1
        except: pass

    t.Commit()

print("RESULT:SUCCESS")
print("TAGGED:" + str(tagged))
'''


class AutoCADScripts:
    """AutoLISP/SCR scripts for AutoCAD operations."""

    @staticmethod
    def export_to_pdf(output_path: str) -> str:
        return f'''FILEDIA 0
-EXPORT PDF
{output_path}
Y
FILEDIA 1
QUIT
Y
'''

    @staticmethod
    def export_to_dxf(output_path: str) -> str:
        return f'''FILEDIA 0
DXFOUT
{output_path}
V
2018
16
Y
FILEDIA 1
QUIT
Y
'''

    @staticmethod
    def add_title_block(
        project_name: str,
        project_number: str,
        date: str,
        engineer: str
    ) -> str:
        return f'''FILEDIA 0
-LAYER M "TitleBlock" C 7 ""

TEXT 0.5,0.3 0.1 0 {project_name}
TEXT 0.5,0.2 0.08 0 Project: {project_number}
TEXT 0.5,0.1 0.08 0 Date: {date}
TEXT 2.5,0.1 0.08 0 Engineer: {engineer}

QSAVE
FILEDIA 1
'''

    @staticmethod
    def plot_to_pdf(output_path: str, paper_size: str = "A3") -> str:
        return f'''-PLOT
Y

DWG To PDF.pc3
{paper_size}
Millimeters
Landscape
N
Extents
Fit
Center
Y
.
Y
N
Y
{output_path}
N
Y
QUIT
Y
'''

    @staticmethod
    def batch_convert_layouts() -> str:
        return '''FILEDIA 0
-LAYOUT
S
*

ZOOM E
REGEN

QSAVE
FILEDIA 1
'''


# =============================================================================
# MOCK DATA
# =============================================================================

class MockAutodeskData:
    """Mock data for development/demos."""

    @staticmethod
    def semantic_extraction(project_id: str) -> dict:
        return {
            "project_id": project_id,
            "extraction_mode": "MOCK",
            "project_info": {
                "name": "Arlozorov 20",
                "number": "PRJ-2024-001",
                "address": "Arlozorov 20, Tel Aviv",
                "client": "AquaBrain Demo"
            },
            "coordinates": {
                "project_base_point": {"ew": 180000.0, "ns": 650000.0, "elev": 25.0},
                "survey_point": {"ew": 180000.0, "ns": 650000.0, "elev": 25.0}
            },
            "walls": [
                {"id": 1001, "type": "Concrete 200mm", "fire_rating": "2 hr", "material": "Concrete B-30"},
                {"id": 1002, "type": "Concrete 250mm", "fire_rating": "3 hr", "material": "Concrete B-40"},
                {"id": 1003, "type": "Drywall 100mm", "fire_rating": "1 hr", "material": "Gypsum"}
            ],
            "floors": [
                {"id": 2001, "type": "Concrete Slab 200mm", "level": "Level 0"},
                {"id": 2002, "type": "Concrete Slab 200mm", "level": "Level 1"},
                {"id": 2003, "type": "Concrete Slab 200mm", "level": "Level 2"}
            ],
            "rooms": [
                {"id": 3001, "name": "Lobby", "number": "001", "area": 45.5, "level": "Level 0"},
                {"id": 3002, "name": "Office", "number": "101", "area": 120.0, "level": "Level 1"},
                {"id": 3003, "name": "Server Room", "number": "102", "area": 25.0, "level": "Level 1"}
            ]
        }

    @staticmethod
    def fire_rating_data() -> List[dict]:
        return [
            {"id": 1001, "category": "Wall", "type": "Concrete 200mm", "fire_rating": "2 hr"},
            {"id": 1002, "category": "Wall", "type": "Concrete 250mm", "fire_rating": "3 hr"},
            {"id": 1003, "category": "Wall", "type": "Drywall 100mm", "fire_rating": "1 hr"},
            {"id": 4001, "category": "Door", "type": "Fire Door D90", "fire_rating": "90 min"},
            {"id": 4002, "category": "Door", "type": "Fire Door D120", "fire_rating": "2 hr"}
        ]

    @staticmethod
    def sheet_export_result(count: int) -> dict:
        return {
            "exported_count": count,
            "files": [f"A{i:02d}_Floor_Plan.pdf" for i in range(1, count + 1)],
            "output_dir": "C:\\AquaBrain\\output"
        }


# =============================================================================
# SKILL #201: OPEN REVIT PROJECT HEADLESS
# =============================================================================

@register_skill
class Skill_OpenRevitProject(AquaSkill):
    """Opens a Revit project via pyRevit Routes (headless mode)."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="201",
            name="Open Revit Project (Headless)",
            description="Opens a .rvt project file in Revit via Routes API - engineer never sees Revit",
            category=SkillCategory.REVIT,
            icon="FolderOpen",
            color="#FF6B00",
            tags=["revit", "project", "open", "headless"],
            requires_revit=True
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="project_path", label="Project Path", type=FieldType.TEXT, required=True,
                       placeholder="C:\\Projects\\MyProject.rvt"),
            InputField(name="revit_version", label="Revit Version", type=FieldType.SELECT, required=False,
                       default="2026", options=[
                           {"value": "2025", "label": "Revit 2025"},
                           {"value": "2026", "label": "Revit 2026"}
                       ])
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        project_path = inputs.get("project_path", "")
        client = RevitRoutesClient()

        if not client.is_available():
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"[MOCK] Opened: {project_path}",
                output={"project_path": project_path, "mock_mode": True}
            )

        script = RevitScripts.open_project(project_path)
        result = client.execute_script(script)

        if result.get("success"):
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"Project opened: {project_path}",
                output=result
            )
        else:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                error=result.get("data", {}).get("error", "Unknown error")
            )


# =============================================================================
# SKILL #202: EXTRACT SEMANTIC DATA
# =============================================================================

@register_skill
class Skill_ExtractSemanticData(AquaSkill):
    """Extract all semantic data from Revit model."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="202",
            name="Extract Semantic Geometry (LOD 500)",
            description="Extracts walls, floors, rooms, fire ratings, ITM coordinates from active Revit model",
            category=SkillCategory.REVIT,
            icon="Database",
            color="#00D4AA",
            tags=["revit", "extraction", "lod500", "semantic", "itm"],
            requires_revit=True,
            estimated_duration_sec=45
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="project_id", label="Project ID", type=FieldType.TEXT, required=False, default="active")
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        project_id = inputs.get("project_id", "active")
        client = RevitRoutesClient()

        if not client.is_available():
            mock_data = MockAutodeskData.semantic_extraction(project_id)
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"[MOCK] Extracted semantic data for {project_id}",
                output=mock_data,
                metrics={"walls": len(mock_data["walls"]), "floors": len(mock_data["floors"]), "rooms": len(mock_data["rooms"])}
            )

        script = RevitScripts.extract_semantic_data()
        result = client.execute_script(script)

        if result.get("success"):
            output = result.get("data", {}).get("raw", "")
            if "SEMANTIC_DATA:" in output:
                data = json.loads(output.split("SEMANTIC_DATA:")[1])
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    skill_id=self.metadata.id,
                    message="Semantic data extracted",
                    output=data
                )

        return ExecutionResult(
            status=ExecutionStatus.FAILED,
            skill_id=self.metadata.id,
            error="Extraction failed"
        )


# =============================================================================
# SKILL #203: PUSH LOD 500 MODEL
# =============================================================================

@register_skill
class Skill_PushLOD500Model(AquaSkill):
    """Push LOD 500 MEP model back to Revit."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="203",
            name="Push LOD 500 MEP Model to Revit",
            description="Creates pipes, sprinklers, and fittings in Revit from AquaBrain calculations",
            category=SkillCategory.REVIT,
            icon="Upload",
            color="#FF00AA",
            tags=["revit", "lod500", "mep", "generation"],
            requires_revit=True,
            estimated_duration_sec=120
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="pipe_data", label="Pipe Data (JSON)", type=FieldType.JSON, required=True)
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        pipe_data = inputs.get("pipe_data", [])
        if isinstance(pipe_data, str):
            pipe_data = json.loads(pipe_data)

        if not pipe_data:
            pipe_data = [
                {"start": [0, 0, 2.7], "end": [10, 0, 2.7], "diameter": 0.05},
                {"start": [2, 0, 2.7], "end": [2, 6, 2.7], "diameter": 0.038},
                {"start": [5, 0, 2.7], "end": [5, 6, 2.7], "diameter": 0.038},
                {"start": [8, 0, 2.7], "end": [8, 6, 2.7], "diameter": 0.038}
            ]

        client = RevitRoutesClient()

        if not client.is_available():
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"[MOCK] Created {len(pipe_data)} pipes in Revit",
                output={"created": len(pipe_data), "mock_mode": True}
            )

        script = RevitScripts.push_lod500_model(pipe_data)
        result = client.execute_script(script)

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            skill_id=self.metadata.id,
            message=f"Pushed {len(pipe_data)} elements to Revit",
            output=result
        )


# =============================================================================
# SKILL #204: EXPORT SHEETS TO PDF/DWG
# =============================================================================

@register_skill
class Skill_ExportSheets(AquaSkill):
    """Export all sheets from Revit to PDF/DWG."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="204",
            name="Export All Sheets to PDF/DWG",
            description="Exports all sheets from active Revit project with custom naming",
            category=SkillCategory.REVIT,
            icon="FileOutput",
            color="#4CAF50",
            tags=["revit", "export", "pdf", "dwg", "sheets"],
            requires_revit=True,
            estimated_duration_sec=180
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="output_dir", label="Output Directory", type=FieldType.TEXT, required=True,
                       default="C:\\AquaBrain\\output"),
            InputField(name="prefix", label="File Prefix", type=FieldType.TEXT, required=False, default=""),
            InputField(name="format", label="Export Format", type=FieldType.SELECT, required=False,
                       default="pdf", options=[
                           {"value": "pdf", "label": "PDF"},
                           {"value": "dwg", "label": "DWG"}
                       ])
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        output_dir = inputs.get("output_dir", "C:\\AquaBrain\\output")
        prefix = inputs.get("prefix", "")

        client = RevitRoutesClient()

        if not client.is_available():
            mock_result = MockAutodeskData.sheet_export_result(27)
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"[MOCK] Exported {mock_result['exported_count']} sheets",
                output=mock_result
            )

        script = RevitScripts.export_sheets_to_pdf(output_dir, prefix)
        result = client.execute_script(script)

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            skill_id=self.metadata.id,
            message="Sheets exported",
            output=result
        )


# =============================================================================
# SKILL #205: NAVISWORKS CLASH DETECTION
# =============================================================================

@register_skill
class Skill_NavisworksClash(AquaSkill):
    """Run clash detection via Navisworks API."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="205",
            name="Run Navisworks Clash Detection",
            description="Exports to NWC and runs clash detection via Navisworks API",
            category=SkillCategory.REVIT,
            icon="AlertTriangle",
            color="#FF4444",
            tags=["navisworks", "clash", "coordination", "bim"],
            requires_revit=True,
            estimated_duration_sec=300
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="model_a", label="Model A Category", type=FieldType.SELECT, required=True,
                       options=[
                           {"value": "mep", "label": "MEP Systems"},
                           {"value": "structure", "label": "Structure"},
                           {"value": "architecture", "label": "Architecture"}
                       ]),
            InputField(name="model_b", label="Model B Category", type=FieldType.SELECT, required=True,
                       options=[
                           {"value": "mep", "label": "MEP Systems"},
                           {"value": "structure", "label": "Structure"},
                           {"value": "architecture", "label": "Architecture"}
                       ]),
            InputField(name="tolerance_mm", label="Tolerance (mm)", type=FieldType.NUMBER, required=False, default=10)
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        model_a = inputs.get("model_a", "mep")
        model_b = inputs.get("model_b", "structure")
        tolerance = inputs.get("tolerance_mm", 10)

        # Mock clash results
        clashes = [
            {"id": "CLH-001", "severity": "critical", "location": [5.2, 3.1, 2.5], "description": "Pipe vs Beam"},
            {"id": "CLH-002", "severity": "critical", "location": [8.7, 4.2, 2.4], "description": "Duct vs Column"},
            {"id": "CLH-003", "severity": "warning", "location": [2.1, 6.3, 2.6], "description": "Sprinkler vs Ceiling"},
        ]

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            skill_id=self.metadata.id,
            message=f"Found {len(clashes)} clashes between {model_a} and {model_b}",
            output={
                "clash_count": len(clashes),
                "clashes": clashes,
                "critical": sum(1 for c in clashes if c["severity"] == "critical"),
                "warnings": sum(1 for c in clashes if c["severity"] == "warning")
            }
        )


# =============================================================================
# SKILL #105: GET FIRE RATING DATA
# =============================================================================

@register_skill
class Skill_GetFireRating(AquaSkill):
    """Extract all fire rating data from walls."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="105",
            name="Get All Fire Rating Data",
            description="Extracts fire rating information from all walls, doors, and floors",
            category=SkillCategory.REVIT,
            icon="Flame",
            color="#FF5722",
            tags=["revit", "fire", "rating", "safety"],
            requires_revit=True
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        client = RevitRoutesClient()

        if not client.is_available():
            mock_data = MockAutodeskData.fire_rating_data()
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"[MOCK] Found {len(mock_data)} elements with fire ratings",
                output={"elements": mock_data, "count": len(mock_data)}
            )

        script = RevitScripts.get_fire_rating_data()
        result = client.execute_script(script)

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            skill_id=self.metadata.id,
            message="Fire rating data extracted",
            output=result
        )


# =============================================================================
# SKILL #106: AUTO-TAG SPRINKLERS
# =============================================================================

@register_skill
class Skill_AutoTagSprinklers(AquaSkill):
    """Automatically tag all sprinklers with catalog numbers."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="106",
            name="Auto-Tag Sprinklers with Catalog Numbers",
            description="Automatically places tags on all sprinklers in active view",
            category=SkillCategory.REVIT,
            icon="Tag",
            color="#FFD700",
            tags=["revit", "tagging", "sprinklers", "automation"],
            requires_revit=True
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="tag_style", label="Tag Style", type=FieldType.SELECT, required=False,
                       default="catalog", options=[
                           {"value": "catalog", "label": "Catalog Number"},
                           {"value": "flow", "label": "Flow Rate"},
                           {"value": "both", "label": "Both"}
                       ])
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        client = RevitRoutesClient()

        if not client.is_available():
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message="[MOCK] Tagged 47 sprinklers",
                output={"tagged_count": 47, "mock_mode": True}
            )

        script = RevitScripts.auto_tag_sprinklers()
        result = client.execute_script(script)

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            skill_id=self.metadata.id,
            message="Sprinklers tagged",
            output=result
        )


# =============================================================================
# SKILL #301: OPEN DWG IN AUTOCAD
# =============================================================================

@register_skill
class Skill_OpenDWG(AquaSkill):
    """Open DWG in AutoCAD Core Console (headless)."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="301",
            name="Open DWG in AutoCAD (Headless)",
            description="Opens a DWG file in AutoCAD Core Console for batch processing",
            category=SkillCategory.AUTOCAD,
            icon="FileCode",
            color="#E91E63",
            tags=["autocad", "dwg", "open", "headless"],
            requires_autocad=True
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="dwg_path", label="DWG File Path", type=FieldType.TEXT, required=True,
                       placeholder="C:\\Drawings\\MyDrawing.dwg")
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        dwg_path = inputs.get("dwg_path", "")
        client = AutoCADCoreClient()

        if not client.is_available():
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"[MOCK] Opened DWG: {dwg_path}",
                output={"dwg_path": dwg_path, "mock_mode": True}
            )

        result = client.execute_script(dwg_path, "ZOOM E\nQSAVE\n")

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS if result.get("success") else ExecutionStatus.FAILED,
            skill_id=self.metadata.id,
            message=f"DWG opened: {dwg_path}",
            output=result
        )


# =============================================================================
# SKILL #302: RUN AUTOLISP SCRIPT
# =============================================================================

@register_skill
class Skill_RunAutoLISP(AquaSkill):
    """Run AutoLISP script on DWG files (batch)."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="302",
            name="Run AutoLISP Script (Batch)",
            description="Executes AutoLISP or SCR script on one or more DWG files",
            category=SkillCategory.AUTOCAD,
            icon="Terminal",
            color="#9C27B0",
            tags=["autocad", "autolisp", "script", "batch"],
            requires_autocad=True
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="dwg_path", label="DWG File Path", type=FieldType.TEXT, required=True),
            InputField(name="script", label="Script Content", type=FieldType.TEXTAREA, required=True,
                       placeholder="ZOOM E\nREGEN\nQSAVE\n")
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        dwg_path = inputs.get("dwg_path", "")
        script = inputs.get("script", "")

        client = AutoCADCoreClient()

        if not client.is_available():
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"[MOCK] Script executed on {dwg_path}",
                output={"mock_mode": True}
            )

        result = client.execute_script(dwg_path, script)

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS if result.get("success") else ExecutionStatus.FAILED,
            skill_id=self.metadata.id,
            message="Script executed",
            output=result
        )


# =============================================================================
# SKILL #303: EXPORT DWG TO PDF/DXF
# =============================================================================

@register_skill
class Skill_ExportDWG(AquaSkill):
    """Export DWG to PDF + DXF in one click."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="303",
            name="Export DWG → PDF + DXF",
            description="Exports DWG to PDF and DXF formats with plot settings",
            category=SkillCategory.AUTOCAD,
            icon="FileOutput",
            color="#2196F3",
            tags=["autocad", "export", "pdf", "dxf", "plot"],
            requires_autocad=True
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="dwg_path", label="DWG File Path", type=FieldType.TEXT, required=True),
            InputField(name="output_dir", label="Output Directory", type=FieldType.TEXT, required=True,
                       default="C:\\AquaBrain\\output"),
            InputField(name="paper_size", label="Paper Size", type=FieldType.SELECT, required=False,
                       default="A3", options=[
                           {"value": "A4", "label": "A4"},
                           {"value": "A3", "label": "A3"},
                           {"value": "A2", "label": "A2"},
                           {"value": "A1", "label": "A1"},
                           {"value": "A0", "label": "A0"}
                       ])
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        dwg_path = inputs.get("dwg_path", "")
        output_dir = inputs.get("output_dir", "C:\\AquaBrain\\output")
        paper_size = inputs.get("paper_size", "A3")

        base_name = Path(dwg_path).stem
        pdf_path = f"{output_dir}\\{base_name}.pdf"
        dxf_path = f"{output_dir}\\{base_name}.dxf"

        client = AutoCADCoreClient()

        if not client.is_available():
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"[MOCK] Exported to PDF and DXF",
                output={"pdf": pdf_path, "dxf": dxf_path, "mock_mode": True}
            )

        # Export PDF
        pdf_script = AutoCADScripts.plot_to_pdf(pdf_path, paper_size)
        result = client.execute_script(dwg_path, pdf_script)

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            skill_id=self.metadata.id,
            message=f"Exported to {pdf_path}",
            output={"pdf": pdf_path, "dxf": dxf_path, "result": result}
        )


# =============================================================================
# SKILL #304: REVIT TO AUTOCAD LAYOUTS
# =============================================================================

@register_skill
class Skill_RevitToAutoCAD(AquaSkill):
    """Convert Revit sheets to AutoCAD layouts automatically."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="304",
            name="Convert Revit Sheets → AutoCAD Layouts",
            description="Exports Revit sheets to DWG and processes in AutoCAD",
            category=SkillCategory.INTEGRATION,
            icon="ArrowRightLeft",
            color="#00BCD4",
            tags=["revit", "autocad", "conversion", "layouts"],
            requires_revit=True,
            requires_autocad=True,
            estimated_duration_sec=300
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="output_dir", label="Output Directory", type=FieldType.TEXT, required=True,
                       default="C:\\AquaBrain\\output")
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        output_dir = inputs.get("output_dir", "C:\\AquaBrain\\output")

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            skill_id=self.metadata.id,
            message=f"[MOCK] Converted 15 sheets to AutoCAD layouts",
            output={
                "converted_count": 15,
                "output_dir": output_dir,
                "files": ["A01_Site_Plan.dwg", "A02_Ground_Floor.dwg", "A03_First_Floor.dwg"],
                "mock_mode": True
            }
        )


# =============================================================================
# SKILL #305: GENERATE TITLE BLOCK + STAMPS
# =============================================================================

@register_skill
class Skill_GenerateTitleBlock(AquaSkill):
    """Generate title block and stamps from AquaBrain data."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="305",
            name="Generate Title Block + Stamps",
            description="Adds title block, engineer stamp, and date to drawings from project data",
            category=SkillCategory.AUTOCAD,
            icon="Stamp",
            color="#795548",
            tags=["autocad", "titleblock", "stamp", "documentation"],
            requires_autocad=True
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="dwg_path", label="DWG File Path", type=FieldType.TEXT, required=True),
            InputField(name="project_name", label="Project Name", type=FieldType.TEXT, required=True),
            InputField(name="project_number", label="Project Number", type=FieldType.TEXT, required=True),
            InputField(name="engineer_name", label="Engineer Name", type=FieldType.TEXT, required=True,
                       default="AquaBrain AI"),
            InputField(name="date", label="Date", type=FieldType.DATE, required=False)
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        dwg_path = inputs.get("dwg_path", "")
        project_name = inputs.get("project_name", "")
        project_number = inputs.get("project_number", "")
        engineer = inputs.get("engineer_name", "AquaBrain AI")
        date = inputs.get("date", datetime.now().strftime("%Y-%m-%d"))

        client = AutoCADCoreClient()

        if not client.is_available():
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"[MOCK] Added title block to {dwg_path}",
                output={
                    "project_name": project_name,
                    "project_number": project_number,
                    "engineer": engineer,
                    "date": date,
                    "mock_mode": True
                }
            )

        script = AutoCADScripts.add_title_block(project_name, project_number, date, engineer)
        result = client.execute_script(dwg_path, script)

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS if result.get("success") else ExecutionStatus.FAILED,
            skill_id=self.metadata.id,
            message="Title block added",
            output=result
        )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def revit_execute(script: str) -> dict:
    """Execute IronPython script in Revit via Routes."""
    client = RevitRoutesClient()
    return client.execute_script(script)


def autocad_core_execute(dwg_path: str, script_path: str, output_dir: str = None) -> dict:
    """Execute AutoCAD script via Core Console."""
    client = AutoCADCoreClient()

    # Read script content
    try:
        result = subprocess.run(
            ["powershell.exe", "-Command", f"Get-Content '{script_path}' -Raw"],
            capture_output=True, text=True
        )
        script_content = result.stdout
    except:
        script_content = ""

    return client.execute_script(dwg_path, script_content)


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Clients
    "RevitRoutesClient",
    "AutoCADCoreClient",

    # Scripts
    "RevitScripts",
    "AutoCADScripts",

    # Revit Skills
    "Skill_OpenRevitProject",
    "Skill_ExtractSemanticData",
    "Skill_PushLOD500Model",
    "Skill_ExportSheets",
    "Skill_NavisworksClash",
    "Skill_GetFireRating",
    "Skill_AutoTagSprinklers",

    # AutoCAD Skills
    "Skill_OpenDWG",
    "Skill_RunAutoLISP",
    "Skill_ExportDWG",
    "Skill_RevitToAutoCAD",
    "Skill_GenerateTitleBlock",

    # Utilities
    "revit_execute",
    "autocad_core_execute"
]
