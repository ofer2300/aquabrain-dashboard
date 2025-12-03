"""
Hydraulic Calculator Skill
==========================
Hazen-Williams calculation for fire protection systems.
"""

from typing import Dict, Any
from skills.base import (
    AquaSkill, SkillMetadata, InputSchema, InputField,
    FieldType, SkillCategory, ExecutionResult, ExecutionStatus,
    register_skill
)


@register_skill
class HydraulicCalculatorSkill(AquaSkill):
    """
    Calculate hydraulic parameters using Hazen-Williams formula.
    LOD 500 accurate calculations for fire protection design.
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="builtin_hydraulic",
            name="Hydraulic Calculator",
            description="Calculate pressure loss and velocity for pipe segments using Hazen-Williams formula",
            category=SkillCategory.HYDRAULICS,
            icon="Droplets",
            color="#00E676",
            version="2.0.0",
            author="AquaBrain Core",
            tags=["hazen-williams", "pressure", "velocity", "nfpa13", "fire-protection"],
            is_async=False,
            estimated_duration_sec=1,
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="flow_gpm",
                label="Flow Rate (GPM)",
                type=FieldType.NUMBER,
                required=True,
                min_value=1,
                max_value=5000,
                placeholder="100",
                description="Water flow rate in gallons per minute"
            ),
            InputField(
                name="diameter_inch",
                label="Pipe Diameter (inches)",
                type=FieldType.SELECT,
                required=True,
                options=[
                    {"value": "1", "label": "1 inch"},
                    {"value": "1.25", "label": "1.25 inch"},
                    {"value": "1.5", "label": "1.5 inch"},
                    {"value": "2", "label": "2 inch"},
                    {"value": "2.5", "label": "2.5 inch"},
                    {"value": "3", "label": "3 inch"},
                    {"value": "4", "label": "4 inch"},
                    {"value": "6", "label": "6 inch"},
                ],
                default="2"
            ),
            InputField(
                name="length_ft",
                label="Pipe Length (feet)",
                type=FieldType.NUMBER,
                required=True,
                min_value=1,
                max_value=10000,
                placeholder="50",
                description="Total equivalent pipe length"
            ),
            InputField(
                name="c_factor",
                label="C-Factor",
                type=FieldType.SELECT,
                required=False,
                options=[
                    {"value": "100", "label": "100 - Cast Iron (old)"},
                    {"value": "120", "label": "120 - Steel (standard)"},
                    {"value": "140", "label": "140 - Copper"},
                    {"value": "150", "label": "150 - Plastic/CPVC"},
                ],
                default="120",
                description="Hazen-Williams roughness coefficient"
            ),
            InputField(
                name="schedule",
                label="Pipe Schedule",
                type=FieldType.SELECT,
                required=False,
                options=[
                    {"value": "40", "label": "Schedule 40"},
                    {"value": "10", "label": "Schedule 10"},
                ],
                default="40"
            ),
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        """Execute Hazen-Williams calculation."""
        try:
            # Extract inputs
            flow = float(inputs.get('flow_gpm', 100))
            diameter = float(inputs.get('diameter_inch', 2))
            length = float(inputs.get('length_ft', 50))
            c_factor = float(inputs.get('c_factor', 120))
            schedule = inputs.get('schedule', '40')

            # Nominal to actual diameter (Schedule 40)
            actual_diameter_map = {
                1: 1.049, 1.25: 1.380, 1.5: 1.610, 2: 2.067,
                2.5: 2.469, 3: 3.068, 4: 4.026, 6: 6.065
            }
            actual_diameter = actual_diameter_map.get(diameter, diameter)

            # Hazen-Williams formula
            # P = 4.52 * Q^1.85 / (C^1.85 * d^4.87)
            friction_per_ft = 4.52 * (flow ** 1.85) / ((c_factor ** 1.85) * (actual_diameter ** 4.87))
            pressure_loss = friction_per_ft * length

            # Velocity calculation
            # V = 0.4085 * Q / d^2
            velocity = 0.4085 * flow / (actual_diameter ** 2)

            # Compliance checks
            velocity_ok = velocity <= 20  # NFPA 13 recommended max
            velocity_critical = velocity > 32  # Absolute max

            # Build result
            result = {
                "pressure_loss_psi": round(pressure_loss, 3),
                "friction_per_ft": round(friction_per_ft, 5),
                "velocity_fps": round(velocity, 2),
                "actual_diameter_inch": actual_diameter,
                "compliant": velocity_ok,
                "warnings": [],
                "calculation": {
                    "formula": "Hazen-Williams",
                    "inputs": {
                        "flow_gpm": flow,
                        "diameter_inch": diameter,
                        "actual_diameter_inch": actual_diameter,
                        "length_ft": length,
                        "c_factor": c_factor,
                    }
                }
            }

            if not velocity_ok:
                result["warnings"].append(f"Velocity {velocity:.1f} fps exceeds recommended 20 fps")
            if velocity_critical:
                result["warnings"].append(f"CRITICAL: Velocity {velocity:.1f} fps exceeds maximum 32 fps")

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"Calculated: {pressure_loss:.2f} PSI loss, {velocity:.1f} fps velocity",
                output=result,
                metrics={
                    "pressure_loss_psi": pressure_loss,
                    "velocity_fps": velocity,
                    "compliant": velocity_ok
                }
            )

        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                error=str(e),
                message="Hydraulic calculation failed"
            )
