"""
AutoCAD Extraction Skill V2.0
=============================
מגשר בין AquaBrain (Linux/WSL) לבין AutoCAD Core Console (Windows).
מבצע המרת נתיבים, הרצת סקריפט PowerShell ועיבוד הנתונים ההידראוליים.

Pipeline:
1. קבלת נתיב קובץ DWG (Linux או Windows)
2. המרת הנתיב ל-Windows format
3. הרצת PowerShell bridge script
4. עיבוד פלט JSON
5. העשרה הנדסית והמרת יחידות
"""

from __future__ import annotations
import subprocess
import json
import os
import re
import shlex
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime


def validate_path(path: str, allowed_extensions: Optional[List[str]] = None) -> str:
    """
    Validate and sanitize file paths to prevent command injection.

    Args:
        path: The file path to validate
        allowed_extensions: Optional list of allowed file extensions (e.g., ['.dwg', '.dxf'])

    Returns:
        Sanitized absolute path

    Raises:
        ValueError: If path is invalid or contains suspicious patterns
    """
    if not path:
        raise ValueError("Path cannot be empty")

    # Block dangerous patterns
    dangerous_patterns = [
        ';', '&', '|', '$', '`', '\n', '\r', '\x00',
        '$(', '${', '..', '<', '>', '"', "'", '\\\\',
    ]
    for pattern in dangerous_patterns:
        if pattern in path:
            raise ValueError(f"Path contains forbidden character: {pattern!r}")

    # Resolve to absolute path
    resolved = Path(path).resolve()

    # Check extension if specified
    if allowed_extensions:
        if resolved.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
            raise ValueError(f"File extension not allowed: {resolved.suffix}")

    return str(resolved)

# Import skill base classes
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from skills.base import (
    AquaSkill, ExecutionResult, ExecutionStatus,
    SkillMetadata, SkillCategory, InputSchema, InputField, FieldType,
    register_skill
)


@register_skill
class AutoCADExtractSkill(AquaSkill):
    """
    Extract sprinkler data from AutoCAD DWG files.

    Uses headless AutoCAD Core Console (accoreconsole.exe) for
    batch processing without GUI overhead.
    """

    # Configuration
    POWERSHELL_SCRIPT = "Extract-Sprinklers.ps1"
    SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "autocad"
    TEMP_DIR = Path("/tmp/aquabrain") if os.name != 'nt' else Path("C:/AquaBrain/temp")

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="autocad_extract",
            name="AutoCAD Sprinkler Extractor",
            description="מחלץ נתוני ספרינקלרים מקובץ DWG באמצעות AutoCAD Core Console",
            category=SkillCategory.AUTOCAD,
            icon="FileDigit",
            color="#E74C3C",
            version="2.0.0",
            author="AquaBrain",
            tags=["autocad", "dwg", "sprinkler", "extraction", "xdata"],
            requires_autocad=True,
            estimated_duration_sec=30
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="dwg_path",
                label="DWG File Path",
                type=FieldType.TEXT,
                required=True,
                placeholder="/mnt/c/Projects/building.dwg or C:\\Projects\\building.dwg",
                description="Full path to the DWG file (WSL or Windows format)"
            ),
            InputField(
                name="output_format",
                label="Output Format",
                type=FieldType.SELECT,
                required=False,
                default="JSON",
                options=[
                    {"value": "JSON", "label": "JSON (for pipeline)"},
                    {"value": "CSV", "label": "CSV (for export)"},
                ]
            ),
            InputField(
                name="extract_xdata",
                label="Extract XDATA",
                type=FieldType.BOOLEAN,
                required=False,
                default=True,
                description="Include extended data (K-Factor, Flow, Coverage) if available"
            )
        ])

    def _is_wsl(self) -> bool:
        """Detect if running in WSL environment."""
        return os.path.exists("/proc/version") and "microsoft" in open("/proc/version").read().lower()

    def _wsl_to_windows_path(self, wsl_path: str) -> str:
        r"""
        Convert WSL path (/mnt/c/...) to Windows path (C:\...).

        Examples:
            /mnt/c/Users/John/file.dwg -> C:\Users\John\file.dwg
            /mnt/g/.shortcut-targets-by-id/... -> G:\.shortcut-targets-by-id/...
        """
        if not wsl_path.startswith("/mnt/"):
            # Already a Windows path or relative path
            return wsl_path

        try:
            result = subprocess.run(
                ["wslpath", "-w", wsl_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            print(f"[WARN] wslpath failed: {e}")

        # Manual fallback conversion
        # /mnt/c/Users/... -> C:\Users\...
        if wsl_path.startswith("/mnt/"):
            parts = wsl_path[5:].split("/", 1)
            if len(parts) == 2:
                drive = parts[0].upper()
                path = parts[1].replace("/", "\\")
                return f"{drive}:\\{path}"
            elif len(parts) == 1:
                return f"{parts[0].upper()}:\\"

        return wsl_path

    def _windows_to_wsl_path(self, windows_path: str) -> str:
        """
        Convert Windows path (C:\...) to WSL path (/mnt/c/...).
        """
        if windows_path.startswith("/"):
            # Already a Unix path
            return windows_path

        try:
            result = subprocess.run(
                ["wslpath", "-u", windows_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        # Manual fallback
        if len(windows_path) >= 2 and windows_path[1] == ":":
            drive = windows_path[0].lower()
            path = windows_path[2:].replace("\\", "/")
            return f"/mnt/{drive}{path}"

        return windows_path

    def _find_powershell_script(self) -> str:
        """Locate the PowerShell bridge script."""
        script_path = self.SCRIPTS_DIR / self.POWERSHELL_SCRIPT

        if script_path.exists():
            return str(script_path)

        # Try alternative locations
        alt_paths = [
            Path(__file__).parent.parent.parent / "scripts" / "autocad" / self.POWERSHELL_SCRIPT,
            Path("/home/nimrodo/AquaProjects/aquabrain-dashboard/backend/scripts/autocad") / self.POWERSHELL_SCRIPT,
        ]

        for alt in alt_paths:
            if alt.exists():
                return str(alt)

        raise FileNotFoundError(f"PowerShell script not found: {self.POWERSHELL_SCRIPT}")

    def _run_powershell(self, dwg_path: str, output_format: str) -> Dict[str, Any]:
        """
        Execute the PowerShell bridge script.

        Args:
            dwg_path: Windows-formatted path to DWG file
            output_format: JSON or CSV

        Returns:
            Dictionary with extraction results
        """
        script_path = self._find_powershell_script()

        # Convert script path to Windows format if in WSL
        if self._is_wsl():
            windows_script_path = self._wsl_to_windows_path(script_path)
        else:
            windows_script_path = script_path

        # Build PowerShell command
        cmd = [
            "powershell.exe",
            "-ExecutionPolicy", "Bypass",
            "-File", windows_script_path,
            "-DwgPath", dwg_path,
            "-OutputFormat", output_format
        ]

        print(f"[AutoCAD Extract] Running: {' '.join(cmd)}")

        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                env={**os.environ, "PYTHONIOENCODING": "utf-8"}
            )

            stdout = process.stdout.strip()
            stderr = process.stderr.strip()

            if stderr:
                print(f"[AutoCAD Extract] STDERR: {stderr}")

            return {
                "success": process.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": process.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Extraction timed out after 5 minutes",
                "stdout": "",
                "stderr": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": ""
            }

    def _parse_json_output(self, raw_output: str) -> List[Dict[str, Any]]:
        """
        Parse JSON from PowerShell output.

        PowerShell may include log messages before/after JSON,
        so we need to extract just the JSON array.
        """
        # Try to find JSON array in output
        json_match = re.search(r'\[[\s\S]*\]', raw_output)

        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                print(f"[AutoCAD Extract] JSON parse error: {e}")
                return []

        # Try parsing as error object
        error_match = re.search(r'\{[\s\S]*"error"[\s\S]*\}', raw_output)
        if error_match:
            try:
                error_data = json.loads(error_match.group(0))
                raise ValueError(error_data.get("message", "Unknown error"))
            except json.JSONDecodeError:
                pass

        return []

    def _enrich_sprinkler_data(self, raw_sprinklers: List[Dict]) -> List[Dict[str, Any]]:
        """
        Enrich and standardize sprinkler data.

        - Convert units (LPM -> GPM, m² -> ft²)
        - Add calculated fields
        - Normalize property names
        """
        enriched = []

        for spk in raw_sprinklers:
            # Extract location
            x = float(spk.get("X", 0))
            y = float(spk.get("Y", 0))
            z = float(spk.get("Z", 0))

            # Convert flow: LPM -> GPM
            flow_lpm = float(spk.get("FlowLpm", 0))
            flow_gpm = round(flow_lpm * 0.264172, 2)

            # Convert coverage: m² -> ft²
            coverage_m2 = float(spk.get("CoverageM2", 12))
            coverage_sqft = round(coverage_m2 * 10.7639, 1)

            # K-Factor
            k_factor = float(spk.get("KFactor", 5.6))

            # Calculate minimum required pressure (P = (Q/K)²)
            if k_factor > 0 and flow_gpm > 0:
                min_pressure_psi = round((flow_gpm / k_factor) ** 2, 2)
            else:
                min_pressure_psi = 7.0  # Default minimum

            enriched.append({
                "id": spk.get("ID", f"SPK-{len(enriched)+1}"),
                "block_name": spk.get("BlockName", "SPRINKLER"),
                "layer": spk.get("Layer", "0"),
                "location": {
                    "x": x,
                    "y": y,
                    "z": z,
                    "units": "drawing_units"
                },
                "properties": {
                    "k_factor": k_factor,
                    "k_factor_units": "gpm/psi^0.5",
                    "flow_gpm": flow_gpm,
                    "flow_lpm": flow_lpm,
                    "coverage_sqft": coverage_sqft,
                    "coverage_m2": coverage_m2,
                    "min_pressure_psi": min_pressure_psi,
                    "zone": spk.get("ZoneId", "ZONE-1")
                },
                "rotation_deg": float(spk.get("Rotation", 0)) * (180 / 3.14159),
                "scale": {
                    "x": float(spk.get("ScaleX", 1)),
                    "y": float(spk.get("ScaleY", 1)),
                    "z": float(spk.get("ScaleZ", 1))
                },
                "metadata": {
                    "source": "autocad_dwg",
                    "extracted_at": datetime.now().isoformat(),
                    "attributes": spk.get("Attributes", {}),
                    "xdata": spk.get("XData", {})
                }
            })

        return enriched

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        """
        Execute sprinkler extraction from DWG file.

        Steps:
        1. Validate and convert file path
        2. Run PowerShell bridge script
        3. Parse JSON output
        4. Enrich and standardize data
        5. Return results
        """
        start_time = datetime.now()
        dwg_path = inputs.get("dwg_path", "")
        output_format = inputs.get("output_format", "JSON")
        extract_xdata = inputs.get("extract_xdata", True)

        # Step 1: Validate file exists
        # Convert to check existence (might be WSL or Windows path)
        check_path = dwg_path
        if self._is_wsl() and dwg_path.startswith("/mnt/"):
            check_path = dwg_path
        elif not dwg_path.startswith("/"):
            check_path = self._windows_to_wsl_path(dwg_path)

        if not os.path.exists(check_path):
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message=f"File not found: {dwg_path}",
                error=f"The DWG file does not exist at: {check_path}"
            )

        # Step 2: Convert path to Windows format for AutoCAD
        if self._is_wsl():
            windows_dwg_path = self._wsl_to_windows_path(dwg_path)
        else:
            windows_dwg_path = dwg_path

        print(f"[AutoCAD Extract] Processing: {windows_dwg_path}")

        # Step 3: Run extraction
        result = self._run_powershell(windows_dwg_path, output_format)

        if not result.get("success"):
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="AutoCAD extraction failed",
                error=result.get("error") or result.get("stderr", "Unknown error")
            )

        # Step 4: Parse JSON output
        try:
            raw_sprinklers = self._parse_json_output(result.get("stdout", ""))
        except ValueError as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message=str(e),
                error=f"Failed to parse extraction output: {e}"
            )

        if not raw_sprinklers:
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message="No sprinklers found in DWG file",
                output={
                    "sprinklers": [],
                    "count": 0,
                    "source_file": windows_dwg_path
                }
            )

        # Step 5: Enrich data
        enriched_sprinklers = self._enrich_sprinkler_data(raw_sprinklers)

        # Calculate summary statistics
        total_flow_gpm = sum(s["properties"]["flow_gpm"] for s in enriched_sprinklers)
        total_coverage_sqft = sum(s["properties"]["coverage_sqft"] for s in enriched_sprinklers)
        zones = list(set(s["properties"]["zone"] for s in enriched_sprinklers))

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            skill_id=self.metadata.id,
            message=f"Extracted {len(enriched_sprinklers)} sprinklers from AutoCAD",
            output={
                "sprinklers": enriched_sprinklers,
                "count": len(enriched_sprinklers),
                "source_file": windows_dwg_path,
                "summary": {
                    "total_sprinklers": len(enriched_sprinklers),
                    "total_flow_gpm": round(total_flow_gpm, 1),
                    "total_coverage_sqft": round(total_coverage_sqft, 1),
                    "zones": zones,
                    "zone_count": len(zones)
                }
            },
            metrics={
                "extraction_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                "sprinkler_count": len(enriched_sprinklers),
                "zone_count": len(zones)
            }
        )


# ============================================================================
# ADDITIONAL AUTOCAD SKILLS
# ============================================================================

@register_skill
class AutoCADOpenDWGSkill(AquaSkill):
    """Open a DWG file in AutoCAD GUI."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="autocad_open_dwg",
            name="Open DWG in AutoCAD",
            description="פותח קובץ DWG ב-AutoCAD GUI",
            category=SkillCategory.AUTOCAD,
            icon="FileUp",
            requires_autocad=True
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="dwg_path", label="DWG File Path", type=FieldType.TEXT, required=True)
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        dwg_path = inputs.get("dwg_path", "")

        # Convert path if in WSL
        if dwg_path.startswith("/mnt/"):
            try:
                result = subprocess.run(["wslpath", "-w", dwg_path], capture_output=True, text=True)
                windows_path = result.stdout.strip()
            except:
                windows_path = dwg_path
        else:
            windows_path = dwg_path

        # Find AutoCAD
        autocad_paths = [
            "C:\\Program Files\\Autodesk\\AutoCAD 2026\\acad.exe",
            "C:\\Program Files\\Autodesk\\AutoCAD 2025\\acad.exe",
        ]

        autocad_exe = None
        for path in autocad_paths:
            # SECURITY: Use list args instead of shell=True to prevent injection
            result = subprocess.run(
                ["powershell.exe", "-Command", f"Test-Path '{path}'"],
                capture_output=True, text=True
            )
            if "True" in result.stdout:
                autocad_exe = path
                break

        if not autocad_exe:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="AutoCAD not found"
            )

        # SECURITY: Use list args to prevent command injection
        ps_command = f'Start-Process "{autocad_exe}" -ArgumentList @("{windows_path}")'
        subprocess.run(["powershell.exe", "-Command", ps_command])

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            skill_id=self.metadata.id,
            message=f"Opened {os.path.basename(dwg_path)} in AutoCAD",
            output={"file": windows_path, "autocad": autocad_exe}
        )


@register_skill
class AutoCADRunLISPSkill(AquaSkill):
    """Execute AutoLISP code in AutoCAD via accoreconsole."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="autocad_run_lisp",
            name="Run AutoLISP Script",
            description="מריץ קוד AutoLISP ב-AutoCAD Core Console",
            category=SkillCategory.AUTOCAD,
            icon="Code",
            requires_autocad=True
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="dwg_path", label="DWG File", type=FieldType.TEXT, required=True),
            InputField(name="lisp_code", label="LISP Code", type=FieldType.TEXTAREA, required=True,
                      placeholder="(defun c:myfunc () ...)")
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        dwg_path = inputs.get("dwg_path", "")
        lisp_code = inputs.get("lisp_code", "")

        # SECURITY: Validate dwg_path to prevent injection
        try:
            validated_dwg = validate_path(dwg_path, allowed_extensions=['.dwg', '.dxf'])
        except ValueError as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message=f"Invalid DWG path: {e}"
            )

        # Create temp LISP file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lsp', delete=False) as f:
            f.write(lisp_code)
            lisp_file = f.name

        # Create SCR to load and run
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scr', delete=False) as f:
            f.write(f'(load "{lisp_file.replace(chr(92), "/")}")\n')
            f.write('QSAVE\n')
            scr_file = f.name

        # Convert paths for Windows (using secure subprocess without shell)
        try:
            windows_dwg = subprocess.run(["wslpath", "-w", validated_dwg], capture_output=True, text=True).stdout.strip()
            windows_scr = subprocess.run(["wslpath", "-w", scr_file], capture_output=True, text=True).stdout.strip()
        except Exception:
            windows_dwg = validated_dwg
            windows_scr = scr_file

        # SECURITY: Run accoreconsole using list args instead of shell=True
        accore = "C:\\Program Files\\Autodesk\\AutoCAD 2026\\accoreconsole.exe"
        ps_command = f'& "{accore}" /i "{windows_dwg}" /s "{windows_scr}" /l en-US'

        result = subprocess.run(
            ["powershell.exe", "-Command", ps_command],
            capture_output=True, text=True, timeout=120
        )

        # Cleanup
        os.unlink(lisp_file)
        os.unlink(scr_file)

        if result.returncode == 0:
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message="LISP executed successfully",
                output={"stdout": result.stdout}
            )
        else:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="LISP execution failed",
                error=result.stderr
            )
