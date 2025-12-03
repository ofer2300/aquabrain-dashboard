"""
AquaBrain Ingestion Module
Handles file upload, validation, and pipeline triggering.
The Engineer's Command Center - "Upload & GO"
"""

import os
import uuid
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class FileType(Enum):
    """Supported file types for ingestion."""
    DWG = "dwg"
    PDF = "pdf"
    RVT = "rvt"
    IFC = "ifc"
    DXF = "dxf"


class ProjectStatus(Enum):
    """Project processing status."""
    CREATED = "created"
    FILES_UPLOADED = "files_uploaded"
    PROCESSING = "processing"
    AI_ANALYSIS = "ai_analysis"
    HYDRAULIC_CALC = "hydraulic_calc"
    REVIT_GENERATION = "revit_generation"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class UploadedFile:
    """Represents an uploaded file."""
    id: str
    original_name: str
    stored_path: str
    file_type: FileType
    size_bytes: int
    checksum: str
    uploaded_at: str
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class Project:
    """Represents an AquaBrain project."""
    id: str
    name: str
    created_at: str
    status: ProjectStatus
    files: List[UploadedFile] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    processing_log: List[Dict[str, Any]] = field(default_factory=list)
    results: Optional[Dict[str, Any]] = None


class IngestionManager:
    """
    Manages file ingestion and project initialization.
    The Gateway between the Engineer's command and the AI pipeline.
    """

    ALLOWED_EXTENSIONS = {'.dwg', '.pdf', '.rvt', '.ifc', '.dxf'}
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    UPLOAD_DIR = Path("uploads")

    def __init__(self):
        self.projects: Dict[str, Project] = {}
        self.task_queue: List[Dict[str, Any]] = []
        self._ensure_upload_dir()

    def _ensure_upload_dir(self):
        """Create upload directory if it doesn't exist."""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def _generate_id(self) -> str:
        """Generate unique ID."""
        return str(uuid.uuid4())[:8].upper()

    def _calculate_checksum(self, content: bytes) -> str:
        """Calculate MD5 checksum for file validation."""
        return hashlib.md5(content).hexdigest()

    def _get_file_type(self, filename: str) -> Optional[FileType]:
        """Determine file type from extension."""
        ext = Path(filename).suffix.lower()
        type_map = {
            '.dwg': FileType.DWG,
            '.pdf': FileType.PDF,
            '.rvt': FileType.RVT,
            '.ifc': FileType.IFC,
            '.dxf': FileType.DXF,
        }
        return type_map.get(ext)

    def create_project(self, name: str, settings: Optional[Dict] = None) -> Project:
        """
        Create a new project.
        This is called when the engineer starts a new design session.
        """
        project_id = f"PRJ-{self._generate_id()}"
        project = Project(
            id=project_id,
            name=name,
            created_at=datetime.now().isoformat(),
            status=ProjectStatus.CREATED,
            settings=settings or {
                "standard": "NFPA 13",
                "hazard_class": "light",
                "water_pressure_bar": 4.0,
            }
        )
        self.projects[project_id] = project
        self._log_event(project_id, "PROJECT_CREATED", f"Project '{name}' created")
        return project

    def handle_file_upload(
        self,
        project_id: str,
        filename: str,
        content: bytes
    ) -> Dict[str, Any]:
        """
        Handle file upload from the engineer.
        Validates and stores the file for processing.

        Returns:
            Dict with upload result and any validation errors
        """
        if project_id not in self.projects:
            return {"success": False, "error": f"Project {project_id} not found"}

        project = self.projects[project_id]

        # Validate extension
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            return {
                "success": False,
                "error": f"File type '{ext}' not supported. Allowed: {self.ALLOWED_EXTENSIONS}"
            }

        # Validate size
        if len(content) > self.MAX_FILE_SIZE:
            return {
                "success": False,
                "error": f"File too large. Maximum: {self.MAX_FILE_SIZE // (1024*1024)}MB"
            }

        # Generate file ID and path
        file_id = self._generate_id()
        file_type = self._get_file_type(filename)
        stored_filename = f"{project_id}_{file_id}{ext}"
        stored_path = self.UPLOAD_DIR / stored_filename

        # Save file
        with open(stored_path, 'wb') as f:
            f.write(content)

        # Create file record
        uploaded_file = UploadedFile(
            id=file_id,
            original_name=filename,
            stored_path=str(stored_path),
            file_type=file_type,
            size_bytes=len(content),
            checksum=self._calculate_checksum(content),
            uploaded_at=datetime.now().isoformat(),
            validated=True,
        )

        project.files.append(uploaded_file)
        project.status = ProjectStatus.FILES_UPLOADED
        self._log_event(project_id, "FILE_UPLOADED", f"File '{filename}' uploaded ({len(content)} bytes)")

        return {
            "success": True,
            "file_id": file_id,
            "filename": filename,
            "size": len(content),
            "checksum": uploaded_file.checksum,
        }

    def trigger_processing_pipeline(self, project_id: str) -> Dict[str, Any]:
        """
        THE GO BUTTON - Triggers the entire processing pipeline.
        This is the moment the engineer hits IGNITE.

        Pipeline stages:
        1. File normalization
        2. AI analysis (ComfyUI)
        3. Voxelization
        4. Generative routing
        5. Hydraulic calculations
        6. Revit generation
        """
        if project_id not in self.projects:
            return {"success": False, "error": f"Project {project_id} not found"}

        project = self.projects[project_id]

        if not project.files:
            return {"success": False, "error": "No files uploaded. Upload plans first."}

        # Update status
        project.status = ProjectStatus.PROCESSING
        self._log_event(project_id, "PIPELINE_STARTED", "🚀 IGNITION! Processing pipeline initiated")

        # Create task for the processing queue
        task = {
            "task_id": f"TASK-{self._generate_id()}",
            "project_id": project_id,
            "type": "FULL_PIPELINE",
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "files": [f.stored_path for f in project.files],
            "settings": project.settings,
            "stages": [
                {"name": "normalization", "status": "pending"},
                {"name": "ai_analysis", "status": "pending"},
                {"name": "voxelization", "status": "pending"},
                {"name": "routing", "status": "pending"},
                {"name": "hydraulics", "status": "pending"},
                {"name": "revit_generation", "status": "pending"},
            ]
        }

        self.task_queue.append(task)

        return {
            "success": True,
            "task_id": task["task_id"],
            "project_id": project_id,
            "message": "🚀 Pipeline ignited! Processing started.",
            "stages": len(task["stages"]),
        }

    def get_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get current project status and progress."""
        if project_id not in self.projects:
            return None

        project = self.projects[project_id]
        return {
            "id": project.id,
            "name": project.name,
            "status": project.status.value,
            "files_count": len(project.files),
            "files": [
                {"name": f.original_name, "type": f.file_type.value, "size": f.size_bytes}
                for f in project.files
            ],
            "settings": project.settings,
            "log": project.processing_log[-10:],  # Last 10 events
            "results": project.results,
        }

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get all pending tasks for workers (Revit Agent, AI Worker, etc.)"""
        return [t for t in self.task_queue if t["status"] == "pending"]

    def update_task_status(self, task_id: str, status: str, stage: Optional[str] = None):
        """Update task status (called by workers)."""
        for task in self.task_queue:
            if task["task_id"] == task_id:
                task["status"] = status
                if stage:
                    for s in task["stages"]:
                        if s["name"] == stage:
                            s["status"] = status
                            break

                # Update project status based on stage
                project = self.projects.get(task["project_id"])
                if project and stage:
                    stage_to_status = {
                        "ai_analysis": ProjectStatus.AI_ANALYSIS,
                        "hydraulics": ProjectStatus.HYDRAULIC_CALC,
                        "revit_generation": ProjectStatus.REVIT_GENERATION,
                    }
                    if stage in stage_to_status:
                        project.status = stage_to_status[stage]

                break

    def _log_event(self, project_id: str, event_type: str, message: str):
        """Log event to project history."""
        if project_id in self.projects:
            self.projects[project_id].processing_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "message": message,
            })


# Global instance
ingestion_manager = IngestionManager()
