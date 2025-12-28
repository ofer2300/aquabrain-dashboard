"""
AquaBrain Universal Orchestrator API
=====================================
"One Endpoint to Rule Them All"

The Universal Trigger - a single endpoint that can invoke ANY registered skill.

Features:
- Dynamic skill invocation by ID
- Input validation against skill schema
- Async execution with task tracking
- Full audit trail in database
- Support for chained skill execution
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import threading

from skills.base import skill_registry, AquaSkill
from core.skill_interface import (
    ExecutionContext,
    TaskRecord,
    TaskStatus,
    SkillRunner,
)
from models import SessionLocal, get_db

router = APIRouter(prefix="/api/orchestrator", tags=["Orchestrator"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TriggerRequest(BaseModel):
    """
    Universal trigger request.

    This is the standardized input for ANY skill execution.
    """
    skill_id: str = Field(..., description="The registered skill ID to execute")
    project_id: Optional[str] = Field(None, description="Project context (if applicable)")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Skill-specific input data")

    # Execution options
    async_mode: bool = Field(True, description="Execute asynchronously (returns task_id)")
    timeout_seconds: int = Field(300, ge=1, le=3600, description="Execution timeout")

    # Context
    user_id: Optional[str] = Field(None, description="User who triggered this")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Chaining
    parent_task_id: Optional[str] = Field(None, description="Parent task for chained execution")


class TriggerResponse(BaseModel):
    """Response from the universal trigger."""
    task_id: str
    skill_id: str
    status: str
    message: str
    queued_at: datetime


class TaskStatusResponse(BaseModel):
    """Full task status response."""
    id: str
    skill_id: str
    status: str
    current_stage: str
    progress_percent: int
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    execution_time_ms: int
    result_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    artifacts: List[Dict[str, str]]


# ============================================================================
# IN-MEMORY TASK STORE (Production would use Redis/DB)
# ============================================================================

# Simple in-memory store for task records
# In production, this would be backed by Redis or a database
_task_store: Dict[str, TaskRecord] = {}
_task_lock = threading.Lock()


def store_task(task: TaskRecord) -> None:
    """Store a task record."""
    with _task_lock:
        _task_store[task.id] = task


def get_task(task_id: str) -> Optional[TaskRecord]:
    """Retrieve a task record."""
    with _task_lock:
        return _task_store.get(task_id)


def update_task(task: TaskRecord) -> None:
    """Update a task record."""
    with _task_lock:
        _task_store[task.id] = task


def list_tasks(
    skill_id: Optional[str] = None,
    project_id: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    limit: int = 50
) -> List[TaskRecord]:
    """List tasks with optional filters."""
    with _task_lock:
        tasks = list(_task_store.values())

    # Apply filters
    if skill_id:
        tasks = [t for t in tasks if t.skill_id == skill_id]
    if project_id:
        tasks = [t for t in tasks if t.project_id == project_id]
    if status:
        tasks = [t for t in tasks if t.status == status]

    # Sort by created_at descending
    tasks.sort(key=lambda t: t.created_at, reverse=True)

    return tasks[:limit]


# ============================================================================
# BACKGROUND EXECUTION (CELERY + FALLBACK)
# ============================================================================

def get_execution_mode() -> str:
    """Determine the execution mode (celery or thread)."""
    try:
        from celery_app import get_task_mode
        return get_task_mode()
    except ImportError:
        return "thread"


def execute_skill_celery(
    task_id: str,
    skill_id: str,
    payload: Dict[str, Any],
    project_id: Optional[str] = None,
) -> None:
    """
    Queue skill execution via Celery.

    Uses the Celery task queue for true async execution.
    """
    try:
        from tasks import execute_skill
        execute_skill.delay(
            task_id=task_id,
            skill_id=skill_id,
            payload=payload,
            project_id=project_id,
        )
    except Exception as e:
        print(f"[WARN] Celery unavailable, falling back to thread: {e}")
        # Fallback to thread execution
        execute_skill_thread(task_id, skill_id, payload, project_id)


def execute_skill_thread(
    task_id: str,
    skill_id: str,
    payload: Dict[str, Any],
    project_id: Optional[str] = None,
) -> None:
    """
    Execute skill in a background thread (fallback mode).
    """
    def run():
        try:
            from skills.base import skill_registry
            skill = skill_registry.get(skill_id)
            if not skill:
                raise ValueError(f"Skill '{skill_id}' not found")

            context = ExecutionContext(
                task_id=task_id,
                skill_id=skill_id,
                project_id=project_id,
                payload=payload,
            )

            runner = SkillRunner(skill)
            result_task = runner.execute_sync(context)

            # Update in-memory store
            task = get_task(task_id)
            if task:
                task.status = result_task.status
                task.current_stage = result_task.current_stage
                task.progress_percent = result_task.progress_percent
                task.result_data = result_task.result_data
                task.artifacts = result_task.artifacts
                task.started_at = result_task.started_at
                task.completed_at = result_task.completed_at
                task.execution_time_ms = result_task.execution_time_ms
                task.error_message = result_task.error_message
                task.error_traceback = result_task.error_traceback
                update_task(task)

            # Also persist to database
            try:
                from tasks import update_task_status
                status = "success" if result_task.status.value == "success" else "failed"
                update_task_status(
                    task_id,
                    status,
                    result_task.current_stage,
                    result_task.progress_percent,
                    result_task.result_data,
                    result_task.error_message,
                )
            except Exception:
                pass

        except Exception as e:
            task = get_task(task_id)
            if task:
                task.mark_failed(str(e))
                update_task(task)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()


def execute_skill_background(
    skill: AquaSkill,
    context: ExecutionContext,
    task: TaskRecord
) -> None:
    """
    Execute a skill in the background.

    Automatically chooses between Celery and thread execution.
    """
    mode = get_execution_mode()

    if mode == "celery":
        execute_skill_celery(
            task_id=task.id,
            skill_id=context.skill_id,
            payload=context.payload,
            project_id=context.project_id,
        )
    else:
        execute_skill_thread(
            task_id=task.id,
            skill_id=context.skill_id,
            payload=context.payload,
            project_id=context.project_id,
        )


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/trigger", response_model=TriggerResponse)
async def trigger_skill(request: TriggerRequest):
    """
    🚀 THE UNIVERSAL TRIGGER - One Endpoint to Rule Them All

    Execute any registered skill through a single, unified endpoint.

    How it works:
    1. Look up the skill by ID
    2. Validate the payload against the skill's schema
    3. Create execution context with full audit trail
    4. Queue for execution (async) or execute immediately (sync)
    5. Return task_id for status tracking

    Example:
    ```json
    POST /api/orchestrator/trigger
    {
        "skill_id": "hydraulic_calc",
        "project_id": "proj_123",
        "payload": {
            "flow_gpm": 100,
            "pipe_diameter": 2,
            "pipe_length": 50
        },
        "async_mode": true
    }
    ```

    Response:
    ```json
    {
        "task_id": "task_abc123",
        "skill_id": "hydraulic_calc",
        "status": "queued",
        "message": "Task queued for execution"
    }
    ```
    """
    # 1. Find the skill
    skill = skill_registry.get(request.skill_id)
    if not skill:
        raise HTTPException(
            status_code=404,
            detail=f"Skill '{request.skill_id}' not found. Use GET /api/orchestrator/skills for available skills."
        )

    # 2. Create execution context
    task_id = str(uuid.uuid4())[:12]
    context = ExecutionContext(
        task_id=task_id,
        skill_id=request.skill_id,
        project_id=request.project_id,
        user_id=request.user_id,
        payload=request.payload,
        timeout_seconds=request.timeout_seconds,
        metadata=request.metadata,
        parent_task_id=request.parent_task_id,
    )

    # 3. Pre-validate payload (fail fast)
    errors = skill.validate_inputs(request.payload)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Payload validation failed",
                "errors": errors,
                "expected_schema": skill.input_schema.to_json_schema()
            }
        )

    # 4. Create task record (in-memory + database)
    task = TaskRecord(
        id=task_id,
        skill_id=request.skill_id,
        project_id=request.project_id,
        user_id=request.user_id,
        input_params=request.payload,
        metadata=request.metadata,
    )
    store_task(task)

    # Persist to database for audit trail
    try:
        from tasks import create_task_record
        create_task_record(
            task_id=task_id,
            skill_id=request.skill_id,
            project_id=request.project_id,
            input_params=request.payload,
        )
    except Exception as e:
        print(f"[WARN] Could not persist task to database: {e}")

    # 5. Execute
    execution_mode = get_execution_mode()

    if request.async_mode:
        # Queue for background execution
        execute_skill_background(skill, context, task)

        return TriggerResponse(
            task_id=task_id,
            skill_id=request.skill_id,
            status="queued",
            message=f"Task queued. Poll GET /api/orchestrator/tasks/{task_id} for status.",
            queued_at=datetime.utcnow()
        )
    else:
        # Synchronous execution
        runner = SkillRunner(skill)
        result_task = runner.execute_sync(context)
        update_task(result_task)

        return TriggerResponse(
            task_id=task_id,
            skill_id=request.skill_id,
            status=result_task.status.value,
            message=result_task.error_message or "Completed",
            queued_at=task.created_at
        )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    📊 Get Task Status

    Poll this endpoint to track the progress of an async skill execution.

    Returns full task details including:
    - Current status (queued, running, success, failed)
    - Progress percentage
    - Execution time
    - Result data (when completed)
    - Error details (if failed)
    """
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return TaskStatusResponse(
        id=task.id,
        skill_id=task.skill_id,
        status=task.status.value,
        current_stage=task.current_stage,
        progress_percent=task.progress_percent,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        execution_time_ms=task.execution_time_ms,
        result_data=task.result_data,
        error_message=task.error_message,
        artifacts=task.artifacts,
    )


@router.get("/tasks")
async def list_all_tasks(
    skill_id: Optional[str] = None,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """
    📋 List All Tasks

    List all task executions with optional filtering.

    Query Parameters:
    - skill_id: Filter by skill
    - project_id: Filter by project
    - status: Filter by status (queued, running, success, failed)
    - limit: Max results (default 50)
    """
    status_enum = None
    if status:
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    tasks = list_tasks(
        skill_id=skill_id,
        project_id=project_id,
        status=status_enum,
        limit=limit
    )

    return {
        "tasks": [t.to_dict() for t in tasks],
        "total": len(tasks),
        "filters": {
            "skill_id": skill_id,
            "project_id": project_id,
            "status": status,
        }
    }


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    ❌ Cancel a Task

    Cancel a queued or running task.
    Note: Already completed tasks cannot be cancelled.
    """
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task with status '{task.status.value}'"
        )

    task.status = TaskStatus.CANCELLED
    task.completed_at = datetime.utcnow()
    task.current_stage = "cancelled"
    update_task(task)

    return {"message": f"Task {task_id} cancelled", "status": "cancelled"}


@router.get("/skills")
async def list_available_skills():
    """
    📚 List Available Skills

    Returns all registered skills with their metadata and input schemas.
    Use this to discover what skills are available and how to invoke them.

    Each skill includes:
    - ID: The identifier to use in /trigger
    - Name: Human-readable name
    - Description: What the skill does
    - Category: Organizational category
    - Input Schema: JSON Schema for payload validation
    """
    skills = skill_registry.list_all()

    def get_input_schema(s):
        """Safely get input schema from skill."""
        schema = s.input_schema
        if hasattr(schema, 'to_json_schema'):
            return schema.to_json_schema()
        elif isinstance(schema, dict):
            return schema
        else:
            return {"fields": []}

    return {
        "skills": [
            {
                "id": s.metadata.id,
                "name": s.metadata.name,
                "description": s.metadata.description,
                "category": s.metadata.category.value,
                "icon": s.metadata.icon,
                "color": s.metadata.color,
                "version": s.metadata.version,
                "tags": s.metadata.tags,
                "requires_revit": s.metadata.requires_revit,
                "requires_autocad": s.metadata.requires_autocad,
                "input_schema": get_input_schema(s),
            }
            for s in skills
        ],
        "total": len(skills)
    }


@router.get("/skills/{skill_id}")
async def get_skill_details(skill_id: str):
    """
    🔍 Get Skill Details

    Get detailed information about a specific skill including:
    - Full metadata
    - Complete input schema with field definitions
    - Example payload
    """
    skill = skill_registry.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    # Generate example payload from schema
    example_payload = {}
    for field in skill.input_schema.fields:
        if field.default is not None:
            example_payload[field.name] = field.default
        elif field.type.value == "number":
            example_payload[field.name] = 0
        elif field.type.value == "boolean":
            example_payload[field.name] = False
        elif field.type.value == "select" and field.options:
            example_payload[field.name] = field.options[0]["value"]
        else:
            example_payload[field.name] = ""

    return {
        "metadata": skill.metadata.model_dump(),
        "input_schema": {
            "fields": [f.model_dump() for f in skill.input_schema.fields],
            "json_schema": skill.input_schema.to_json_schema(),
        },
        "example_payload": example_payload,
        "trigger_url": f"/api/orchestrator/trigger",
        "example_request": {
            "skill_id": skill_id,
            "project_id": "your_project_id",
            "payload": example_payload,
            "async_mode": True
        }
    }


# ============================================================================
# BATCH EXECUTION
# ============================================================================

class BatchTriggerRequest(BaseModel):
    """Request to execute multiple skills in batch."""
    tasks: List[TriggerRequest] = Field(..., max_length=100)
    parallel: bool = Field(True, description="Execute in parallel (true) or sequential (false)")


@router.post("/batch")
async def batch_trigger(request: BatchTriggerRequest):
    """
    🔄 Batch Trigger - Execute Multiple Skills

    Execute multiple skills in a single request.

    Options:
    - parallel=true: All tasks run concurrently
    - parallel=false: Tasks run sequentially

    Returns task IDs for all queued tasks.
    """
    results = []

    for trigger_req in request.tasks:
        # Find skill
        skill = skill_registry.get(trigger_req.skill_id)
        if not skill:
            results.append({
                "skill_id": trigger_req.skill_id,
                "status": "error",
                "message": f"Skill not found"
            })
            continue

        # Create task
        task_id = str(uuid.uuid4())[:12]
        context = ExecutionContext(
            task_id=task_id,
            skill_id=trigger_req.skill_id,
            project_id=trigger_req.project_id,
            user_id=trigger_req.user_id,
            payload=trigger_req.payload,
            timeout_seconds=trigger_req.timeout_seconds,
            metadata=trigger_req.metadata,
        )

        task = TaskRecord(
            id=task_id,
            skill_id=trigger_req.skill_id,
            project_id=trigger_req.project_id,
            user_id=trigger_req.user_id,
            input_params=trigger_req.payload,
        )
        store_task(task)

        if request.parallel:
            # Queue for background execution
            thread = threading.Thread(
                target=execute_skill_background,
                args=(skill, context, task),
                daemon=True
            )
            thread.start()
        else:
            # Execute synchronously
            runner = SkillRunner(skill)
            result_task = runner.execute_sync(context)
            update_task(result_task)

        results.append({
            "skill_id": trigger_req.skill_id,
            "task_id": task_id,
            "status": "queued" if request.parallel else task.status.value,
        })

    return {
        "tasks": results,
        "total": len(results),
        "mode": "parallel" if request.parallel else "sequential"
    }
