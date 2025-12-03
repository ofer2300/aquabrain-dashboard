"""
AquaBrain Skill Factory V1.0
============================
The Contract - All skills inherit from AquaSkill.

Features:
- Dynamic input schema (JSON Schema for auto-form generation)
- Standardized execution interface
- Built-in logging and error handling
- Metadata for UI rendering
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, Literal
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import json
import uuid
import traceback


class FieldType(str, Enum):
    """Supported input field types for dynamic forms."""
    TEXT = "text"
    NUMBER = "number"
    EMAIL = "email"
    FILE = "file"
    DATE = "date"
    DATETIME = "datetime"
    SELECT = "select"
    MULTISELECT = "multiselect"
    BOOLEAN = "boolean"
    TEXTAREA = "textarea"
    JSON = "json"
    COLOR = "color"
    RANGE = "range"


class InputField(BaseModel):
    """Definition of a single input field for the skill."""
    name: str = Field(..., description="Field identifier (snake_case)")
    label: str = Field(..., description="Display label for UI")
    type: FieldType = Field(default=FieldType.TEXT)
    required: bool = Field(default=True)
    default: Optional[Any] = Field(default=None)
    placeholder: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    # For SELECT/MULTISELECT
    options: Optional[List[Dict[str, str]]] = Field(default=None, description="[{value, label}]")
    # For NUMBER/RANGE
    min_value: Optional[float] = Field(default=None, alias="min")
    max_value: Optional[float] = Field(default=None, alias="max")
    step: Optional[float] = Field(default=None)
    # For FILE
    accept: Optional[str] = Field(default=None, description="File types: '.pdf,.dwg'")
    multiple: bool = Field(default=False)
    # Validation
    pattern: Optional[str] = Field(default=None, description="Regex pattern")
    min_length: Optional[int] = Field(default=None)
    max_length: Optional[int] = Field(default=None)

    class Config:
        populate_by_name = True


class InputSchema(BaseModel):
    """Complete input schema for a skill - defines all required inputs."""
    fields: List[InputField] = Field(default_factory=list)

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to standard JSON Schema for compatibility."""
        properties = {}
        required = []

        for field in self.fields:
            prop = {
                "title": field.label,
                "description": field.description or "",
            }

            # Map FieldType to JSON Schema types
            type_map = {
                FieldType.TEXT: {"type": "string"},
                FieldType.EMAIL: {"type": "string", "format": "email"},
                FieldType.NUMBER: {"type": "number"},
                FieldType.BOOLEAN: {"type": "boolean"},
                FieldType.DATE: {"type": "string", "format": "date"},
                FieldType.DATETIME: {"type": "string", "format": "date-time"},
                FieldType.FILE: {"type": "string", "format": "uri"},
                FieldType.TEXTAREA: {"type": "string"},
                FieldType.JSON: {"type": "object"},
                FieldType.SELECT: {"type": "string"},
                FieldType.MULTISELECT: {"type": "array", "items": {"type": "string"}},
                FieldType.COLOR: {"type": "string", "format": "color"},
                FieldType.RANGE: {"type": "number"},
            }

            prop.update(type_map.get(field.type, {"type": "string"}))

            if field.options:
                prop["enum"] = [opt["value"] for opt in field.options]
            if field.min_value is not None:
                prop["minimum"] = field.min_value
            if field.max_value is not None:
                prop["maximum"] = field.max_value
            if field.pattern:
                prop["pattern"] = field.pattern
            if field.default is not None:
                prop["default"] = field.default

            properties[field.name] = prop

            if field.required:
                required.append(field.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }


class SkillCategory(str, Enum):
    """Categories for organizing skills in the UI."""
    REVIT = "revit"
    AUTOCAD = "autocad"
    HYDRAULICS = "hydraulics"
    DOCUMENTATION = "documentation"
    FILE_PROCESSING = "file_processing"
    DATA_ANALYSIS = "data_analysis"
    REPORTING = "reporting"
    INTEGRATION = "integration"
    RPA = "rpa"  # Robotic Process Automation / Web Agents
    CUSTOM = "custom"


class SkillMetadata(BaseModel):
    """Metadata for skill display and discovery."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="What does this skill do?")
    category: SkillCategory = Field(default=SkillCategory.CUSTOM)
    icon: str = Field(default="Cog", description="Lucide icon name")
    color: str = Field(default="#BD00FF", description="Accent color (hex)")
    version: str = Field(default="1.0.0")
    author: str = Field(default="AquaBrain")
    tags: List[str] = Field(default_factory=list)
    is_async: bool = Field(default=False, description="Long-running task?")
    estimated_duration_sec: Optional[int] = Field(default=None)
    requires_revit: bool = Field(default=False)
    requires_autocad: bool = Field(default=False)


class ExecutionStatus(str, Enum):
    """Skill execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionResult(BaseModel):
    """Result of skill execution."""
    status: ExecutionStatus
    skill_id: str
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    # Output
    output: Optional[Dict[str, Any]] = None
    message: str = ""
    # Artifacts (files, reports, etc.)
    artifacts: List[Dict[str, str]] = Field(default_factory=list)
    # Errors
    error: Optional[str] = None
    error_traceback: Optional[str] = None
    # Metrics
    metrics: Dict[str, Any] = Field(default_factory=dict)


class AquaSkill(ABC):
    """
    Base class for all AquaBrain skills.

    To create a new skill:
    1. Inherit from AquaSkill
    2. Define metadata() -> SkillMetadata
    3. Define input_schema() -> InputSchema
    4. Implement execute(inputs) -> ExecutionResult

    Example:
        class MySkill(AquaSkill):
            @property
            def metadata(self) -> SkillMetadata:
                return SkillMetadata(
                    name="My Awesome Skill",
                    description="Does something awesome",
                    category=SkillCategory.CUSTOM
                )

            @property
            def input_schema(self) -> InputSchema:
                return InputSchema(fields=[
                    InputField(name="file_path", label="File", type=FieldType.FILE),
                ])

            def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
                # Your logic here
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    skill_id=self.metadata.id,
                    message="Done!",
                    output={"result": "success"}
                )
    """

    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """Return skill metadata for UI display."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> InputSchema:
        """Return the input schema for dynamic form generation."""
        pass

    @abstractmethod
    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        """Execute the skill with provided inputs."""
        pass

    def validate_inputs(self, inputs: Dict[str, Any]) -> List[str]:
        """Validate inputs against schema. Returns list of errors."""
        errors = []
        schema = self.input_schema

        for field in schema.fields:
            value = inputs.get(field.name)

            # Required check
            if field.required and value is None:
                errors.append(f"Missing required field: {field.label}")
                continue

            if value is None:
                continue

            # Type-specific validation
            if field.type == FieldType.NUMBER:
                try:
                    num = float(value)
                    if field.min_value is not None and num < field.min_value:
                        errors.append(f"{field.label} must be >= {field.min_value}")
                    if field.max_value is not None and num > field.max_value:
                        errors.append(f"{field.label} must be <= {field.max_value}")
                except (ValueError, TypeError):
                    errors.append(f"{field.label} must be a number")

            elif field.type == FieldType.EMAIL:
                if "@" not in str(value):
                    errors.append(f"{field.label} must be a valid email")

            elif field.type in [FieldType.TEXT, FieldType.TEXTAREA]:
                if field.min_length and len(str(value)) < field.min_length:
                    errors.append(f"{field.label} must be at least {field.min_length} characters")
                if field.max_length and len(str(value)) > field.max_length:
                    errors.append(f"{field.label} must be at most {field.max_length} characters")

        return errors

    def safe_execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        """Execute with error handling and timing."""
        start_time = datetime.now()

        # Validate inputs first
        errors = self.validate_inputs(inputs)
        if errors:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                started_at=start_time,
                completed_at=datetime.now(),
                error="; ".join(errors),
                message="Input validation failed"
            )

        try:
            result = self.execute(inputs)
            result.completed_at = datetime.now()
            result.duration_ms = int((result.completed_at - start_time).total_seconds() * 1000)
            return result
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                started_at=start_time,
                completed_at=datetime.now(),
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e),
                error_traceback=traceback.format_exc(),
                message="Execution failed"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize skill for API response."""
        return {
            "metadata": self.metadata.model_dump(),
            "input_schema": self.input_schema.model_dump(),
            "json_schema": self.input_schema.to_json_schema(),
        }


# ============================================================================
# SKILL REGISTRY
# ============================================================================

class SkillRegistry:
    """
    Central registry for all available skills.
    Supports hot-reloading of custom skills.
    """

    _instance: Optional['SkillRegistry'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills: Dict[str, AquaSkill] = {}
            cls._instance._initialized = False
        return cls._instance

    def register(self, skill: AquaSkill) -> None:
        """Register a skill instance."""
        self._skills[skill.metadata.id] = skill

    def unregister(self, skill_id: str) -> bool:
        """Unregister a skill by ID."""
        if skill_id in self._skills:
            del self._skills[skill_id]
            return True
        return False

    def get(self, skill_id: str) -> Optional[AquaSkill]:
        """Get a skill by ID."""
        return self._skills.get(skill_id)

    def list_all(self) -> List[AquaSkill]:
        """List all registered skills."""
        return list(self._skills.values())

    def list_by_category(self, category: SkillCategory) -> List[AquaSkill]:
        """List skills in a specific category."""
        return [s for s in self._skills.values() if s.metadata.category == category]

    def search(self, query: str) -> List[AquaSkill]:
        """Search skills by name, description, or tags."""
        query = query.lower()
        results = []
        for skill in self._skills.values():
            meta = skill.metadata
            if (query in meta.name.lower() or
                query in meta.description.lower() or
                any(query in tag.lower() for tag in meta.tags)):
                results.append(skill)
        return results

    def to_catalog(self) -> List[Dict[str, Any]]:
        """Export full catalog for frontend."""
        return [skill.to_dict() for skill in self._skills.values()]


# Global registry instance
skill_registry = SkillRegistry()


def register_skill(skill_class: Type[AquaSkill]) -> Type[AquaSkill]:
    """Decorator to auto-register a skill class."""
    instance = skill_class()
    skill_registry.register(instance)
    return skill_class
