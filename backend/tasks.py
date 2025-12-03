"""
AquaBrain Celery Tasks
======================
Background task definitions for the event-driven architecture.

Tasks:
- execute_engineering_workflow: Full autopilot pipeline
- execute_skill: Universal skill execution
- health_check: Periodic health monitoring
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime
from typing import Dict, Any, Optional
import traceback
import json

from models import SessionLocal, SkillExecution, ProjectRun

logger = get_task_logger(__name__)


# ============================================================================
# DATABASE HELPERS
# ============================================================================

def update_task_status(
    task_id: str,
    status: str,
    stage: str = None,
    progress: int = None,
    result_data: Dict = None,
    error_message: str = None,
):
    """Update task status in the database."""
    db = SessionLocal()
    try:
        # Try SkillExecution first
        task = db.query(SkillExecution).filter(SkillExecution.id == task_id).first()
        if task:
            task.status = status
            if stage:
                task.current_stage = stage
            if progress is not None:
                task.progress_percent = progress
            if result_data:
                task.set_result_data(result_data)
            if error_message:
                task.error_message = error_message
            if status in ["success", "failed", "cancelled"]:
                task.completed_at = datetime.utcnow()
                if task.started_at:
                    task.execution_time_ms = int(
                        (task.completed_at - task.started_at).total_seconds() * 1000
                    )
            db.commit()
            return

        # Try ProjectRun
        run = db.query(ProjectRun).filter(ProjectRun.id == task_id).first()
        if run:
            run.status = status.upper()
            if stage:
                run.current_stage = stage
            if progress is not None:
                run.progress_percent = progress
            if result_data:
                run.set_metrics(result_data)
            if error_message:
                run.error_message = error_message
            if status in ["completed", "failed"]:
                run.completed_at = datetime.utcnow()
                if run.started_at:
                    run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
            db.commit()

    finally:
        db.close()


def create_task_record(
    task_id: str,
    skill_id: str,
    project_id: str = None,
    input_params: Dict = None,
) -> SkillExecution:
    """Create a new task record in the database."""
    db = SessionLocal()
    try:
        task = SkillExecution(
            id=task_id,
            skill_id=skill_id,
            project_id=project_id,
            status="queued",
            current_stage="queued",
            progress_percent=0,
        )
        if input_params:
            task.set_input_params(input_params)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    finally:
        db.close()


# ============================================================================
# CELERY TASKS
# ============================================================================

@shared_task(
    name="tasks.execute_engineering_workflow",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
)
def execute_engineering_workflow(
    self,
    task_id: str,
    project_id: str,
    hazard_class: str = "ordinary_1",
    notes: str = "",
    revit_version: str = "auto",
):
    """
    Execute the full engineering automation pipeline.

    This is the "Tesla of Engineering" - one task that does everything:
    1. Extract geometry from Revit
    2. Voxelize the space
    3. Run A* pathfinding
    4. Calculate hydraulics
    5. Validate NFPA 13
    6. Generate LOD 500 model
    7. Return Traffic Light status

    Args:
        task_id: Unique task identifier
        project_id: Project to process
        hazard_class: NFPA 13 hazard classification
        notes: Engineering notes
        revit_version: Target Revit version
    """
    logger.info(f"Starting engineering workflow for task {task_id}")

    try:
        # Update status to PROCESSING
        update_task_status(task_id, "PROCESSING", "starting", 5)

        # Import orchestrator (lazy to avoid circular imports)
        from services.orchestrator import run_engineering_process_sync

        # Execute the pipeline
        update_task_status(task_id, "PROCESSING", "executing", 10)

        result = run_engineering_process_sync(
            project_id=project_id,
            hazard_class=hazard_class,
            notes=notes,
            revit_version=revit_version,
            mock_mode=True,  # Use mock mode for now
        )

        # Store result
        update_task_status(
            task_id,
            "COMPLETED",
            "completed",
            100,
            result_data=result,
        )

        logger.info(f"Engineering workflow completed for task {task_id}")
        return result

    except Exception as e:
        logger.error(f"Engineering workflow failed for task {task_id}: {e}")
        update_task_status(
            task_id,
            "FAILED",
            "failed",
            0,
            error_message=str(e),
        )
        raise


@shared_task(
    name="tasks.execute_skill",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def execute_skill(
    self,
    task_id: str,
    skill_id: str,
    payload: Dict[str, Any],
    project_id: str = None,
):
    """
    Execute any registered skill via the Universal Orchestrator.

    This is the generic skill execution task that can run any skill
    from the skill registry.

    Args:
        task_id: Unique task identifier
        skill_id: ID of the skill to execute
        payload: Input parameters for the skill
        project_id: Optional project context
    """
    logger.info(f"Executing skill {skill_id} for task {task_id}")

    try:
        # Update status
        update_task_status(task_id, "running", "executing", 10)

        # Get skill from registry
        from skills.base import skill_registry
        skill = skill_registry.get(skill_id)

        if not skill:
            raise ValueError(f"Skill '{skill_id}' not found in registry")

        # Execute skill
        from core.skill_interface import ExecutionContext, SkillRunner

        context = ExecutionContext(
            task_id=task_id,
            skill_id=skill_id,
            project_id=project_id,
            payload=payload,
        )

        runner = SkillRunner(skill)
        result_task = runner.execute_sync(context)

        # Store result
        if result_task.status.value == "success":
            update_task_status(
                task_id,
                "success",
                "completed",
                100,
                result_data={
                    "output": result_task.result_data,
                    "artifacts": result_task.artifacts,
                },
            )
        else:
            update_task_status(
                task_id,
                "failed",
                "failed",
                0,
                error_message=result_task.error_message,
            )

        logger.info(f"Skill {skill_id} completed for task {task_id}")
        return result_task.to_dict()

    except Exception as e:
        logger.error(f"Skill execution failed for task {task_id}: {e}")
        update_task_status(
            task_id,
            "failed",
            "failed",
            0,
            error_message=str(e),
        )
        raise


@shared_task(name="tasks.health_check")
def health_check():
    """
    Periodic health check task.

    Verifies system components are operational.
    """
    logger.info("Running health check...")

    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
    }

    # Check database
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        status["checks"]["database"] = "ok"
    except Exception as e:
        status["checks"]["database"] = f"error: {str(e)}"

    # Check skill registry
    try:
        from skills.base import skill_registry
        count = len(skill_registry.list_all())
        status["checks"]["skills"] = f"ok ({count} skills)"
    except Exception as e:
        status["checks"]["skills"] = f"error: {str(e)}"

    logger.info(f"Health check completed: {status}")
    return status


# ============================================================================
# FALLBACK: Thread-based execution (when Redis unavailable)
# ============================================================================

import threading
from queue import Queue

_task_queue: Queue = Queue()
_worker_running = False


def start_fallback_worker():
    """Start the fallback thread worker."""
    global _worker_running

    if _worker_running:
        return

    def worker():
        global _worker_running
        _worker_running = True
        while True:
            try:
                task_func, args, kwargs = _task_queue.get(timeout=1)
                try:
                    task_func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Fallback worker error: {e}")
            except:
                pass

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def submit_task_fallback(task_func, *args, **kwargs):
    """Submit a task to the fallback queue."""
    start_fallback_worker()
    _task_queue.put((task_func, args, kwargs))
