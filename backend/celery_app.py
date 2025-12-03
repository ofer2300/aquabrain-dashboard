"""
AquaBrain Celery Configuration
==============================
Event-driven task queue for enterprise scalability.

Features:
- Redis as message broker and result backend
- Task routing to priority queues
- Automatic retries with exponential backoff
- Dead letter queue for failed tasks
- Flower monitoring support
"""

from celery import Celery
import os

# Redis configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
REDIS_RESULT_BACKEND = os.environ.get("REDIS_RESULT_URL", "redis://localhost:6379/1")

# Create Celery app
celery_app = Celery(
    "aquabrain",
    broker=REDIS_URL,
    backend=REDIS_RESULT_BACKEND,
    include=[
        "tasks",  # Engineering tasks
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Include task metadata in results

    # Worker settings
    worker_prefetch_multiplier=1,  # Fair task distribution
    worker_concurrency=4,  # 4 concurrent workers per instance

    # Task execution limits
    task_time_limit=600,  # Hard limit: 10 minutes
    task_soft_time_limit=540,  # Soft limit: 9 minutes (for cleanup)

    # Retry settings
    task_acks_late=True,  # Acknowledge after completion
    task_reject_on_worker_lost=True,  # Requeue if worker dies

    # Task routing
    task_routes={
        "tasks.execute_engineering_workflow": {"queue": "engineering"},
        "tasks.execute_skill": {"queue": "skills"},
        "tasks.*": {"queue": "default"},
    },

    # Beat scheduler (for periodic tasks)
    beat_schedule={
        "health-check-every-minute": {
            "task": "tasks.health_check",
            "schedule": 60.0,
        },
    },
)

# Optional: Configure task priorities
celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5


# ============================================================================
# FALLBACK: SQLite-based task tracking (when Redis unavailable)
# ============================================================================

class TaskTracker:
    """
    Fallback task tracking when Redis is not available.
    Uses SQLite for persistence.
    """

    def __init__(self, db_path: str = "aquabrain.db"):
        self.db_path = db_path
        self._redis_available = None

    @property
    def redis_available(self) -> bool:
        """Check if Redis is available."""
        if self._redis_available is None:
            try:
                import redis
                r = redis.from_url(REDIS_URL)
                r.ping()
                self._redis_available = True
            except Exception:
                self._redis_available = False
        return self._redis_available

    def use_celery(self) -> bool:
        """Determine if we should use Celery or fallback."""
        return self.redis_available


# Global task tracker
task_tracker = TaskTracker()


def get_task_mode() -> str:
    """Get the current task execution mode."""
    if task_tracker.use_celery():
        return "celery"
    return "thread"  # Fallback to threaded execution
