"""
AquaBrain Skill #802 - DWG UPDATER & DELIVERY
==============================================
Automates DWG modification, annotation, and delivery to architects/engineers.

What This Skill Does:
1. Opens specified DWG file in AutoCAD
2. Finds and replaces text values (e.g., elevation changes)
3. Draws revision cloud around modified areas
4. Adds AquaBrain verification stamp
5. Saves as new file with version suffix
6. Exports PDF for quick reference
7. Sends email with attachments to requester

Use Case:
- Shiran (Architect) requests: "עדכני את הגובה מ-8.57- ל-7.90-"
- AquaBrain: Opens DWG → Finds "-8.57" → Replaces → Annotates → Saves → Emails

Author: AquaBrain V9.0 Platinum
Date: 2025-12-04
"""

from __future__ import annotations
import os
import sys
import re
import smtplib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from skills.base import (
    AquaSkill, ExecutionResult, ExecutionStatus,
    SkillMetadata, SkillCategory, InputSchema, InputField, FieldType,
    register_skill
)

# Import AutoCAD bridge
try:
    from scripts.bridge_autocad import (
        connect_autocad,
        get_active_document,
        add_text_annotation,
        draw_revision_cloud,
        execute_lisp,
        zoom_to_selection,
        test_connection,
        MOCK_MODE
    )
    BRIDGE_AVAILABLE = True
except ImportError:
    BRIDGE_AVAILABLE = False
    MOCK_MODE = True


# ============================================================================
# CONSTANTS
# ============================================================================

# Output directory for updated DWGs
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "dwg_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Email configuration
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")


# ============================================================================
# AUTOCAD OPERATIONS
# ============================================================================

def open_dwg_file(file_path: str) -> Dict[str, Any]:
    """
    Open a DWG file in AutoCAD.

    Args:
        file_path: Full path to the DWG file

    Returns:
        Dictionary with open status
    """
    if MOCK_MODE or not BRIDGE_AVAILABLE:
        return {
            "success": True,
            "mock_mode": True,
            "file": file_path,
            "message": f"[MOCK] Opened: {Path(file_path).name}"
        }

    script = f'''
    try {{
        $acad = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
        $doc = $acad.Documents.Open("{file_path.replace(chr(92), chr(92)+chr(92))}")
        @{{
            success = $true
            name = $doc.Name
            path = $doc.FullName
        }} | ConvertTo-Json
    }} catch {{
        @{{
            success = $false
            error = $_.Exception.Message
        }} | ConvertTo-Json
    }}
    '''

    from scripts.bridge_autocad import run_powershell
    result = run_powershell(script)
    return result.data if result.success else {"success": False, "error": result.error}


def find_and_replace_text(search_text: str, replace_text: str) -> Dict[str, Any]:
    """
    Find and replace text in the active DWG document.

    Args:
        search_text: Text to find (e.g., "-8.57")
        replace_text: Replacement text (e.g., "-7.90")

    Returns:
        Dictionary with replacement results including coordinates
    """
    if MOCK_MODE or not BRIDGE_AVAILABLE:
        # Mock: simulate finding 3 instances
        return {
            "success": True,
            "mock_mode": True,
            "found_count": 3,
            "replaced_count": 3,
            "locations": [
                {"handle": "2A3F", "x": 1500, "y": 2000, "old_text": search_text, "new_text": replace_text},
                {"handle": "2B4C", "x": 3200, "y": 2000, "old_text": search_text, "new_text": replace_text},
                {"handle": "2C5D", "x": 4800, "y": 2000, "old_text": search_text, "new_text": replace_text}
            ],
            "message": f"[MOCK] Replaced '{search_text}' with '{replace_text}' in 3 locations"
        }

    # Real implementation using AutoCAD COM
    script = f'''
    try {{
        $acad = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
        $doc = $acad.ActiveDocument
        $modelSpace = $doc.ModelSpace

        $searchText = "{search_text}"
        $replaceText = "{replace_text}"
        $locations = @()
        $replacedCount = 0

        foreach ($obj in $modelSpace) {{
            try {{
                # Check Text entities
                if ($obj.ObjectName -eq "AcDbText" -or $obj.ObjectName -eq "AcDbMText") {{
                    $currentText = $obj.TextString
                    if ($currentText -like "*$searchText*") {{
                        $newText = $currentText -replace [regex]::Escape($searchText), $replaceText
                        $obj.TextString = $newText

                        $pt = $obj.InsertionPoint
                        $locations += @{{
                            handle = $obj.Handle
                            x = $pt[0]
                            y = $pt[1]
                            old_text = $currentText
                            new_text = $newText
                        }}
                        $replacedCount++
                    }}
                }}
            }} catch {{ }}
        }}

        $doc.Regen(1)

        @{{
            success = $true
            found_count = $locations.Count
            replaced_count = $replacedCount
            locations = $locations
        }} | ConvertTo-Json -Depth 3
    }} catch {{
        @{{
            success = $false
            error = $_.Exception.Message
        }} | ConvertTo-Json
    }}
    '''

    from scripts.bridge_autocad import run_powershell
    result = run_powershell(script, timeout=60)
    return result.data if result.success else {"success": False, "error": result.error}


def save_dwg_as(new_filename: str) -> Dict[str, Any]:
    """
    Save the active document with a new filename.

    Args:
        new_filename: New filename (without path - saves to OUTPUT_DIR)

    Returns:
        Dictionary with save status
    """
    output_path = OUTPUT_DIR / new_filename

    if MOCK_MODE or not BRIDGE_AVAILABLE:
        return {
            "success": True,
            "mock_mode": True,
            "path": str(output_path),
            "message": f"[MOCK] Saved as: {new_filename}"
        }

    # Convert to Windows path for PowerShell
    win_path = str(output_path).replace("/", "\\")

    script = f'''
    try {{
        $acad = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
        $doc = $acad.ActiveDocument
        $doc.SaveAs("{win_path}")
        @{{
            success = $true
            path = "{win_path}"
        }} | ConvertTo-Json
    }} catch {{
        @{{
            success = $false
            error = $_.Exception.Message
        }} | ConvertTo-Json
    }}
    '''

    from scripts.bridge_autocad import run_powershell
    result = run_powershell(script)
    return result.data if result.success else {"success": False, "error": result.error}


def export_pdf(pdf_filename: str) -> Dict[str, Any]:
    """
    Export the current view to PDF.

    Args:
        pdf_filename: PDF filename (without path)

    Returns:
        Dictionary with export status
    """
    output_path = OUTPUT_DIR / pdf_filename

    if MOCK_MODE or not BRIDGE_AVAILABLE:
        return {
            "success": True,
            "mock_mode": True,
            "path": str(output_path),
            "message": f"[MOCK] Exported PDF: {pdf_filename}"
        }

    # Use PLOT command with PDF driver
    win_path = str(output_path).replace("/", "\\")

    script = f'''
    try {{
        $acad = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
        $doc = $acad.ActiveDocument

        # Configure plot
        $doc.SendCommand("-PLOT Y Model DWG To PDF.pc3 ISO A3 M 1:100 C L N . Y {win_path} N Y`n")

        Start-Sleep -Seconds 3

        @{{
            success = $true
            path = "{win_path}"
        }} | ConvertTo-Json
    }} catch {{
        @{{
            success = $false
            error = $_.Exception.Message
        }} | ConvertTo-Json
    }}
    '''

    from scripts.bridge_autocad import run_powershell
    result = run_powershell(script, timeout=30)
    return result.data if result.success else {"success": False, "error": result.error}


# ============================================================================
# EMAIL DELIVERY
# ============================================================================

def send_update_email(
    recipient: str,
    recipient_name: str,
    old_value: str,
    new_value: str,
    dwg_path: Optional[str] = None,
    pdf_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send email with updated DWG and PDF attachments.

    Args:
        recipient: Email address
        recipient_name: Name for greeting
        old_value: Original value that was changed
        new_value: New value
        dwg_path: Path to DWG file (optional)
        pdf_path: Path to PDF file (optional)

    Returns:
        Dictionary with send status
    """
    today = datetime.now().strftime("%d/%m/%Y")

    # Email body in Hebrew
    body = f"""היי {recipient_name},

בהמשך לבקשתך, מצורף קובץ DWG מעודכן.

גובה בורות השאיבה עודכן מ-{old_value} ל-{new_value}.
סימנתי את השינוי בענן רוויזיה (Revision Cloud).

קבצים מצורפים:
• קובץ DWG מעודכן
• קובץ PDF לעיון מהיר

בברכה,
AquaBrain
(בשם נימרוד עופר)

---
עודכן אוטומטית ב-{today}
AquaBrain V9.0 - AutoCAD Automation"""

    if not GMAIL_USER or MOCK_MODE:
        return {
            "success": True,
            "mock_mode": True,
            "to": recipient,
            "subject": f"עדכון DWG - גובה בורות שאיבה {new_value}",
            "body_preview": body[:200] + "...",
            "message": f"[MOCK] Email sent to {recipient}"
        }

    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = recipient
        msg['Subject'] = f"עדכון DWG - גובה בורות שאיבה {new_value}"

        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # Attach DWG
        if dwg_path and Path(dwg_path).exists():
            with open(dwg_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{Path(dwg_path).name}"'
                )
                msg.attach(part)

        # Attach PDF
        if pdf_path and Path(pdf_path).exists():
            with open(pdf_path, 'rb') as f:
                part = MIMEBase('application', 'pdf')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{Path(pdf_path).name}"'
                )
                msg.attach(part)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)

        return {
            "success": True,
            "to": recipient,
            "subject": msg['Subject'],
            "attachments": [
                Path(dwg_path).name if dwg_path else None,
                Path(pdf_path).name if pdf_path else None
            ]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "mock_fallback": True,
            "to": recipient,
            "message": f"[MOCK] Email would be sent to {recipient}"
        }


# ============================================================================
# SKILL #802 - DWG UPDATER & DELIVERY
# ============================================================================

@register_skill
class DWGUpdaterSkill(AquaSkill):
    """
    SKILL #802 - DWG UPDATER & DELIVERY

    Automates the complete workflow:
    1. Open DWG file
    2. Find and replace text values
    3. Draw revision cloud
    4. Add AquaBrain stamp
    5. Save new version
    6. Export PDF
    7. Email to requester
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="802",
            name="עדכון DWG ושליחה",
            description="עדכון אוטומטי של ערכים בשרטוט AutoCAD, הוספת ענן רוויזיה, ושליחה במייל.",
            category=SkillCategory.AUTOCAD,
            icon="FileEdit",  # Edit icon
            color="#F59E0B",  # Amber/Orange
            tags=["autocad", "dwg", "update", "email", "delivery", "revision"],
            is_async=False,
            estimated_duration_sec=30,
            requires_autocad=True
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="action",
                label="פעולה",
                type=FieldType.SELECT,
                required=True,
                default="update_and_send",
                options=[
                    {"value": "update_and_send", "label": "עדכן ושלח"},
                    {"value": "update_only", "label": "עדכן בלבד (ללא מייל)"},
                    {"value": "demo", "label": "הדגמה (Mock)"}
                ]
            ),
            InputField(
                name="dwg_file",
                label="קובץ DWG",
                type=FieldType.TEXT,
                required=False,
                default="2046_P3_18.06.2025.dwg",
                placeholder="שם הקובץ או נתיב מלא"
            ),
            InputField(
                name="search_text",
                label="טקסט לחיפוש",
                type=FieldType.TEXT,
                required=False,
                default="-8.57",
                placeholder="-8.57"
            ),
            InputField(
                name="replace_text",
                label="טקסט להחלפה",
                type=FieldType.TEXT,
                required=False,
                default="-7.90",
                placeholder="-7.90"
            ),
            InputField(
                name="recipient_email",
                label="מייל נמען",
                type=FieldType.EMAIL,
                required=False,
                default="shiran@architect.co.il",
                placeholder="shiran@architect.co.il"
            ),
            InputField(
                name="recipient_name",
                label="שם נמען",
                type=FieldType.TEXT,
                required=False,
                default="שירן",
                placeholder="שירן"
            )
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        """Execute DWG update and delivery workflow."""
        action = inputs.get("action", "update_and_send")
        start_time = datetime.now()

        try:
            if action == "demo":
                result = self._run_demo(inputs)
            elif action == "update_only":
                result = self._update_dwg(inputs, send_email=False)
            elif action == "update_and_send":
                result = self._update_dwg(inputs, send_email=True)
            else:
                result = {"error": f"פעולה לא מוכרת: {action}"}

            duration = (datetime.now() - start_time).total_seconds()
            result["duration_seconds"] = round(duration, 1)

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=result.get("message", "עדכון הושלם"),
                output=result
            )

        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="שגיאה בעדכון DWG",
                error=str(e)
            )

    def _run_demo(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run full demo with mock data."""
        search_text = inputs.get("search_text", "-8.57")
        replace_text = inputs.get("replace_text", "-7.90")
        recipient_email = inputs.get("recipient_email", "shiran@architect.co.il")
        recipient_name = inputs.get("recipient_name", "שירן")
        dwg_file = inputs.get("dwg_file", "2046_P3_18.06.2025.dwg")

        today = datetime.now().strftime("%d.%m.%y")
        new_filename = f"1210-20-23_{today}_UPDATED_{replace_text.replace('-', '').replace('.', '_')}.dwg"
        pdf_filename = new_filename.replace(".dwg", ".pdf")

        steps = []

        # Step 1: Open DWG
        steps.append({
            "step": 1,
            "name": "Open DWG",
            "result": {
                "success": True,
                "mock_mode": True,
                "file": dwg_file,
                "message": f"[MOCK] Opened: {dwg_file}"
            }
        })

        # Step 2: Find and Replace
        replace_result = find_and_replace_text(search_text, replace_text)
        steps.append({
            "step": 2,
            "name": "Find & Replace",
            "result": replace_result
        })

        # Step 3: Draw Revision Cloud
        cloud_points = [
            (1400, 1900), (5000, 1900), (5000, 2100), (1400, 2100)
        ]
        cloud_result = draw_revision_cloud(cloud_points, color=1)
        steps.append({
            "step": 3,
            "name": "Revision Cloud",
            "result": {
                "success": True,
                "mock_mode": True,
                "handle": "MOCK_REVCLOUD_001",
                "locations_covered": replace_result.get("found_count", 0)
            }
        })

        # Step 4: Add Stamp
        stamp_text = f"UPDATED BY AQUABRAIN | {today}"
        stamp_result = add_text_annotation(stamp_text, (1500, 1700, 0), height=100, color=3)
        steps.append({
            "step": 4,
            "name": "AquaBrain Stamp",
            "result": {
                "success": True,
                "mock_mode": True,
                "text": stamp_text,
                "handle": "MOCK_STAMP_001"
            }
        })

        # Step 5: Save As
        save_result = save_dwg_as(new_filename)
        steps.append({
            "step": 5,
            "name": "Save DWG",
            "result": save_result
        })

        # Step 6: Export PDF
        pdf_result = export_pdf(pdf_filename)
        steps.append({
            "step": 6,
            "name": "Export PDF",
            "result": pdf_result
        })

        # Step 7: Send Email
        email_result = send_update_email(
            recipient=recipient_email,
            recipient_name=recipient_name,
            old_value=search_text,
            new_value=replace_text,
            dwg_path=str(OUTPUT_DIR / new_filename),
            pdf_path=str(OUTPUT_DIR / pdf_filename)
        )
        steps.append({
            "step": 7,
            "name": "Send Email",
            "result": email_result
        })

        return {
            "message": f"[DEMO] עודכן וישלח ל-{recipient_name}",
            "mock_mode": True,
            "traffic_light": "green",
            "summary": {
                "original_file": dwg_file,
                "new_file": new_filename,
                "pdf_file": pdf_filename,
                "changes": {
                    "search": search_text,
                    "replace": replace_text,
                    "count": replace_result.get("replaced_count", 3)
                },
                "email_sent_to": recipient_email
            },
            "steps": steps
        }

    def _update_dwg(self, inputs: Dict[str, Any], send_email: bool = True) -> Dict[str, Any]:
        """Execute actual DWG update workflow."""
        search_text = inputs.get("search_text", "-8.57")
        replace_text = inputs.get("replace_text", "-7.90")
        recipient_email = inputs.get("recipient_email", "shiran@architect.co.il")
        recipient_name = inputs.get("recipient_name", "שירן")
        dwg_file = inputs.get("dwg_file", "2046_P3_18.06.2025.dwg")

        # If mock mode, run demo instead
        if MOCK_MODE or not BRIDGE_AVAILABLE:
            return self._run_demo(inputs)

        today = datetime.now().strftime("%d.%m.%y")
        new_filename = f"1210-20-23_{today}_UPDATED_{replace_text.replace('-', '').replace('.', '_')}.dwg"
        pdf_filename = new_filename.replace(".dwg", ".pdf")

        results = {"steps": []}

        try:
            # Step 1: Open DWG
            open_result = open_dwg_file(dwg_file)
            results["steps"].append({"step": 1, "name": "Open DWG", "result": open_result})

            if not open_result.get("success"):
                return {
                    "message": f"שגיאה בפתיחת הקובץ: {open_result.get('error')}",
                    "traffic_light": "red",
                    "steps": results["steps"]
                }

            # Step 2: Find and Replace
            replace_result = find_and_replace_text(search_text, replace_text)
            results["steps"].append({"step": 2, "name": "Find & Replace", "result": replace_result})

            if replace_result.get("replaced_count", 0) == 0:
                return {
                    "message": f"לא נמצא טקסט '{search_text}' בשרטוט",
                    "traffic_light": "yellow",
                    "steps": results["steps"]
                }

            # Step 3: Draw Revision Cloud around changes
            locations = replace_result.get("locations", [])
            if locations:
                # Calculate bounding box
                min_x = min(loc.get("x", 0) for loc in locations) - 200
                max_x = max(loc.get("x", 0) for loc in locations) + 500
                min_y = min(loc.get("y", 0) for loc in locations) - 100
                max_y = max(loc.get("y", 0) for loc in locations) + 100

                cloud_points = [
                    (min_x, min_y), (max_x, min_y),
                    (max_x, max_y), (min_x, max_y)
                ]
                cloud_result = draw_revision_cloud(cloud_points, color=1)
                results["steps"].append({"step": 3, "name": "Revision Cloud", "result": cloud_result})

            # Step 4: Add Stamp
            stamp_text = f"UPDATED BY AQUABRAIN | {today}"
            stamp_point = (min_x if locations else 1500, (min_y - 300) if locations else 1700, 0)
            stamp_result = add_text_annotation(stamp_text, stamp_point, height=100, color=3)
            results["steps"].append({"step": 4, "name": "AquaBrain Stamp", "result": stamp_result})

            # Step 5: Save As
            save_result = save_dwg_as(new_filename)
            results["steps"].append({"step": 5, "name": "Save DWG", "result": save_result})

            # Step 6: Export PDF
            pdf_result = export_pdf(pdf_filename)
            results["steps"].append({"step": 6, "name": "Export PDF", "result": pdf_result})

            # Step 7: Send Email (if requested)
            if send_email:
                email_result = send_update_email(
                    recipient=recipient_email,
                    recipient_name=recipient_name,
                    old_value=search_text,
                    new_value=replace_text,
                    dwg_path=str(OUTPUT_DIR / new_filename),
                    pdf_path=str(OUTPUT_DIR / pdf_filename)
                )
                results["steps"].append({"step": 7, "name": "Send Email", "result": email_result})

            return {
                "message": f"עודכן בהצלחה! {replace_result.get('replaced_count', 0)} שינויים" +
                          (f" + נשלח ל-{recipient_name}" if send_email else ""),
                "traffic_light": "green",
                "summary": {
                    "original_file": dwg_file,
                    "new_file": new_filename,
                    "pdf_file": pdf_filename,
                    "changes": {
                        "search": search_text,
                        "replace": replace_text,
                        "count": replace_result.get("replaced_count", 0)
                    },
                    "email_sent_to": recipient_email if send_email else None
                },
                "steps": results["steps"]
            }

        except Exception as e:
            return {
                "message": f"שגיאה: {str(e)}",
                "traffic_light": "red",
                "error": str(e),
                "steps": results.get("steps", [])
            }


# ============================================================================
# ALTERNATIVE REGISTRATION
# ============================================================================

@register_skill
class Skill_DWGUpdater(DWGUpdaterSkill):
    """Alias with different ID."""

    @property
    def metadata(self) -> SkillMetadata:
        base = super().metadata
        return SkillMetadata(
            id="skill_802_dwg_updater",
            name=base.name,
            description=base.description,
            category=base.category,
            icon=base.icon,
            color=base.color,
            tags=base.tags,
            is_async=base.is_async,
            estimated_duration_sec=base.estimated_duration_sec,
            requires_autocad=base.requires_autocad
        )


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    'DWGUpdaterSkill',
    'Skill_DWGUpdater',
    'open_dwg_file',
    'find_and_replace_text',
    'save_dwg_as',
    'export_pdf',
    'send_update_email',
]
