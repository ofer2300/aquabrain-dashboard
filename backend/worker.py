"""
AquaBrain Worker Module
=======================
Async task processing for the engineering pipeline.

Supports TWO modes:
1. CELERY MODE: When celery is installed, uses Celery/Redis for distributed processing
2. THREAD MODE: When celery is NOT installed, runs tasks in background threads

This allows the system to work in development without Redis/Celery installed.

Run Celery worker with: celery -A worker worker --loglevel=info
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# CELERY MODE (Optional - only if celery is installed)
# =============================================================================
CELERY_AVAILABLE = False
celery = None

try:
    from celery import Celery
    from celery.signals import task_prerun, task_postrun, task_failure
    CELERY_AVAILABLE = True
    print("[WORKER] Celery module available")
except ImportError:
    print("[WORKER] Celery not installed - using THREAD MODE (no Redis/Celery required)")

# Initialize Celery ONLY if available
if CELERY_AVAILABLE:
    # Redis configuration (with fallback for dev without Redis)
    # Using port 6380 to avoid conflict with Windows/Docker Redis on 6379
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6380/0")

    # Check if Redis is available, fallback to filesystem broker for dev
    try:
        import redis
        r = redis.from_url(REDIS_URL)
        r.ping()
        BROKER_URL = REDIS_URL
        BACKEND_URL = REDIS_URL
        print(f"[WORKER] Connected to Redis: {REDIS_URL}")
    except Exception as e:
        # Fallback to filesystem for development without Redis
        BROKER_URL = "filesystem://"
        BACKEND_URL = "db+sqlite:///celery_results.db"
        # Create required directories for filesystem broker
        os.makedirs("./broker/out", exist_ok=True)
        os.makedirs("./broker/processed", exist_ok=True)
        print(f"[WORKER] Redis not available, using filesystem broker: {e}")

    # Initialize Celery
    celery = Celery(
        "aquabrain",
        broker=BROKER_URL,
        backend=BACKEND_URL,
    )

    # Celery configuration
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=600,  # 10 minute max per task
        result_expires=86400,  # Results expire after 24 hours
        # Filesystem broker settings
        broker_transport_options={
            "data_folder_in": "./broker/out",
            "data_folder_out": "./broker/out",
            "data_folder_processed": "./broker/processed",
        },
    )


def get_db_session():
    """Get database session."""
    from models import SessionLocal
    return SessionLocal()


def update_run_status(
    run_id: str,
    status: str,
    stage: str = None,
    progress: int = None,
    error: str = None,
    result_data: dict = None,
):
    """Update project run status in database."""
    from models import ProjectRun

    db = get_db_session()
    try:
        run = db.query(ProjectRun).filter(ProjectRun.id == run_id).first()
        if not run:
            print(f"[ERROR] Run {run_id} not found in database")
            return

        run.status = status
        if stage:
            run.current_stage = stage
        if progress is not None:
            run.progress_percent = progress
        if error:
            run.error_message = error

        if status == "PROCESSING" and not run.started_at:
            run.started_at = datetime.utcnow()

        if status == "COMPLETED" or status == "FAILED":
            run.completed_at = datetime.utcnow()
            if run.started_at:
                run.duration_seconds = (run.completed_at - run.started_at).total_seconds()

        if result_data:
            if "traffic_light" in result_data:
                run.traffic_light_json = json.dumps(result_data["traffic_light"])
            if "metrics" in result_data:
                run.metrics_json = json.dumps(result_data["metrics"])
            if "geometry_summary" in result_data:
                run.geometry_json = json.dumps(result_data["geometry_summary"])
            if "routing_summary" in result_data:
                run.routing_json = json.dumps(result_data["routing_summary"])
            if "hydraulic_summary" in result_data:
                run.hydraulic_json = json.dumps(result_data["hydraulic_summary"])

        db.commit()
        print(f"[DB] Updated run {run_id}: status={status}, stage={stage}, progress={progress}%")

    except Exception as e:
        print(f"[ERROR] Failed to update run {run_id}: {e}")
        db.rollback()
    finally:
        db.close()


def _run_engineering_job_impl(
    run_id: str,
    project_id: str,
    hazard_class: str = "ordinary_1",
    notes: str = "",
    revit_version: str = "auto",
) -> Dict[str, Any]:
    """
    Async Celery task for the engineering pipeline.

    This task:
    1. Updates DB status to PROCESSING
    2. Runs the full engineering pipeline (Bridge -> Logic -> Traffic Light)
    3. Updates DB status to COMPLETED with results

    Args:
        run_id: Unique run identifier
        project_id: Project identifier
        hazard_class: NFPA 13 hazard classification
        notes: Special instructions

    Returns:
        Complete engineering result dictionary
    """
    print(f"\n{'='*60}")
    print(f"[TASK] Starting engineering job: {run_id}")
    print(f"[TASK] Project: {project_id}, Hazard: {hazard_class}")
    print(f"{'='*60}\n")

    # Update status to PROCESSING
    update_run_status(
        run_id=run_id,
        status="PROCESSING",
        stage="initializing",
        progress=5,
    )

    try:
        # Import orchestrator
        from services.orchestrator import EngineeringOrchestrator

        # Create orchestrator instance
        orchestrator = EngineeringOrchestrator()

        # Define progress callback to update DB
        def on_progress(progress_info):
            stage_map = {
                "pending": 0,
                "extracting": 15,
                "voxelizing": 30,
                "routing": 45,
                "calculating": 60,
                "validating": 75,
                "generating": 85,
                "signaling": 95,
                "completed": 100,
            }
            stage_name = progress_info.stage.value
            progress_pct = stage_map.get(stage_name, progress_info.progress_percent)

            update_run_status(
                run_id=run_id,
                status="PROCESSING",
                stage=stage_name,
                progress=progress_pct,
            )

        # Add progress callback
        orchestrator.progress_callbacks.append(on_progress)

        # Run the async pipeline in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                orchestrator.run_pipeline(
                    project_id=project_id,
                    hazard_class=hazard_class,
                    instructions=notes,
                )
            )
        finally:
            loop.close()

        # Convert result to dict
        result_dict = result.to_dict()

        # Extract metrics for storage
        traffic = result_dict.get("traffic_light", {})
        metrics = traffic.get("metrics", {})

        # Update DB with completed status and results
        update_run_status(
            run_id=run_id,
            status="COMPLETED",
            stage="completed",
            progress=100,
            result_data={
                "traffic_light": traffic,
                "metrics": metrics,
                "geometry_summary": result_dict.get("geometry_summary"),
                "routing_summary": result_dict.get("routing_summary"),
                "hydraulic_summary": result_dict.get("hydraulic_summary"),
            },
        )

        print(f"\n[TASK] Completed: {run_id}")
        print(f"[TASK] Traffic Light: {traffic.get('status', 'UNKNOWN')}")
        print(f"[TASK] Duration: {result_dict.get('duration_seconds', 0):.2f}s\n")

        return result_dict

    except Exception as e:
        error_msg = str(e)
        print(f"\n[TASK] FAILED: {run_id}")
        print(f"[TASK] Error: {error_msg}\n")

        # Update DB with failed status
        update_run_status(
            run_id=run_id,
            status="FAILED",
            stage="failed",
            progress=0,
            error=error_msg,
            result_data={
                "traffic_light": {
                    "status": "RED",
                    "message": "Task failed",
                    "details": [error_msg],
                },
            },
        )

        # Re-raise to mark task as failed
        raise


# =============================================================================
# PUBLIC WRAPPER - Works in BOTH Celery and Thread mode
# =============================================================================
def run_engineering_job(
    run_id: str,
    project_id: str,
    hazard_class: str = "ordinary_1",
    notes: str = "",
    revit_version: str = "auto",
) -> Dict[str, Any]:
    """
    Public wrapper for engineering job.

    This function is called from main.py and works in both modes:
    - CELERY MODE: Would dispatch to Celery task (if running with worker)
    - THREAD MODE: Runs directly in current thread

    The main.py already wraps this in a background thread, so we just run directly.
    """
    return _run_engineering_job_impl(
        run_id=run_id,
        project_id=project_id,
        hazard_class=hazard_class,
        notes=notes,
        revit_version=revit_version,
    )


def create_run(
    project_id: str,
    hazard_class: str = "ordinary_1",
    notes: str = "",
) -> str:
    """
    Create a new run record in the database.

    Returns:
        run_id: Unique identifier for the run
    """
    from models import ProjectRun, init_db

    # Ensure DB is initialized
    init_db()

    run_id = f"RUN-{uuid.uuid4().hex[:12].upper()}"

    db = get_db_session()
    try:
        run = ProjectRun(
            id=run_id,
            project_id=project_id,
            status="QUEUED",
            current_stage="queued",
            progress_percent=0,
            hazard_class=hazard_class,
            notes=notes,
        )
        db.add(run)
        db.commit()
        print(f"[DB] Created run: {run_id}")
        return run_id
    except Exception as e:
        print(f"[ERROR] Failed to create run: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def get_run_status(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Get current status of a run from database.

    Returns:
        Run data as dictionary, or None if not found
    """
    from models import ProjectRun

    db = get_db_session()
    try:
        run = db.query(ProjectRun).filter(ProjectRun.id == run_id).first()
        if run:
            return run.to_dict()
        return None
    finally:
        db.close()


def get_project_history(project_id: str, limit: int = 10) -> list:
    """
    Get run history for a project.

    Returns:
        List of run dictionaries, most recent first
    """
    from models import ProjectRun

    db = get_db_session()
    try:
        runs = (
            db.query(ProjectRun)
            .filter(ProjectRun.project_id == project_id)
            .order_by(ProjectRun.created_at.desc())
            .limit(limit)
            .all()
        )
        return [run.to_dict() for run in runs]
    finally:
        db.close()


# =============================================================================
# CELERY SIGNALS (only if Celery is available)
# =============================================================================
if CELERY_AVAILABLE:
    @task_prerun.connect
    def task_started(sender=None, task_id=None, task=None, args=None, **kwargs):
        """Log when task starts."""
        print(f"[SIGNAL] Task started: {task_id}")

    @task_postrun.connect
    def task_completed(sender=None, task_id=None, task=None, retval=None, state=None, **kwargs):
        """Log when task completes."""
        print(f"[SIGNAL] Task completed: {task_id} (state={state})")

    @task_failure.connect
    def task_failed(sender=None, task_id=None, exception=None, **kwargs):
        """Log when task fails."""
        print(f"[SIGNAL] Task failed: {task_id} (error={exception})")


if __name__ == "__main__":
    # Test the worker
    print("AquaBrain Worker Module")
    print("=======================")
    if CELERY_AVAILABLE:
        print(f"Mode: CELERY")
        print(f"Broker: {BROKER_URL}")
        print(f"Backend: {BACKEND_URL}")
        print("\nTo start worker: celery -A worker worker --loglevel=info")
    else:
        print(f"Mode: THREAD (no Celery/Redis required)")
        print("Tasks run in background threads within the main API process.")
        print("\nTo install Celery for distributed processing:")
        print("  pip install celery redis")
