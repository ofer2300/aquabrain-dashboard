"""
AquaBrain Traffic Light Service V1.0
=====================================
The Decision Engine - Translates complex engineering data into
simple GO/CAUTION/STOP signals for the engineer.

This is the "Augmented Intelligence" layer that bridges
machine computation and human decision-making.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


class TrafficLightStatus(Enum):
    """Traffic light status codes."""
    GREEN = "GREEN"    # All clear - proceed to fabrication
    YELLOW = "YELLOW"  # Caution - review recommended
    RED = "RED"        # Stop - critical issues detected


@dataclass
class TrafficLightResult:
    """
    Result from traffic light analysis.

    Attributes:
        status: GREEN/YELLOW/RED status
        message: Human-readable status message (Hebrew)
        details: List of specific findings
        action_required: What the engineer needs to do (if any)
        confidence: AI confidence level (0.0-1.0)
        metrics: Engineering metrics summary
    """
    status: TrafficLightStatus
    message: str
    details: List[str] = field(default_factory=list)
    action_required: Optional[str] = None
    confidence: float = 0.95
    metrics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "action_required": self.action_required,
            "confidence": self.confidence,
            "metrics": self.metrics,
        }


class TrafficLightService:
    """
    Traffic Light Decision Service.

    Analyzes engineering results and produces a simple traffic light
    signal for the engineer. This is the core of "Augmented Intelligence" -
    the AI does the heavy lifting, but the human makes the final call.

    Decision Matrix:
    ================
    RED (Stop):
        - NFPA 13 non-compliance (velocity > 32 fps)
        - Critical structural clashes
        - Insufficient water supply pressure
        - Missing fire department connection

    YELLOW (Caution):
        - Velocity 20-32 fps (allowed but suboptimal)
        - Soft clashes (MEP vs MEP)
        - High pressure loss (>50 PSI)
        - Near-limit coverage areas

    GREEN (Go):
        - All NFPA 13 requirements met
        - Velocity < 20 fps (recommended)
        - No clashes or soft clashes only
        - Adequate pressure margin (>20%)
    """

    # Thresholds
    VELOCITY_MAX_FPS = 32.0        # NFPA 13 maximum
    VELOCITY_RECOMMENDED_FPS = 20.0 # Industry recommendation
    VELOCITY_MIN_FPS = 2.0          # Minimum to prevent sediment
    PRESSURE_LOSS_WARNING_PSI = 50.0
    PRESSURE_LOSS_CRITICAL_PSI = 75.0

    def __init__(self):
        """Initialize the traffic light service."""
        pass

    def analyze(
        self,
        hydraulic_results: Dict[str, Any],
        clash_data: Optional[List[Dict]] = None,
        nfpa_compliance: Optional[Dict[str, Any]] = None,
    ) -> TrafficLightResult:
        """
        Analyze engineering results and determine traffic light status.

        Args:
            hydraulic_results: Results from hydraulic calculation
            clash_data: List of detected clashes (if any)
            nfpa_compliance: NFPA 13 compliance check results

        Returns:
            TrafficLightResult with status and explanation
        """
        clashes = clash_data or []
        compliance = nfpa_compliance or {"compliant": True}

        # Extract metrics
        max_velocity = self._extract_velocity(hydraulic_results)
        pressure_loss = self._extract_pressure_loss(hydraulic_results)

        metrics = {
            "maxVelocity": round(max_velocity, 2),
            "pressureLoss": round(pressure_loss, 2),
            "clashCount": len(clashes),
            "nfpaCompliant": compliance.get("compliant", True),
        }

        # === LAYER 1: Critical NFPA Violations (RED) ===
        if not compliance.get("compliant", True):
            return TrafficLightResult(
                status=TrafficLightStatus.RED,
                message="חריגת תקן קריטית - NFPA 13",
                details=compliance.get("violations", ["Non-compliant design"]),
                action_required="תקן את העיצוב לפני המשך",
                confidence=0.99,
                metrics=metrics,
            )

        # === LAYER 2: Critical Velocity Violation (RED) ===
        if max_velocity > self.VELOCITY_MAX_FPS:
            return TrafficLightResult(
                status=TrafficLightStatus.RED,
                message="מהירות זרימה קריטית",
                details=[
                    f"מהירות: {max_velocity:.1f} fps",
                    f"מקסימום מותר: {self.VELOCITY_MAX_FPS} fps",
                    "חריגה מתקן NFPA 13",
                    "סכנת שחיקת צנרת ורעש",
                ],
                action_required="הגדל קוטר צנרת או הפחת ספיקה",
                confidence=0.99,
                metrics=metrics,
            )

        # === LAYER 3: Critical Clashes (RED) ===
        critical_clashes = self._find_critical_clashes(clashes)
        if critical_clashes:
            return TrafficLightResult(
                status=TrafficLightStatus.RED,
                message="התנגשויות קריטיות זוהו",
                details=[
                    f"נמצאו {len(critical_clashes)} התנגשויות קריטיות",
                    *[f"• {c.get('description', 'Clash')}" for c in critical_clashes[:3]],
                ],
                action_required="פתור התנגשויות לפני המשך",
                confidence=0.95,
                metrics=metrics,
            )

        # === LAYER 4: High Velocity Warning (YELLOW) ===
        if max_velocity > self.VELOCITY_RECOMMENDED_FPS:
            return TrafficLightResult(
                status=TrafficLightStatus.YELLOW,
                message="מהירות זרימה גבוהה",
                details=[
                    f"מהירות: {max_velocity:.1f} fps",
                    f"מומלץ: מתחת ל-{self.VELOCITY_RECOMMENDED_FPS} fps",
                    "בתוך גבולות התקן אך לא אופטימלי",
                    "שקול הגדלת קוטר צנרת",
                ],
                action_required="בדיקה מומלצת",
                confidence=0.90,
                metrics=metrics,
            )

        # === LAYER 5: High Pressure Loss (YELLOW) ===
        if pressure_loss > self.PRESSURE_LOSS_WARNING_PSI:
            return TrafficLightResult(
                status=TrafficLightStatus.YELLOW,
                message="אובדן לחץ גבוה",
                details=[
                    f"אובדן לחץ: {pressure_loss:.1f} PSI",
                    "וודא זמינות לחץ מספקת",
                    "שקול הגדלת קוטר צנרת ראשית",
                ],
                action_required="בדוק לחץ זמין במקור המים",
                confidence=0.85,
                metrics=metrics,
            )

        # === LAYER 6: Minor Clashes (YELLOW) ===
        if clashes:
            return TrafficLightResult(
                status=TrafficLightStatus.YELLOW,
                message="התנגשויות קלות זוהו",
                details=[
                    f"נמצאו {len(clashes)} התנגשויות",
                    "אין התנגשויות קריטיות",
                    "מומלץ לבדוק לפני ייצור",
                ],
                action_required="בדיקה מומלצת",
                confidence=0.85,
                metrics=metrics,
            )

        # === LAYER 7: Low Velocity Warning (YELLOW) ===
        if max_velocity < self.VELOCITY_MIN_FPS and max_velocity > 0:
            return TrafficLightResult(
                status=TrafficLightStatus.YELLOW,
                message="מהירות זרימה נמוכה",
                details=[
                    f"מהירות: {max_velocity:.1f} fps",
                    f"מינימום מומלץ: {self.VELOCITY_MIN_FPS} fps",
                    "סכנת שקיעת משקעים",
                ],
                action_required="שקול הקטנת קוטר צנרת",
                confidence=0.80,
                metrics=metrics,
            )

        # === ALL CLEAR: GREEN ===
        return TrafficLightResult(
            status=TrafficLightStatus.GREEN,
            message="תכנון אופטימלי - מאושר להמשך",
            details=[
                "✓ עומד בתקן NFPA 13",
                "✓ ללא התנגשויות",
                "✓ הידראוליקה תקינה",
                f"✓ מהירות: {max_velocity:.1f} fps",
                f"✓ אובדן לחץ: {pressure_loss:.1f} PSI",
            ],
            action_required=None,
            confidence=0.95,
            metrics=metrics,
        )

    def _extract_velocity(self, hydraulic_results: Dict) -> float:
        """Extract maximum velocity from hydraulic results."""
        # Handle various result formats
        if "totals" in hydraulic_results:
            return hydraulic_results["totals"].get("max_velocity_fps", 0)
        if "max_velocity_fps" in hydraulic_results:
            return hydraulic_results["max_velocity_fps"]
        if "velocity_fps" in hydraulic_results:
            return hydraulic_results["velocity_fps"]
        if "velocity" in hydraulic_results:
            return hydraulic_results["velocity"]
        return 0.0

    def _extract_pressure_loss(self, hydraulic_results: Dict) -> float:
        """Extract total pressure loss from hydraulic results."""
        if "totals" in hydraulic_results:
            return hydraulic_results["totals"].get("total_pressure_loss_psi", 0)
        if "total_pressure_loss_psi" in hydraulic_results:
            return hydraulic_results["total_pressure_loss_psi"]
        if "pressure_loss_psi" in hydraulic_results:
            return hydraulic_results["pressure_loss_psi"]
        if "pressure_loss" in hydraulic_results:
            return hydraulic_results["pressure_loss"]
        return 0.0

    def _find_critical_clashes(self, clashes: List[Dict]) -> List[Dict]:
        """Find critical clashes (structural elements)."""
        critical = []
        for clash in clashes:
            severity = clash.get("severity", "").upper()
            clash_type = clash.get("type", "").lower()

            # Critical if high severity or structural element
            if severity in ["HIGH", "CRITICAL"]:
                critical.append(clash)
            elif any(s in clash_type for s in ["beam", "column", "structure", "slab"]):
                critical.append(clash)

        return critical


# Singleton instance for easy access
traffic_light_service = TrafficLightService()
