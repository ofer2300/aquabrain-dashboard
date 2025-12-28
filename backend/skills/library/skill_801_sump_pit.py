"""
AquaBrain Skill #801 - SUMP PIT OPTIMIZER
==========================================
Optimizes fire suppression sump pit design via AutoCAD integration.

What This Skill Does:
1. Connects to AutoCAD via the bridge
2. Reads selected polylines (sump pit outlines)
3. Calculates volume based on pit area + bottom level
4. Validates against fire suppression requirements (min 100m³)
5. Annotates the drawing with verification stamp
6. Returns Traffic Light status for dashboard

Flow:
    User selects polylines → Input bottom level → Calculate volume →
    Validate → Draw revision cloud → Add verification text → Return result

Standards:
- Israeli Standard ת"י 1596 for fire water tanks
- Minimum 100m³ for most occupancy types
- Safety factor 1.2 recommended

Author: AquaBrain V8.0 Platinum
Date: 2025-12-04
"""

from __future__ import annotations
import os
import sys
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from enum import Enum

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
        get_selection_area,
        add_text_annotation,
        draw_revision_cloud,
        zoom_to_selection,
        test_connection,
        get_sump_pit_selection,
        annotate_verification,
        MOCK_MODE
    )
    BRIDGE_AVAILABLE = True
except ImportError:
    BRIDGE_AVAILABLE = False
    MOCK_MODE = True


# ============================================================================
# CONSTANTS
# ============================================================================

class ValidationStatus(str, Enum):
    GREEN = "green"   # Volume >= required with safety factor
    YELLOW = "yellow" # Volume meets minimum but no safety factor
    RED = "red"       # Volume below minimum


# Minimum volumes by occupancy type (m³)
VOLUME_REQUIREMENTS = {
    "residential": 50,      # מגורים
    "office": 75,           # משרדים
    "commercial": 100,      # מסחרי
    "industrial": 150,      # תעשייה
    "warehouse": 200,       # מחסנים
    "high_hazard": 300,     # סיכון גבוה
    "default": 100          # ברירת מחדל
}

# Safety factor for volume calculation
SAFETY_FACTOR = 1.2

# Default reference level (usually ground level or basement slab)
DEFAULT_TOP_LEVEL = 0.00


# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================

def calculate_pit_volume(
    area_sqm: float,
    top_level: float,
    bottom_level: float
) -> float:
    """
    Calculate sump pit volume.

    Args:
        area_sqm: Pit area in square meters
        top_level: Top of pit level (m)
        bottom_level: Bottom of pit level (m)

    Returns:
        Volume in cubic meters
    """
    depth = abs(top_level - bottom_level)
    volume = area_sqm * depth
    return round(volume, 2)


def validate_volume(
    volume: float,
    occupancy_type: str = "default",
    safety_factor: float = SAFETY_FACTOR
) -> Tuple[ValidationStatus, str]:
    """
    Validate pit volume against requirements.

    Args:
        volume: Calculated volume in m³
        occupancy_type: Building occupancy type
        safety_factor: Safety factor to apply

    Returns:
        Tuple of (ValidationStatus, message)
    """
    required = VOLUME_REQUIREMENTS.get(occupancy_type, VOLUME_REQUIREMENTS["default"])
    required_with_safety = required * safety_factor

    if volume >= required_with_safety:
        return (
            ValidationStatus.GREEN,
            f"נפח {volume}m³ עומד בדרישות ({required}m³ + מקדם ביטחון {safety_factor})"
        )
    elif volume >= required:
        return (
            ValidationStatus.YELLOW,
            f"נפח {volume}m³ עומד במינימום ({required}m³) אך ללא מקדם ביטחון"
        )
    else:
        deficit = required - volume
        return (
            ValidationStatus.RED,
            f"נפח {volume}m³ נמוך מהנדרש ({required}m³). חסרים {deficit:.1f}m³"
        )


# ============================================================================
# SKILL #801 - SUMP PIT OPTIMIZER
# ============================================================================

@register_skill
class SumpPitOptimizer(AquaSkill):
    """
    SKILL #801 - SUMP PIT OPTIMIZER

    Optimizes fire suppression sump pit design by:
    1. Reading pit geometry from AutoCAD selection
    2. Calculating volume based on user-specified depth
    3. Validating against fire code requirements
    4. Annotating the drawing with verification stamp
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="801",
            name="בור איגום - אופטימיזציה",
            description="חישוב נפח בור איגום מתוך AutoCAD, אימות מול תקן ת\"י 1596, והטבעת חותמת אישור.",
            category=SkillCategory.AUTOCAD,
            icon="Droplets",  # Water drop icon
            color="#0EA5E9",  # Cyan/water blue
            tags=["autocad", "sump", "fire", "volume", "optimization"],
            is_async=False,
            estimated_duration_sec=5,
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
                default="calculate",
                options=[
                    {"value": "calculate", "label": "חשב וודא נפח"},
                    {"value": "connect", "label": "בדוק חיבור AutoCAD"},
                    {"value": "demo", "label": "הדגמה (Mock)"}
                ]
            ),
            InputField(
                name="bottom_level",
                label="מפלס תחתית (מ')",
                type=FieldType.NUMBER,
                required=False,
                default=-7.90,
                placeholder="-7.90"
            ),
            InputField(
                name="top_level",
                label="מפלס עליון (מ')",
                type=FieldType.NUMBER,
                required=False,
                default=0.00,
                placeholder="0.00"
            ),
            InputField(
                name="occupancy_type",
                label="סוג אכלוס",
                type=FieldType.SELECT,
                required=False,
                default="commercial",
                options=[
                    {"value": "residential", "label": "מגורים (50m³)"},
                    {"value": "office", "label": "משרדים (75m³)"},
                    {"value": "commercial", "label": "מסחרי (100m³)"},
                    {"value": "industrial", "label": "תעשייה (150m³)"},
                    {"value": "warehouse", "label": "מחסנים (200m³)"},
                    {"value": "high_hazard", "label": "סיכון גבוה (300m³)"}
                ]
            ),
            InputField(
                name="annotate",
                label="הוסף חותמת לשרטוט",
                type=FieldType.BOOLEAN,
                required=False,
                default=True
            )
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        """Execute sump pit optimization."""
        action = inputs.get("action", "calculate")
        start_time = datetime.now()

        try:
            if action == "connect":
                result = self._test_connection()
            elif action == "demo":
                result = self._run_demo(inputs)
            elif action == "calculate":
                result = self._calculate_volume(inputs)
            else:
                result = {"error": f"פעולה לא מוכרת: {action}"}

            duration = (datetime.now() - start_time).total_seconds()
            result["duration_seconds"] = round(duration, 1)

            # Determine status based on validation
            status = result.get("traffic_light", "green")
            exec_status = ExecutionStatus.SUCCESS if status != "red" else ExecutionStatus.SUCCESS

            return ExecutionResult(
                status=exec_status,
                skill_id=self.metadata.id,
                message=result.get("message", "חישוב הושלם"),
                output=result
            )

        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="שגיאה באופטימיזציית בור האיגום",
                error=str(e)
            )

    def _test_connection(self) -> Dict[str, Any]:
        """Test AutoCAD connection."""
        if not BRIDGE_AVAILABLE:
            return {
                "connected": False,
                "message": "גשר AutoCAD לא זמין",
                "mock_mode": True
            }

        conn = test_connection()
        return {
            "connected": conn.get("connected", False),
            "mock_mode": conn.get("mock_mode", True),
            "version": conn.get("data", {}).get("version", "N/A"),
            "document": conn.get("data", {}).get("document", "N/A"),
            "message": "מחובר ל-AutoCAD" if conn.get("connected") else "לא מחובר"
        }

    def _run_demo(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run demo with mock data."""
        bottom_level = inputs.get("bottom_level", -7.90)
        top_level = inputs.get("top_level", 0.00)
        occupancy_type = inputs.get("occupancy_type", "commercial")

        # Mock selection: 3 pits totaling 12.5 m²
        mock_area = 12.5

        # Calculate volume
        volume = calculate_pit_volume(mock_area, top_level, bottom_level)

        # Validate
        status, validation_msg = validate_volume(volume, occupancy_type)

        return {
            "message": f"[DEMO] נפח בור איגום: {volume} m³",
            "mock_mode": True,
            "traffic_light": status.value,
            "calculation": {
                "pit_count": 3,
                "total_area_sqm": mock_area,
                "depth_m": abs(top_level - bottom_level),
                "volume_m3": volume,
                "required_m3": VOLUME_REQUIREMENTS.get(occupancy_type, 100),
                "safety_factor": SAFETY_FACTOR
            },
            "validation": {
                "status": status.value,
                "message": validation_msg,
                "occupancy_type": occupancy_type
            },
            "annotation": {
                "added": True,
                "text": f"AquaBrain Verified: Vol={volume}m³, Status={status.value.upper()}",
                "handle": "MOCK_ANNOTATION_001"
            },
            "revision_cloud": {
                "added": True,
                "handle": "MOCK_CLOUD_001"
            }
        }

    def _calculate_volume(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate pit volume from AutoCAD selection."""
        bottom_level = inputs.get("bottom_level", -7.90)
        top_level = inputs.get("top_level", 0.00)
        occupancy_type = inputs.get("occupancy_type", "commercial")
        annotate = inputs.get("annotate", True)

        # Get selection from AutoCAD
        if not BRIDGE_AVAILABLE or MOCK_MODE:
            return self._run_demo(inputs)

        try:
            # Get pit selection
            selection = get_sump_pit_selection()

            if not selection.get("success"):
                return {
                    "message": "לא הצלחתי לקרוא בחירה מ-AutoCAD",
                    "error": selection.get("error", "Unknown error"),
                    "traffic_light": "red"
                }

            pit_count = selection.get("pit_count", 0)
            total_area = selection.get("total_area_sqm", 0)

            if pit_count == 0:
                return {
                    "message": "לא נבחרו פוליליינים. בחר את בורות האיגום ב-AutoCAD.",
                    "traffic_light": "yellow",
                    "hint": "בחר פוליליינים סגורים המייצגים את בורות האיגום"
                }

            # Calculate volume
            volume = calculate_pit_volume(total_area, top_level, bottom_level)

            # Validate
            status, validation_msg = validate_volume(volume, occupancy_type)

            result = {
                "message": f"נפח בור איגום: {volume} m³ - {status.value.upper()}",
                "mock_mode": selection.get("mock_mode", False),
                "traffic_light": status.value,
                "calculation": {
                    "pit_count": pit_count,
                    "total_area_sqm": total_area,
                    "depth_m": abs(top_level - bottom_level),
                    "volume_m3": volume,
                    "required_m3": VOLUME_REQUIREMENTS.get(occupancy_type, 100),
                    "safety_factor": SAFETY_FACTOR
                },
                "validation": {
                    "status": status.value,
                    "message": validation_msg,
                    "occupancy_type": occupancy_type
                }
            }

            # Add annotations if requested
            if annotate:
                annotation_result = self._add_annotations(
                    volume, status, selection.get("objects", [])
                )
                result["annotation"] = annotation_result.get("annotation")
                result["revision_cloud"] = annotation_result.get("revision_cloud")

            return result

        except Exception as e:
            return {
                "message": f"שגיאה בחישוב: {str(e)}",
                "traffic_light": "red",
                "error": str(e)
            }

    def _add_annotations(
        self,
        volume: float,
        status: ValidationStatus,
        objects: List[Dict]
    ) -> Dict[str, Any]:
        """Add verification annotations to AutoCAD."""
        result = {
            "annotation": {"added": False},
            "revision_cloud": {"added": False}
        }

        try:
            # Calculate center point from first object (simplified)
            center_x = 3000  # Default position
            center_y = 2500

            # Create verification text
            verification_text = (
                f"AquaBrain Verified\\P"
                f"Volume: {volume} m³\\P"
                f"Status: {status.value.upper()}\\P"
                f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )

            color = 3 if status == ValidationStatus.GREEN else (2 if status == ValidationStatus.YELLOW else 1)

            text_result = add_text_annotation(
                verification_text,
                (center_x + 500, center_y + 500, 0),
                height=150.0,
                color=color
            )

            result["annotation"] = {
                "added": text_result.success,
                "text": verification_text.replace("\\P", "\n"),
                "handle": text_result.data.get("handle"),
                "mock_mode": text_result.mock_mode
            }

            # Draw revision cloud around pits
            cloud_points = [
                (center_x - 200, center_y - 200),
                (center_x + 1500, center_y - 200),
                (center_x + 1500, center_y + 1000),
                (center_x - 200, center_y + 1000)
            ]

            cloud_result = draw_revision_cloud(cloud_points, color=color)

            result["revision_cloud"] = {
                "added": cloud_result.success,
                "handle": cloud_result.data.get("handle"),
                "mock_mode": cloud_result.mock_mode
            }

        except Exception as e:
            result["error"] = str(e)

        return result


# ============================================================================
# ALTERNATIVE SKILL NAME
# ============================================================================

# Also register with full name
@register_skill
class Skill_SumpPitOptimizer(SumpPitOptimizer):
    """Alias for SumpPitOptimizer with different ID."""

    @property
    def metadata(self) -> SkillMetadata:
        base = super().metadata
        return SkillMetadata(
            id="skill_801_sump_pit",
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
    'SumpPitOptimizer',
    'Skill_SumpPitOptimizer',
    'calculate_pit_volume',
    'validate_volume',
    'ValidationStatus',
    'VOLUME_REQUIREMENTS',
    'SAFETY_FACTOR',
]
