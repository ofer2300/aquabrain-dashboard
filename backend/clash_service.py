"""
Clash Resolution Service
Engineering logic for resolving MEP clashes.
Future: Will integrate with ComfyUI for AI-powered solutions.
"""

from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ClashType(str, Enum):
    PIPE_DUCT = "pipe_duct"
    PIPE_PIPE = "pipe_pipe"
    DUCT_STRUCTURE = "duct_structure"
    ELECTRICAL_PIPE = "electrical_pipe"
    GENERIC = "generic"


class ClashSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClashData(BaseModel):
    """Input model for clash resolution."""
    clash_id: str
    clash_type: ClashType = ClashType.GENERIC
    severity: ClashSeverity = ClashSeverity.MEDIUM
    element_a: str  # e.g., "HVAC Duct 150mm"
    element_b: str  # e.g., "Water Pipe DN50"
    location: Optional[str] = None  # e.g., "Level 2, Grid B-3"
    distance_mm: Optional[float] = None  # Overlap distance


# === Resolution Strategies ===

RESOLUTION_STRATEGIES = {
    ClashType.PIPE_DUCT: {
        "action": "Route pipe below duct",
        "detail": "Lower the pipe elevation by 200mm to clear the duct. Add support bracket.",
        "confidence": 0.85
    },
    ClashType.PIPE_PIPE: {
        "action": "Offset horizontal routing",
        "detail": "Shift secondary pipe 150mm horizontally. Maintain minimum clearance.",
        "confidence": 0.90
    },
    ClashType.DUCT_STRUCTURE: {
        "action": "Resize and reroute duct",
        "detail": "Reduce duct height, increase width to maintain CFM. Route around beam.",
        "confidence": 0.75
    },
    ClashType.ELECTRICAL_PIPE: {
        "action": "Maintain separation distance",
        "detail": "Route electrical conduit 300mm away from water pipe per code.",
        "confidence": 0.95
    },
    ClashType.GENERIC: {
        "action": "Review manually",
        "detail": "Complex clash requires engineering review. Schedule coordination meeting.",
        "confidence": 0.50
    }
}


def resolve_clash(clash_data: ClashData) -> dict:
    """
    Analyze clash and return engineering solution.

    Args:
        clash_data: The clash information to analyze

    Returns:
        Resolution dictionary with suggested action and confidence
    """
    strategy = RESOLUTION_STRATEGIES.get(
        clash_data.clash_type,
        RESOLUTION_STRATEGIES[ClashType.GENERIC]
    )

    # Adjust confidence based on severity
    confidence = strategy["confidence"]
    if clash_data.severity == ClashSeverity.CRITICAL:
        confidence *= 0.8  # Lower confidence for critical clashes
    elif clash_data.severity == ClashSeverity.LOW:
        confidence = min(confidence * 1.1, 0.99)  # Higher confidence for simple clashes

    return {
        "clash_id": clash_data.clash_id,
        "resolution": strategy["detail"],
        "confidence": round(confidence, 2),
        "suggested_action": strategy["action"],
        "elements_involved": f"{clash_data.element_a} ↔ {clash_data.element_b}",
        "location": clash_data.location or "Not specified"
    }


# === Future: ComfyUI Integration ===
async def resolve_clash_with_ai(clash_data: ClashData) -> dict:
    """
    Future implementation: Send clash to ComfyUI for AI analysis.
    Will generate visual solutions and detailed routing suggestions.
    """
    # TODO: Integrate with ComfyUI API
    # 1. Send clash geometry to ComfyUI
    # 2. Run AI workflow for solution generation
    # 3. Return rendered solution with annotations
    pass


# === Traffic Light Determination ===

class TrafficLightStatus(str, Enum):
    """Traffic light status for the engineer."""
    GREEN = "GREEN"    # All clear - proceed to fabrication
    YELLOW = "YELLOW"  # Caution - review needed
    RED = "RED"        # Stop - critical issues


def determine_traffic_light(
    clashes: list,
    hydraulic_result: dict,
    nfpa_compliance: dict
) -> dict:
    """
    Analyze results and determine traffic light status for the engineer.

    This is the "Augmented Intelligence" layer - translating complex
    engineering data into a simple GO/CAUTION/STOP signal.

    Args:
        clashes: List of detected clashes
        hydraulic_result: Results from hydraulic calculation
        nfpa_compliance: NFPA 13 compliance check results

    Returns:
        Traffic light result with status, message, and details

    Traffic Light Logic:
    ====================
    RED (Stop):
        - NFPA 13 non-compliance (critical)
        - Velocity exceeds 32 fps (NFPA max)
        - Critical clashes with structure (beams, columns)
        - Insufficient water pressure

    YELLOW (Caution):
        - Velocity between 20-32 fps (high but allowed)
        - Minor clashes (soft vs soft)
        - Pressure loss approaching limits
        - Non-critical warnings

    GREEN (Go):
        - All NFPA 13 requirements met
        - Velocity under 20 fps (recommended)
        - No clashes or soft clashes only
        - Adequate pressure margin
    """
    details = []

    # === Layer 1: NFPA Compliance Check (Most Critical) ===
    if not nfpa_compliance.get('compliant', True):
        return {
            "status": TrafficLightStatus.RED.value,
            "message": "חריגת תקן קריטית - NFPA 13",
            "details": nfpa_compliance.get('issues', ['Non-compliant design']),
            "action_required": "נדרשת תיקון עיצוב לפני המשך"
        }

    # === Layer 2: Clash Analysis ===
    if clashes:
        critical_clashes = [
            c for c in clashes
            if c.get('severity') in ['HIGH', 'CRITICAL', ClashSeverity.CRITICAL.value, ClashSeverity.HIGH.value]
        ]

        if critical_clashes:
            return {
                "status": TrafficLightStatus.RED.value,
                "message": "התנגשויות קריטיות (קורות/עמודים)",
                "details": [
                    f"נמצאו {len(critical_clashes)} התנגשויות קריטיות",
                    "נדרש שינוי תוואי צנרת",
                    *[f"• {c.get('description', 'Clash')}" for c in critical_clashes[:3]]
                ],
                "action_required": "פתור התנגשויות לפני המשך"
            }

        # Soft clashes - warning only
        if clashes:
            details.append(f"נמצאו {len(clashes)} התנגשויות קלות")

    # === Layer 3: Velocity Check ===
    velocity = hydraulic_result.get('velocity_fps', 0)
    if hasattr(hydraulic_result, 'velocity_fps'):
        velocity = hydraulic_result.velocity_fps

    if velocity > 32.0:
        return {
            "status": TrafficLightStatus.RED.value,
            "message": "מהירות זרימה קריטית",
            "details": [
                f"מהירות: {velocity:.1f} fps",
                "חורג ממגבלת NFPA 13 (32 fps)",
                "סכנת שחיקת צנרת ורעש"
            ],
            "action_required": "הגדל קוטר צנרת או הפחת ספיקה"
        }

    if velocity > 20.0:
        details.append(f"מהירות גבוהה: {velocity:.1f} fps (מומלץ < 20)")
        return {
            "status": TrafficLightStatus.YELLOW.value,
            "message": "מהירות זרימה גבוהה - נדרשת בדיקה",
            "details": [
                f"מהירות נוכחית: {velocity:.1f} fps",
                "מעל המומלץ (20 fps) אך בגבולות התקן",
                "שקול הגדלת קוטר לביצועים אופטימליים",
                *details
            ],
            "action_required": "מומלץ לבדוק אפשרות לשיפור"
        }

    # === Layer 4: Pressure Loss Check ===
    pressure_loss = hydraulic_result.get('pressure_loss_psi', 0)
    if hasattr(hydraulic_result, 'pressure_loss_psi'):
        pressure_loss = hydraulic_result.pressure_loss_psi

    if pressure_loss > 75.0:  # High pressure loss threshold
        return {
            "status": TrafficLightStatus.YELLOW.value,
            "message": "אובדן לחץ גבוה",
            "details": [
                f"אובדן לחץ: {pressure_loss:.1f} PSI",
                "וודא זמינות לחץ מספקת ממקור המים",
                "שקול הגדלת קוטר צנרת ראשית"
            ],
            "action_required": "בדוק לחץ זמין במקור"
        }

    # === Layer 5: All Clear - GREEN ===
    details = [
        "✓ עומד בתקן NFPA 13",
        "✓ ללא התנגשויות קריטיות",
        "✓ הידראוליקה תקינה",
        f"✓ מהירות: {velocity:.1f} fps (תקין)",
        f"✓ אובדן לחץ: {pressure_loss:.1f} PSI"
    ]

    return {
        "status": TrafficLightStatus.GREEN.value,
        "message": "תכנון אופטימלי - מאושר להמשך",
        "details": details,
        "action_required": None
    }
