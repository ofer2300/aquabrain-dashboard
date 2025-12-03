"""
Revit Extract Skill
===================
Extract geometry and semantic data from Revit via the bridge.
"""

from typing import Dict, Any
from skills.base import (
    AquaSkill, SkillMetadata, InputSchema, InputField,
    FieldType, SkillCategory, ExecutionResult, ExecutionStatus,
    register_skill
)


@register_skill
class RevitExtractSkill(AquaSkill):
    """
    Extract building data from Revit using the WSL-Windows bridge.
    Supports multi-version Revit (2024, 2025, 2026).
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="builtin_revit_extract",
            name="Revit Geometry Extractor",
            description="Extract walls, floors, columns, and MEP elements from Revit model with semantic metadata",
            category=SkillCategory.REVIT,
            icon="Building2",
            color="#4FACFE",
            version="3.0.0",
            author="AquaBrain Core",
            tags=["revit", "geometry", "extraction", "bim", "semantic"],
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
                placeholder="PRJ-001",
                description="AquaBrain project identifier"
            ),
            InputField(
                name="revit_version",
                label="Revit Version",
                type=FieldType.SELECT,
                required=False,
                options=[
                    {"value": "auto", "label": "Auto-Detect (Recommended)"},
                    {"value": "2026", "label": "Revit 2026"},
                    {"value": "2025", "label": "Revit 2025"},
                    {"value": "2024", "label": "Revit 2024"},
                ],
                default="auto"
            ),
            InputField(
                name="element_types",
                label="Element Types",
                type=FieldType.MULTISELECT,
                required=False,
                options=[
                    {"value": "walls", "label": "Walls"},
                    {"value": "floors", "label": "Floors"},
                    {"value": "ceilings", "label": "Ceilings"},
                    {"value": "columns", "label": "Columns"},
                    {"value": "beams", "label": "Beams"},
                    {"value": "pipes", "label": "Pipes"},
                    {"value": "ducts", "label": "Ducts"},
                ],
                default=["walls", "floors", "columns", "beams"]
            ),
            InputField(
                name="include_semantic",
                label="Include Semantic Data",
                type=FieldType.BOOLEAN,
                required=False,
                default=True,
                description="Extract fire ratings, materials, assembly codes"
            ),
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        """Execute Revit geometry extraction."""
        try:
            project_id = inputs.get('project_id', 'UNKNOWN')
            revit_version = inputs.get('revit_version', 'auto')
            element_types = inputs.get('element_types', ['walls', 'floors'])
            include_semantic = inputs.get('include_semantic', True)

            # Import the bridge
            from scripts.bridge_revit import get_geometry, get_semantic_data

            # Extract data
            if include_semantic:
                data = get_semantic_data(project_id, target_version=revit_version)
            else:
                data = get_geometry(project_id, target_version=revit_version)

            element_count = len(data.get('elements', data.get('geometry', {}).get('walls', [])))

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"Extracted {element_count} elements from Revit",
                output=data,
                metrics={
                    "element_count": element_count,
                    "revit_version": revit_version,
                    "semantic": include_semantic
                }
            )

        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                error=str(e),
                message="Revit extraction failed"
            )
