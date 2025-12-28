"""
AquaBrain Scheduler V1.0
========================
The Orchestrator - Schedule skills to run automatically.

Features:
- Cron-based scheduling
- One-time scheduled execution
- Recurring tasks
- Task history and monitoring
"""

from __future__ import annotations
import sqlite3
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import BaseModel, Field
from enum import Enum
import threading
import time
from croniter import croniter  # pip install croniter

from skills.base import skill_registry, ExecutionResult, ExecutionStatus


class ScheduleType(str, Enum):
    """Type of schedule."""
    ONCE = "once"           # Run once at specified time
    CRON = "cron"           # Cron expression
    INTERVAL = "interval"   # Every X minutes/hours


class ScheduledTask(BaseModel):
    """A scheduled skill execution."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    skill_id: str
    project_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    # Schedule
    schedule_type: ScheduleType = ScheduleType.CRON
    cron_expression: Optional[str] = None  # e.g., "0 8 * * 0" (Sunday 8am)
    run_at: Optional[datetime] = None  # For ONCE type
    interval_minutes: Optional[int] = None  # For INTERVAL type
    # Input data
    inputs: Dict[str, Any] = Field(default_factory=dict)
    # State
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    # Creator
    created_by: str = "system"


class TaskExecution(BaseModel):
    """Record of a task execution."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    skill_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class TaskScheduler:
    """
    Manages scheduled task execution.
    Uses SQLite for persistence and threading for the scheduler loop.
    """

    DB_PATH = Path(__file__).parent.parent / "data" / "scheduler.db"

    def __init__(self):
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running = False

    def _init_db(self):
        """Initialize the SQLite database."""
        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()

        # Scheduled tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                project_id TEXT,
                name TEXT NOT NULL,
                description TEXT,
                schedule_type TEXT NOT NULL,
                cron_expression TEXT,
                run_at TEXT,
                interval_minutes INTEGER,
                inputs TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                last_run TEXT,
                next_run TEXT,
                run_count INTEGER DEFAULT 0,
                created_by TEXT
            )
        """)

        # Execution history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_executions (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                status TEXT,
                result TEXT,
                error TEXT,
                duration_ms INTEGER,
                FOREIGN KEY (task_id) REFERENCES scheduled_tasks(id)
            )
        """)

        conn.commit()
        conn.close()

    def _calculate_next_run(self, task: ScheduledTask) -> Optional[datetime]:
        """Calculate the next run time for a task."""
        now = datetime.now()

        if task.schedule_type == ScheduleType.ONCE:
            if task.run_at and task.run_at > now:
                return task.run_at
            return None  # Already passed

        elif task.schedule_type == ScheduleType.CRON:
            if task.cron_expression:
                try:
                    cron = croniter(task.cron_expression, now)
                    return cron.get_next(datetime)
                except:
                    return None

        elif task.schedule_type == ScheduleType.INTERVAL:
            if task.interval_minutes:
                base_time = task.last_run or now
                return base_time + timedelta(minutes=task.interval_minutes)

        return None

    def create_task(self, task: ScheduledTask) -> ScheduledTask:
        """Create a new scheduled task."""
        task.next_run = self._calculate_next_run(task)

        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO scheduled_tasks
            (id, skill_id, project_id, name, description, schedule_type,
             cron_expression, run_at, interval_minutes, inputs, is_active,
             created_at, last_run, next_run, run_count, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.id, task.skill_id, task.project_id, task.name, task.description,
            task.schedule_type.value, task.cron_expression,
            task.run_at.isoformat() if task.run_at else None,
            task.interval_minutes, json.dumps(task.inputs), int(task.is_active),
            task.created_at.isoformat(),
            task.last_run.isoformat() if task.last_run else None,
            task.next_run.isoformat() if task.next_run else None,
            task.run_count, task.created_by
        ))

        conn.commit()
        conn.close()

        return task

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_task(row)
        return None

    def list_tasks(self, active_only: bool = False) -> List[ScheduledTask]:
        """List all scheduled tasks."""
        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()

        if active_only:
            cursor.execute("SELECT * FROM scheduled_tasks WHERE is_active = 1 ORDER BY next_run")
        else:
            cursor.execute("SELECT * FROM scheduled_tasks ORDER BY created_at DESC")

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_task(row) for row in rows]

    def _row_to_task(self, row) -> ScheduledTask:
        """Convert DB row to ScheduledTask."""
        return ScheduledTask(
            id=row[0],
            skill_id=row[1],
            project_id=row[2],
            name=row[3],
            description=row[4],
            schedule_type=ScheduleType(row[5]),
            cron_expression=row[6],
            run_at=datetime.fromisoformat(row[7]) if row[7] else None,
            interval_minutes=row[8],
            inputs=json.loads(row[9]) if row[9] else {},
            is_active=bool(row[10]),
            created_at=datetime.fromisoformat(row[11]) if row[11] else datetime.now(),
            last_run=datetime.fromisoformat(row[12]) if row[12] else None,
            next_run=datetime.fromisoformat(row[13]) if row[13] else None,
            run_count=row[14],
            created_by=row[15] or "system"
        )

    def update_task(self, task: ScheduledTask) -> bool:
        """Update a task."""
        task.next_run = self._calculate_next_run(task)

        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE scheduled_tasks SET
                name = ?, description = ?, schedule_type = ?,
                cron_expression = ?, run_at = ?, interval_minutes = ?,
                inputs = ?, is_active = ?, next_run = ?
            WHERE id = ?
        """, (
            task.name, task.description, task.schedule_type.value,
            task.cron_expression,
            task.run_at.isoformat() if task.run_at else None,
            task.interval_minutes, json.dumps(task.inputs),
            int(task.is_active),
            task.next_run.isoformat() if task.next_run else None,
            task.id
        ))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()

        cursor.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
        success = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return success

    def execute_task(self, task: ScheduledTask) -> TaskExecution:
        """Execute a scheduled task."""
        execution = TaskExecution(
            task_id=task.id,
            skill_id=task.skill_id,
            started_at=datetime.now(),
            status=ExecutionStatus.RUNNING
        )

        # Get the skill
        skill = skill_registry.get(task.skill_id)
        if not skill:
            execution.status = ExecutionStatus.FAILED
            execution.error = f"Skill not found: {task.skill_id}"
            execution.completed_at = datetime.now()
            self._save_execution(execution)
            return execution

        # Execute
        result = skill.safe_execute(task.inputs)

        # Update execution record
        execution.status = result.status
        execution.completed_at = datetime.now()
        execution.duration_ms = result.duration_ms
        execution.result = result.output
        execution.error = result.error

        # Save execution
        self._save_execution(execution)

        # Update task
        task.last_run = execution.started_at
        task.run_count += 1
        task.next_run = self._calculate_next_run(task)

        # Deactivate one-time tasks
        if task.schedule_type == ScheduleType.ONCE:
            task.is_active = False

        self.update_task(task)

        return execution

    def _save_execution(self, execution: TaskExecution):
        """Save execution record to database."""
        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO task_executions
            (id, task_id, skill_id, started_at, completed_at, status, result, error, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution.id, execution.task_id, execution.skill_id,
            execution.started_at.isoformat(),
            execution.completed_at.isoformat() if execution.completed_at else None,
            execution.status.value,
            json.dumps(execution.result) if execution.result else None,
            execution.error, execution.duration_ms
        ))

        conn.commit()
        conn.close()

    def get_task_history(self, task_id: str, limit: int = 10) -> List[TaskExecution]:
        """Get execution history for a task."""
        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM task_executions
            WHERE task_id = ?
            ORDER BY started_at DESC
            LIMIT ?
        """, (task_id, limit))

        rows = cursor.fetchall()
        conn.close()

        executions = []
        for row in rows:
            executions.append(TaskExecution(
                id=row[0],
                task_id=row[1],
                skill_id=row[2],
                started_at=datetime.fromisoformat(row[3]) if row[3] else datetime.now(),
                completed_at=datetime.fromisoformat(row[4]) if row[4] else None,
                status=ExecutionStatus(row[5]) if row[5] else ExecutionStatus.PENDING,
                result=json.loads(row[6]) if row[6] else None,
                error=row[7],
                duration_ms=row[8]
            ))

        return executions

    def get_due_tasks(self) -> List[ScheduledTask]:
        """Get tasks that are due for execution."""
        now = datetime.now()
        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM scheduled_tasks
            WHERE is_active = 1 AND next_run IS NOT NULL AND next_run <= ?
        """, (now.isoformat(),))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_task(row) for row in rows]

    def _scheduler_loop(self):
        """Background loop that checks and executes due tasks."""
        while self._running:
            try:
                due_tasks = self.get_due_tasks()
                for task in due_tasks:
                    print(f"[Scheduler] Executing task: {task.name} ({task.id})")
                    self.execute_task(task)
            except Exception as e:
                print(f"[Scheduler] Error: {e}")

            # Check every 30 seconds
            time.sleep(30)

    def start(self):
        """Start the scheduler background thread."""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return

        self._running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        print("[Scheduler] Started")

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        print("[Scheduler] Stopped")


# Global scheduler instance
task_scheduler = TaskScheduler()


# ============================================================================
# AUTO-REGISTER SYSTEM JOBS
# ============================================================================

def register_auto_sign_job():
    """
    Register Skill #501 Auto-Sign job to run every 2 minutes.
    Active Listening Mode for email declarations.
    """
    AUTO_SIGN_TASK_ID = "auto_sign_501_monitor"

    # Check if already exists
    existing = task_scheduler.get_task(AUTO_SIGN_TASK_ID)
    if existing:
        print(f"[Scheduler] Auto-Sign job already registered: {existing.id}")
        return existing

    # Create the auto-sign monitoring task
    auto_sign_task = ScheduledTask(
        id=AUTO_SIGN_TASK_ID,
        skill_id="skill_501_auto_sign",
        name="🔥 Auto-Sign Declaration Monitor",
        description="Polls Gmail every 2 minutes for declaration emails to auto-sign",
        schedule_type=ScheduleType.INTERVAL,
        interval_minutes=2,  # Every 2 minutes
        inputs={
            "mode": "poll",
            "engineer_name": "נימרוד עופר",
            "id_number": "025181967",
            "project_id": "auto_signed",
            "auto_reply": True,
        },
        is_active=True,
        created_by="system_v6",
    )

    task_scheduler.create_task(auto_sign_task)
    print(f"[Scheduler] 🔥 Auto-Sign job registered: every 2 minutes")
    return auto_sign_task


def register_virtual_engineer_job():
    """
    Register Skill #601 Virtual Senior Engineer job to run every 15 minutes.
    24/7 Watchdog for calendar monitoring and meeting preparation.
    """
    VIRTUAL_ENGINEER_TASK_ID = "virtual_engineer_601_monitor"

    # Check if already exists
    existing = task_scheduler.get_task(VIRTUAL_ENGINEER_TASK_ID)
    if existing:
        print(f"[Scheduler] Virtual Engineer job already registered: {existing.id}")
        return existing

    # Create the virtual engineer monitoring task
    virtual_engineer_task = ScheduledTask(
        id=VIRTUAL_ENGINEER_TASK_ID,
        skill_id="skill_601_virtual_engineer",
        name="👑 Virtual Senior Engineer 24/7",
        description="Monitors calendar every 15 minutes, prepares meeting briefings automatically",
        schedule_type=ScheduleType.INTERVAL,
        interval_minutes=15,  # Every 15 minutes
        inputs={
            "mode": "auto",
            "hours_ahead": 24,
            "send_notification": True,
        },
        is_active=True,
        created_by="system_v7",
    )

    task_scheduler.create_task(virtual_engineer_task)
    print(f"[Scheduler] 👑 Virtual Engineer job registered: every 15 minutes")
    return virtual_engineer_task


def register_email_cockpit_polling_job():
    """
    Register Skill #701 Email Cockpit polling job to run every 2 minutes.
    Polls Gmail/Outlook for new emails and processes them.
    """
    EMAIL_POLL_TASK_ID = "email_cockpit_701_poll"

    # Check if already exists
    existing = task_scheduler.get_task(EMAIL_POLL_TASK_ID)
    if existing:
        print(f"[Scheduler] Email Cockpit polling job already registered: {existing.id}")
        return existing

    # Create the email polling task
    email_poll_task = ScheduledTask(
        id=EMAIL_POLL_TASK_ID,
        skill_id="701",
        name="✉️ Email Cockpit - Poll Inbox",
        description="Polls Gmail/Outlook every 2 minutes for new emails",
        schedule_type=ScheduleType.INTERVAL,
        interval_minutes=2,  # Every 2 minutes
        inputs={
            "action": "poll",
        },
        is_active=True,
        created_by="system_v8",
    )

    task_scheduler.create_task(email_poll_task)
    print(f"[Scheduler] ✉️ Email Cockpit polling job registered: every 2 minutes")
    return email_poll_task


def register_golden_hours_noon_job():
    """
    Register Skill #701 Golden Hours 12:00 trigger.
    Shows the Focus Mode Dashboard at noon.
    """
    GOLDEN_NOON_TASK_ID = "email_cockpit_701_golden_noon"

    # Check if already exists
    existing = task_scheduler.get_task(GOLDEN_NOON_TASK_ID)
    if existing:
        print(f"[Scheduler] Golden Hours (12:00) job already registered: {existing.id}")
        return existing

    # Create the golden hour noon task (cron: 0 12 * * *)
    golden_noon_task = ScheduledTask(
        id=GOLDEN_NOON_TASK_ID,
        skill_id="701",
        name="🌟 Golden Hour 12:00 - Email Dashboard",
        description="Triggers Email Focus Mode Dashboard at 12:00",
        schedule_type=ScheduleType.CRON,
        cron_expression="0 12 * * *",  # Every day at 12:00
        inputs={
            "action": "dashboard",
        },
        is_active=True,
        created_by="system_v8",
    )

    task_scheduler.create_task(golden_noon_task)
    print(f"[Scheduler] 🌟 Golden Hours (12:00) job registered")
    return golden_noon_task


def register_golden_hours_afternoon_job():
    """
    Register Skill #701 Golden Hours 16:00 trigger.
    Shows the Focus Mode Dashboard in the afternoon.
    """
    GOLDEN_AFTERNOON_TASK_ID = "email_cockpit_701_golden_afternoon"

    # Check if already exists
    existing = task_scheduler.get_task(GOLDEN_AFTERNOON_TASK_ID)
    if existing:
        print(f"[Scheduler] Golden Hours (16:00) job already registered: {existing.id}")
        return existing

    # Create the golden hour afternoon task (cron: 0 16 * * *)
    golden_afternoon_task = ScheduledTask(
        id=GOLDEN_AFTERNOON_TASK_ID,
        skill_id="701",
        name="🌟 Golden Hour 16:00 - Email Dashboard",
        description="Triggers Email Focus Mode Dashboard at 16:00",
        schedule_type=ScheduleType.CRON,
        cron_expression="0 16 * * *",  # Every day at 16:00
        inputs={
            "action": "dashboard",
        },
        is_active=True,
        created_by="system_v8",
    )

    task_scheduler.create_task(golden_afternoon_task)
    print(f"[Scheduler] 🌟 Golden Hours (16:00) job registered")
    return golden_afternoon_task


def initialize_scheduled_jobs():
    """Initialize all system scheduled jobs on startup."""
    print("[Scheduler] Initializing system jobs...")

    # Register Auto-Sign Skill #501
    try:
        register_auto_sign_job()
    except Exception as e:
        print(f"[Scheduler] Warning: Could not register Auto-Sign job: {e}")

    # Register Virtual Senior Engineer Skill #601
    try:
        register_virtual_engineer_job()
    except Exception as e:
        print(f"[Scheduler] Warning: Could not register Virtual Engineer job: {e}")

    # Register Email Cockpit Skill #701 - Polling
    try:
        register_email_cockpit_polling_job()
    except Exception as e:
        print(f"[Scheduler] Warning: Could not register Email Cockpit polling job: {e}")

    # Register Email Cockpit Skill #701 - Golden Hours 12:00
    try:
        register_golden_hours_noon_job()
    except Exception as e:
        print(f"[Scheduler] Warning: Could not register Golden Hours (12:00) job: {e}")

    # Register Email Cockpit Skill #701 - Golden Hours 16:00
    try:
        register_golden_hours_afternoon_job()
    except Exception as e:
        print(f"[Scheduler] Warning: Could not register Golden Hours (16:00) job: {e}")

    print("[Scheduler] System jobs initialized")
