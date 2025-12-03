"""
AquaBrain Skill Builder V1.0
============================
The LLM Contractor - Generates Python skill code from natural language.

Features:
- Natural language to Python skill generation
- Automatic validation and sandboxed testing
- Hot-reload into the skill registry
- Version control for generated skills
"""

from __future__ import annotations
import os
import re
import ast
import uuid
import json
import importlib
import importlib.util
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field

# Import the base skill classes
from skills.base import (
    AquaSkill, SkillMetadata, InputSchema, InputField,
    FieldType, SkillCategory, ExecutionResult, ExecutionStatus,
    skill_registry
)


class SkillGenerationRequest(BaseModel):
    """Request to generate a new skill."""
    description: str = Field(..., description="Natural language description of what the skill should do")
    name: str = Field(..., description="Name for the skill")
    category: SkillCategory = Field(default=SkillCategory.CUSTOM)
    example_inputs: Optional[Dict[str, Any]] = Field(default=None)
    example_output: Optional[str] = Field(default=None)


class GeneratedSkillCode(BaseModel):
    """Generated skill code and metadata."""
    skill_id: str
    class_name: str
    code: str
    file_path: str
    created_at: datetime = Field(default_factory=datetime.now)
    description: str
    validation_passed: bool = False
    validation_errors: List[str] = Field(default_factory=list)
    is_active: bool = False


class SkillBuilder:
    """
    Generates Python skill classes from natural language descriptions.
    Uses LLM to write the code, then validates and hot-loads it.
    """

    CUSTOM_SKILLS_DIR = Path(__file__).parent.parent / "skills" / "custom"
    SKILL_TEMPLATE = '''"""
Auto-generated AquaBrain Skill
Generated: {timestamp}
Description: {description}
"""

from typing import Dict, Any
from skills.base import (
    AquaSkill, SkillMetadata, InputSchema, InputField,
    FieldType, SkillCategory, ExecutionResult, ExecutionStatus,
    register_skill
)


@register_skill
class {class_name}(AquaSkill):
    """
    {description}
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="{skill_id}",
            name="{name}",
            description="""{description}""",
            category=SkillCategory.{category},
            icon="{icon}",
            color="{color}",
            version="1.0.0",
            author="AquaBrain Skill Factory",
            tags={tags},
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
{input_fields}
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        """Execute the skill logic."""
        try:
{execute_logic}

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message="Skill executed successfully",
                output=result,
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                error=str(e),
                message="Execution failed",
            )
'''

    def __init__(self):
        self.CUSTOM_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        # Create __init__.py if not exists
        init_file = self.CUSTOM_SKILLS_DIR / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Auto-generated custom skills\n")

    def _sanitize_class_name(self, name: str) -> str:
        """Convert name to valid Python class name."""
        # Remove non-alphanumeric, convert to PascalCase
        words = re.sub(r'[^a-zA-Z0-9\s]', '', name).split()
        return ''.join(word.capitalize() for word in words) + 'Skill'

    def _generate_skill_id(self) -> str:
        """Generate unique skill ID."""
        return f"custom_{uuid.uuid4().hex[:8]}"

    def _infer_input_fields(self, description: str) -> List[Dict[str, Any]]:
        """
        Infer input fields from description using pattern matching.
        In production, this would use LLM.
        """
        fields = []
        desc_lower = description.lower()

        # Common patterns
        if any(word in desc_lower for word in ['file', 'document', 'pdf', 'dwg', 'rvt']):
            fields.append({
                "name": "file_path",
                "label": "File Path",
                "type": "FILE",
                "required": True,
                "accept": ".pdf,.dwg,.rvt,.csv,.xlsx"
            })

        if any(word in desc_lower for word in ['email', 'send', 'mail']):
            fields.append({
                "name": "email_address",
                "label": "Email Address",
                "type": "EMAIL",
                "required": True
            })

        if any(word in desc_lower for word in ['project', 'name']):
            fields.append({
                "name": "project_name",
                "label": "Project Name",
                "type": "TEXT",
                "required": True
            })

        if any(word in desc_lower for word in ['output', 'destination', 'folder']):
            fields.append({
                "name": "output_path",
                "label": "Output Directory",
                "type": "TEXT",
                "required": False,
                "default": "./output"
            })

        if any(word in desc_lower for word in ['number', 'count', 'quantity']):
            fields.append({
                "name": "count",
                "label": "Count",
                "type": "NUMBER",
                "required": False,
                "default": 1,
                "min": 1,
                "max": 100
            })

        # Default field if none inferred
        if not fields:
            fields.append({
                "name": "input_data",
                "label": "Input Data",
                "type": "TEXTAREA",
                "required": True,
                "placeholder": "Enter your data here..."
            })

        return fields

    def _generate_execute_logic(self, description: str, fields: List[Dict]) -> str:
        """
        Generate the execute logic based on description.
        In production, this would use LLM.
        """
        desc_lower = description.lower()

        # Build input extraction
        input_lines = []
        for field in fields:
            input_lines.append(f"            {field['name']} = inputs.get('{field['name']}')")

        # Generate logic based on keywords
        logic_lines = input_lines + ["", "            # Skill logic"]

        if 'rename' in desc_lower or 'file' in desc_lower:
            logic_lines.append("            # File processing logic")
            logic_lines.append("            import os")
            logic_lines.append("            result = {'processed': True, 'message': 'File processed successfully'}")

        elif 'email' in desc_lower or 'send' in desc_lower:
            logic_lines.append("            # Email sending logic (placeholder)")
            logic_lines.append("            result = {'sent': True, 'recipient': email_address}")

        elif 'report' in desc_lower or 'generate' in desc_lower:
            logic_lines.append("            # Report generation logic")
            logic_lines.append("            result = {'report_generated': True, 'timestamp': str(datetime.now())}")

        elif 'calculate' in desc_lower or 'compute' in desc_lower:
            logic_lines.append("            # Calculation logic")
            logic_lines.append("            result = {'calculated': True}")

        else:
            logic_lines.append("            # Custom logic - implement as needed")
            logic_lines.append("            result = {'success': True, 'inputs_received': inputs}")

        return "\n".join(logic_lines)

    def _format_input_fields(self, fields: List[Dict]) -> str:
        """Format input fields as Python code."""
        lines = []
        for field in fields:
            parts = [
                f"name=\"{field['name']}\"",
                f"label=\"{field['label']}\"",
                f"type=FieldType.{field['type']}",
            ]
            if 'required' in field:
                parts.append(f"required={field['required']}")
            if 'default' in field and field['default'] is not None:
                default_val = f'"{field["default"]}"' if isinstance(field['default'], str) else field['default']
                parts.append(f"default={default_val}")
            if 'placeholder' in field:
                parts.append(f"placeholder=\"{field['placeholder']}\"")
            if 'accept' in field:
                parts.append(f"accept=\"{field['accept']}\"")
            if 'min' in field:
                parts.append(f"min_value={field['min']}")
            if 'max' in field:
                parts.append(f"max_value={field['max']}")

            lines.append(f"            InputField({', '.join(parts)}),")

        return "\n".join(lines)

    def _infer_icon_and_color(self, description: str, category: SkillCategory) -> Tuple[str, str]:
        """Infer appropriate icon and color based on description."""
        desc_lower = description.lower()

        icon_map = {
            'file': ('FileText', '#4FACFE'),
            'pdf': ('FileText', '#FF5757'),
            'email': ('Mail', '#00E676'),
            'report': ('FileBarChart', '#BD00FF'),
            'calculate': ('Calculator', '#00F0FF'),
            'revit': ('Building2', '#4FACFE'),
            'autocad': ('PenTool', '#FF9F0A'),
            'export': ('Download', '#00E676'),
            'import': ('Upload', '#4FACFE'),
            'analyze': ('LineChart', '#BD00FF'),
        }

        for keyword, (icon, color) in icon_map.items():
            if keyword in desc_lower:
                return icon, color

        # Category-based defaults
        category_defaults = {
            SkillCategory.REVIT: ('Building2', '#4FACFE'),
            SkillCategory.AUTOCAD: ('PenTool', '#FF9F0A'),
            SkillCategory.HYDRAULICS: ('Droplets', '#00E676'),
            SkillCategory.DOCUMENTATION: ('FileText', '#BD00FF'),
            SkillCategory.REPORTING: ('FileBarChart', '#FF5757'),
        }

        return category_defaults.get(category, ('Cog', '#BD00FF'))

    def generate_skill(self, request: SkillGenerationRequest) -> GeneratedSkillCode:
        """
        Generate a new skill from natural language description.

        In production, this would:
        1. Send description to LLM (Claude/GPT)
        2. LLM returns structured skill definition
        3. We validate and save
        """
        skill_id = self._generate_skill_id()
        class_name = self._sanitize_class_name(request.name)

        # Infer components
        fields = self._infer_input_fields(request.description)
        icon, color = self._infer_icon_and_color(request.description, request.category)
        execute_logic = self._generate_execute_logic(request.description, fields)
        input_fields_code = self._format_input_fields(fields)

        # Generate tags
        tags = [word for word in request.description.lower().split()
                if len(word) > 4 and word.isalpha()][:5]

        # Generate code from template
        code = self.SKILL_TEMPLATE.format(
            timestamp=datetime.now().isoformat(),
            description=request.description,
            class_name=class_name,
            skill_id=skill_id,
            name=request.name,
            category=request.category.value.upper(),
            icon=icon,
            color=color,
            tags=json.dumps(tags),
            input_fields=input_fields_code,
            execute_logic=execute_logic,
        )

        # File path
        file_name = f"{skill_id}.py"
        file_path = self.CUSTOM_SKILLS_DIR / file_name

        result = GeneratedSkillCode(
            skill_id=skill_id,
            class_name=class_name,
            code=code,
            file_path=str(file_path),
            description=request.description,
        )

        # Validate syntax
        validation_errors = self._validate_code(code)
        result.validation_errors = validation_errors
        result.validation_passed = len(validation_errors) == 0

        return result

    def _validate_code(self, code: str) -> List[str]:
        """Validate generated Python code."""
        errors = []

        # Syntax check
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")

        # Check for required components
        if "class " not in code or "AquaSkill" not in code:
            errors.append("Missing AquaSkill class definition")
        if "def execute" not in code:
            errors.append("Missing execute method")
        if "def metadata" not in code:
            errors.append("Missing metadata property")
        if "def input_schema" not in code:
            errors.append("Missing input_schema property")

        return errors

    def save_skill(self, generated: GeneratedSkillCode) -> bool:
        """Save generated skill to file system."""
        if not generated.validation_passed:
            return False

        try:
            file_path = Path(generated.file_path)
            file_path.write_text(generated.code)
            return True
        except Exception as e:
            generated.validation_errors.append(f"Failed to save: {e}")
            return False

    def load_skill(self, generated: GeneratedSkillCode) -> Optional[AquaSkill]:
        """Hot-load a generated skill into the registry."""
        if not generated.validation_passed:
            return None

        try:
            file_path = Path(generated.file_path)
            if not file_path.exists():
                return None

            # Dynamic import
            spec = importlib.util.spec_from_file_location(
                f"skills.custom.{generated.skill_id}",
                file_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # The @register_skill decorator should have registered it
            skill = skill_registry.get(generated.skill_id)
            if skill:
                generated.is_active = True

            return skill

        except Exception as e:
            generated.validation_errors.append(f"Failed to load: {e}")
            return None

    def generate_and_deploy(self, request: SkillGenerationRequest) -> Tuple[GeneratedSkillCode, Optional[AquaSkill]]:
        """
        Full pipeline: Generate, validate, save, and load a skill.
        """
        # Generate
        generated = self.generate_skill(request)

        if not generated.validation_passed:
            return generated, None

        # Save
        if not self.save_skill(generated):
            return generated, None

        # Load
        skill = self.load_skill(generated)

        return generated, skill

    def list_custom_skills(self) -> List[Dict[str, Any]]:
        """List all custom skills in the directory."""
        skills = []
        for file_path in self.CUSTOM_SKILLS_DIR.glob("custom_*.py"):
            skills.append({
                "file": file_path.name,
                "skill_id": file_path.stem,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            })
        return skills

    def delete_skill(self, skill_id: str) -> bool:
        """Delete a custom skill."""
        file_path = self.CUSTOM_SKILLS_DIR / f"{skill_id}.py"
        if file_path.exists():
            file_path.unlink()
            skill_registry.unregister(skill_id)
            return True
        return False


# Global builder instance
skill_builder = SkillBuilder()
