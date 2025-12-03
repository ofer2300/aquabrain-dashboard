"""
AquaBrain Revit Bridge Module
Manages communication between the web platform and Revit 2026.
This is the gateway to LOD 500 fabrication.
"""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue
import threading


class RevitTaskType(Enum):
    """Types of tasks that can be sent to Revit."""
    GENERATE_SPRINKLERS = "generate_sprinklers"
    CONVERT_TO_FABRICATION = "convert_to_fabrication"
    PLACE_HANGERS = "place_hangers"
    CLASH_DETECTION = "clash_detection"
    EXPORT_ITM = "export_itm"
    SYNC_MODEL = "sync_model"


class TaskStatus(Enum):
    """Task execution status."""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RevitTask:
    """A task to be executed by the Revit Agent."""
    task_id: str
    task_type: RevitTaskType
    project_id: str
    payload: Dict[str, Any]
    created_at: str
    status: TaskStatus = TaskStatus.QUEUED
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class RevitBridge:
    """
    Bridge between AquaBrain Web and Revit 2026.

    Architecture:
    - Web creates tasks and adds them to the queue
    - Revit Agent (external Python/pyRevit script) polls for tasks
    - Agent executes tasks using Revit API
    - Agent reports results back through the bridge
    """

    def __init__(self):
        self.task_queue: List[RevitTask] = []
        self.completed_tasks: Dict[str, RevitTask] = {}
        self.agent_status = {
            "connected": False,
            "last_heartbeat": None,
            "revit_version": None,
            "current_model": None,
        }
        self._task_counter = 0
        self._lock = threading.Lock()

    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        self._task_counter += 1
        return f"RVT-{self._task_counter:05d}"

    def queue_fabrication_task(
        self,
        project_id: str,
        hydraulic_data: Dict[str, Any]
    ) -> RevitTask:
        """
        Queue a fabrication task for Revit.
        This is called after hydraulic calculations are complete.

        The task will:
        1. Generate sprinkler layout in Revit
        2. Convert to Fabrication Parts (ITM)
        3. Place hangers automatically
        """
        task = RevitTask(
            task_id=self._generate_task_id(),
            task_type=RevitTaskType.GENERATE_SPRINKLERS,
            project_id=project_id,
            payload={
                "hydraulic_data": hydraulic_data,
                "operations": [
                    {"op": "generate_sprinklers", "params": hydraulic_data.get("sprinkler_layout", {})},
                    {"op": "route_piping", "params": hydraulic_data.get("pipe_routing", {})},
                    {"op": "convert_fabrication", "params": {"catalog": "default"}},
                    {"op": "place_hangers", "params": {"spacing_ft": 10}},
                ],
                "output_format": "ITM",
            },
            created_at=datetime.now().isoformat(),
        )

        with self._lock:
            self.task_queue.append(task)

        return task

    def queue_clash_detection(self, project_id: str, model_path: str) -> RevitTask:
        """Queue a clash detection task."""
        task = RevitTask(
            task_id=self._generate_task_id(),
            task_type=RevitTaskType.CLASH_DETECTION,
            project_id=project_id,
            payload={"model_path": model_path},
            created_at=datetime.now().isoformat(),
        )

        with self._lock:
            self.task_queue.append(task)

        return task

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """
        Get pending tasks for the Revit Agent.
        Called by the agent via polling.
        """
        with self._lock:
            pending = [
                {
                    "task_id": t.task_id,
                    "type": t.task_type.value,
                    "project_id": t.project_id,
                    "payload": t.payload,
                    "created_at": t.created_at,
                }
                for t in self.task_queue
                if t.status == TaskStatus.QUEUED
            ]
        return pending

    def claim_task(self, task_id: str) -> bool:
        """
        Agent claims a task (marks it as in progress).
        Returns True if successful.
        """
        with self._lock:
            for task in self.task_queue:
                if task.task_id == task_id and task.status == TaskStatus.QUEUED:
                    task.status = TaskStatus.IN_PROGRESS
                    task.started_at = datetime.now().isoformat()
                    return True
        return False

    def complete_task(
        self,
        task_id: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        Agent reports task completion.
        """
        with self._lock:
            for task in self.task_queue:
                if task.task_id == task_id:
                    task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                    task.completed_at = datetime.now().isoformat()
                    task.result = result
                    task.error = error

                    # Move to completed
                    self.completed_tasks[task_id] = task
                    self.task_queue.remove(task)
                    break

    def agent_heartbeat(
        self,
        revit_version: str,
        current_model: Optional[str] = None
    ):
        """
        Agent sends heartbeat to indicate it's alive.
        """
        self.agent_status = {
            "connected": True,
            "last_heartbeat": datetime.now().isoformat(),
            "revit_version": revit_version,
            "current_model": current_model,
        }

    def get_agent_status(self) -> Dict[str, Any]:
        """Get current agent connection status."""
        # Check if agent is still alive (heartbeat within last 30 seconds)
        if self.agent_status["last_heartbeat"]:
            last_beat = datetime.fromisoformat(self.agent_status["last_heartbeat"])
            if (datetime.now() - last_beat).seconds > 30:
                self.agent_status["connected"] = False

        return {
            **self.agent_status,
            "queue_length": len([t for t in self.task_queue if t.status == TaskStatus.QUEUED]),
            "in_progress": len([t for t in self.task_queue if t.status == TaskStatus.IN_PROGRESS]),
        }

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        # Check queue
        for task in self.task_queue:
            if task.task_id == task_id:
                return {
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "created_at": task.created_at,
                    "started_at": task.started_at,
                }

        # Check completed
        if task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
            return {
                "task_id": task.task_id,
                "status": task.status.value,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "result": task.result,
                "error": task.error,
            }

        return None


# Global instance
revit_bridge = RevitBridge()
