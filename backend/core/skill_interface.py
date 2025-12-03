"""
AquaBrain Core Skill Interface V2.0
===================================
Extended execution context and task management for the Universal Orchestrator.

This module provides:
- ExecutionContext: Rich context passed to every skill execution
- TaskContext: Database-persisted task tracking
- SkillRunner: Unified execution engine with audit trail
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid
import json
import traceback
import asyncio
from contextlib import contextmanager

if TYPE_CHECKING:
    from skills.base import AquaSkill, ExecutionResult


class TaskStatus(str, Enum):
    """Task execution status for audit trail."""
    QUEUED = "queued"
    VALIDATING = "validating"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ExecutionContext(BaseModel):
    """
    Rich execution context passed to every skill.

    Contains all the information a skill needs to execute:
    - Task metadata (IDs, timestamps)
    - User context (who triggered this)
    - Project context (which project)
    - Environment context (Revit version, available services)
    - Payload (the actual input data)
    """

    # Task identifiers
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    skill_id: str
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])

    # User context
    user_id: Optional[str] = None
    user_name: Optional[str] = "system"

    # Project context
    project_id: Optional[str] = None
    project_name: Optional[str] = None

    # Environment
    revit_version: str = "auto"
    autocad_version: str = "auto"
    mock_mode: bool = False

    # Payload - the actual input data for the skill
    payload: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None

    # Execution settings
    timeout_seconds: int = 300  # 5 minute default
    max_retries: int = 0
    current_retry: int = 0

    # Parent task (for chained skills)
    parent_task_id: Optional[str] = None

    # Metadata for tracking
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def mark_started(self) -> None:
        """Mark execution as started."""
        self.started_at = datetime.utcnow()

    def elapsed_seconds(self) -> float:
        """Get elapsed time since start."""
        if self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return 0.0

    def is_timed_out(self) -> bool:
        """Check if execution has timed out."""
        return self.elapsed_seconds() > self.timeout_seconds


class TaskRecord(BaseModel):
    """
    Persistent record of a task execution for audit trail.
    Maps to SkillExecution database table.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    skill_id: str
    project_id: Optional[str] = None
    user_id: Optional[str] = None

    # Status tracking
    status: TaskStatus = TaskStatus.QUEUED
    current_stage: str = "queued"
    progress_percent: int = 0

    # Input/Output (JSON)
    input_params: Dict[str, Any] = Field(default_factory=dict)
    result_data: Optional[Dict[str, Any]] = None

    # Artifacts produced
    artifacts: List[Dict[str, str]] = Field(default_factory=list)

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: int = 0

    # Error tracking
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def mark_running(self) -> None:
        """Mark task as running."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.current_stage = "running"

    def mark_success(self, result: Dict[str, Any]) -> None:
        """Mark task as successful."""
        self.status = TaskStatus.SUCCESS
        self.completed_at = datetime.utcnow()
        self.result_data = result
        self.current_stage = "completed"
        self.progress_percent = 100
        if self.started_at:
            self.execution_time_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)

    def mark_failed(self, error: str, tb: Optional[str] = None) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error
        self.error_traceback = tb
        self.current_stage = "failed"
        if self.started_at:
            self.execution_time_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "current_stage": self.current_stage,
            "progress_percent": self.progress_percent,
            "input_params": self.input_params,
            "result_data": self.result_data,
            "artifacts": self.artifacts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class SkillRunner:
    """
    Unified skill execution engine.

    Features:
    - Input validation against skill schema
    - Timeout handling
    - Error capture with full traceback
    - Audit trail creation
    - Async and sync execution modes
    """

    def __init__(self, skill: 'AquaSkill'):
        self.skill = skill

    def validate_payload(self, payload: Dict[str, Any]) -> List[str]:
        """Validate payload against skill's input schema."""
        return self.skill.validate_inputs(payload)

    def execute_sync(self, context: ExecutionContext) -> TaskRecord:
        """
        Execute skill synchronously with full audit trail.

        Returns a TaskRecord with execution results.
        """
        # Create task record
        task = TaskRecord(
            id=context.task_id,
            skill_id=context.skill_id,
            project_id=context.project_id,
            user_id=context.user_id,
            input_params=context.payload,
            metadata=context.metadata,
        )

        # Validate inputs
        task.current_stage = "validating"
        task.status = TaskStatus.VALIDATING

        errors = self.validate_payload(context.payload)
        if errors:
            task.mark_failed(f"Validation failed: {'; '.join(errors)}")
            return task

        # Execute
        task.mark_running()
        context.mark_started()

        try:
            # Run the skill
            result = self.skill.safe_execute(context.payload)

            # Check for timeout
            if context.is_timed_out():
                task.status = TaskStatus.TIMEOUT
                task.mark_failed(f"Execution timed out after {context.timeout_seconds}s")
                return task

            # Process result
            if result.status.value == "success":
                task.mark_success({
                    "output": result.output,
                    "message": result.message,
                    "metrics": result.metrics,
                })
                task.artifacts = result.artifacts
            else:
                task.mark_failed(
                    result.error or result.message,
                    result.error_traceback
                )

            return task

        except Exception as e:
            task.mark_failed(str(e), traceback.format_exc())
            return task

    async def execute_async(self, context: ExecutionContext) -> TaskRecord:
        """
        Execute skill asynchronously.

        Wraps sync execution in asyncio for non-blocking operation.
        """
        # Run in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.execute_sync,
            context
        )


# ============================================================================
# SKILL DISCOVERY
# ============================================================================

import importlib
import pkgutil
from pathlib import Path


def discover_skills(skills_dir: Path) -> List[str]:
    """
    Discover all skill modules in a directory.

    Scans for Python files containing AquaSkill subclasses.
    Returns list of module paths.
    """
    discovered = []

    if not skills_dir.exists():
        return discovered

    for item in skills_dir.rglob("*.py"):
        if item.name.startswith("_"):
            continue

        # Convert path to module name
        relative = item.relative_to(skills_dir.parent)
        module_name = str(relative).replace("/", ".").replace("\\", ".").rstrip(".py")
        discovered.append(module_name)

    return discovered


def load_skill_module(module_name: str) -> bool:
    """
    Dynamically load a skill module.

    Skills are auto-registered via @register_skill decorator.
    Returns True if successful.
    """
    try:
        importlib.import_module(module_name)
        return True
    except Exception as e:
        print(f"[WARN] Failed to load skill module {module_name}: {e}")
        return False


def reload_skill_module(module_name: str) -> bool:
    """
    Hot-reload a skill module.

    Useful for development and custom skill updates.
    """
    try:
        module = importlib.import_module(module_name)
        importlib.reload(module)
        return True
    except Exception as e:
        print(f"[WARN] Failed to reload skill module {module_name}: {e}")
        return False


def initialize_skill_registry():
    """
    Initialize the skill registry by loading all builtin and custom skills.

    Called at application startup.
    """
    from pathlib import Path

    backend_dir = Path(__file__).parent.parent
    skills_dir = backend_dir / "skills"

    # Load builtin skills
    builtin_dir = skills_dir / "builtin"
    if builtin_dir.exists():
        for module_path in discover_skills(builtin_dir):
            full_path = f"skills.builtin.{module_path.split('.')[-1]}"
            load_skill_module(full_path)

    # Load custom skills
    custom_dir = skills_dir / "custom"
    if custom_dir.exists():
        for module_path in discover_skills(custom_dir):
            full_path = f"skills.custom.{module_path.split('.')[-1]}"
            load_skill_module(full_path)

    # Report loaded skills
    from skills.base import skill_registry
    skills = skill_registry.list_all()
    print(f"[INFO] Loaded {len(skills)} skills:")
    for skill in skills:
        print(f"  - {skill.metadata.id}: {skill.metadata.name}")
