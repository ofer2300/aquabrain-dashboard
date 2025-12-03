"""
Revit Autopilot Skill
=====================
The "Tesla of Engineering" - one-click automation for MEP design.

This skill wraps the existing engineering orchestration pipeline:
1. Extract geometry from Revit (via WSL Bridge)
2. Voxelize the space for pathfinding
3. Run A* algorithm for optimal pipe routing
4. Calculate hydraulics (Hazen-Williams LOD 500)
5. Generate LOD 500 model in Revit
6. Return Traffic Light status (GREEN/YELLOW/RED)

Now exposed through the Universal Orchestrator!
"""

from typing import Dict, Any
from skills.base import (
    AquaSkill,
    SkillMetadata,
    InputSchema,
    InputField,
    FieldType,
    SkillCategory,
    ExecutionResult,
    ExecutionStatus,
    register_skill,
)


@register_skill
class RevitAutopilotSkill(AquaSkill):
    """
    Full engineering automation pipeline.

    One click triggers the complete workflow:
    - Semantic Reality Capture from Revit
    - A* Pathfinding for pipe routing
    - LOD 500 Hydraulic calculations
    - NFPA 13 compliance validation
    - Traffic Light status generation
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="revit_autopilot",
            name="Revit Autopilot",
            description="Full engineering automation pipeline - Extract, Route, Calculate, Validate",
            category=SkillCategory.REVIT,
            icon="Rocket",
            color="#FF6B35",
            version="3.0.0",
            author="AquaBrain Core",
            tags=["revit", "autopilot", "hydraulics", "nfpa", "automation"],
            is_async=True,
            estimated_duration_sec=30,
            requires_revit=True,
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="project_id",
                label="Project ID",
                type=FieldType.TEXT,
                required=True,
                placeholder="e.g., PROJ_001",
                description="Unique identifier for the engineering project",
            ),
            InputField(
                name="hazard_class",
                label="NFPA 13 Hazard Class",
                type=FieldType.SELECT,
                required=True,
                default="ordinary_1",
                options=[
                    {"value": "light", "label": "Light Hazard"},
                    {"value": "ordinary_1", "label": "Ordinary Hazard Group 1"},
                    {"value": "ordinary_2", "label": "Ordinary Hazard Group 2"},
                    {"value": "extra_1", "label": "Extra Hazard Group 1"},
                    {"value": "extra_2", "label": "Extra Hazard Group 2"},
                ],
                description="Fire hazard classification per NFPA 13",
            ),
            InputField(
                name="revit_version",
                label="Revit Version",
                type=FieldType.SELECT,
                required=False,
                default="auto",
                options=[
                    {"value": "auto", "label": "Auto-Detect"},
                    {"value": "2024", "label": "Revit 2024"},
                    {"value": "2025", "label": "Revit 2025"},
                    {"value": "2026", "label": "Revit 2026"},
                ],
                description="Target Revit version for COM bridge",
            ),
            InputField(
                name="notes",
                label="Engineering Notes",
                type=FieldType.TEXTAREA,
                required=False,
                default="",
                placeholder="Any special requirements or constraints...",
                description="Additional notes for the engineering team",
            ),
            InputField(
                name="mock_mode",
                label="Mock Mode (Demo)",
                type=FieldType.BOOLEAN,
                required=False,
                default=True,
                description="Use simulated data instead of real Revit connection",
            ),
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        """
        Execute the full engineering pipeline.

        This wraps the existing orchestrator logic into the skill framework.
        """
        try:
            project_id = inputs.get("project_id", "DEMO_PROJECT")
            hazard_class = inputs.get("hazard_class", "ordinary_1")
            revit_version = inputs.get("revit_version", "auto")
            notes = inputs.get("notes", "")
            mock_mode = inputs.get("mock_mode", True)

            # Import the orchestrator service
            from services.orchestrator import run_engineering_process_sync

            # Run the pipeline
            result = run_engineering_process_sync(
                project_id=project_id,
                hazard_class=hazard_class,
                notes=notes,
                revit_version=revit_version,
                mock_mode=mock_mode,
            )

            # Determine status based on traffic light
            traffic_light = result.get("traffic_light", {})
            status_color = traffic_light.get("status", "YELLOW")

            message = f"Pipeline completed - Traffic Light: {status_color}"

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=message,
                output=result,
                metrics={
                    "traffic_light_status": status_color,
                    "compliance_score": traffic_light.get("compliance_score", 0),
                    "project_id": project_id,
                    "hazard_class": hazard_class,
                },
            )

        except Exception as e:
            import traceback
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="Engineering pipeline failed",
                error=str(e),
                error_traceback=traceback.format_exc(),
            )
