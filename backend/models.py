"""
AquaBrain Database Models
=========================
SQLAlchemy models for project persistence and task tracking.
"""

from datetime import datetime
from typing import Optional
import json

from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, Integer, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base

# Database setup
DATABASE_URL = "sqlite:///./aquabrain.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProjectRun(Base):
    """
    Stores engineering pipeline execution history.
    Each run represents one click of the "Capsule" button.
    """
    __tablename__ = "project_runs"

    id = Column(String(50), primary_key=True, index=True)
    project_id = Column(String(100), nullable=False, index=True)

    # Status tracking
    status = Column(String(20), default="QUEUED")  # QUEUED, PROCESSING, COMPLETED, FAILED
    current_stage = Column(String(50), default="queued")
    progress_percent = Column(Integer, default=0)

    # Configuration
    hazard_class = Column(String(20), default="light")
    notes = Column(Text, default="")

    # Results (stored as JSON)
    metrics_json = Column(Text, default="{}")
    traffic_light_json = Column(Text, default="{}")
    geometry_json = Column(Text, default="{}")
    routing_json = Column(Text, default="{}")
    hydraulic_json = Column(Text, default="{}")

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)

    # Error tracking
    error_message = Column(Text, nullable=True)

    def set_metrics(self, metrics: dict):
        """Store metrics as JSON."""
        self.metrics_json = json.dumps(metrics)

    def get_metrics(self) -> dict:
        """Retrieve metrics from JSON."""
        return json.loads(self.metrics_json) if self.metrics_json else {}

    def set_traffic_light(self, traffic: dict):
        """Store traffic light result as JSON."""
        self.traffic_light_json = json.dumps(traffic)

    def get_traffic_light(self) -> dict:
        """Retrieve traffic light from JSON."""
        return json.loads(self.traffic_light_json) if self.traffic_light_json else {}

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "status": self.status,
            "current_stage": self.current_stage,
            "progress_percent": self.progress_percent,
            "hazard_class": self.hazard_class,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            # Parsed JSON fields
            "metrics": self.get_metrics(),
            "traffic_light": self.get_traffic_light(),
            "geometry_summary": json.loads(self.geometry_json) if self.geometry_json else {},
            "routing_summary": json.loads(self.routing_json) if self.routing_json else {},
            "hydraulic_summary": json.loads(self.hydraulic_json) if self.hydraulic_json else {},
        }


class ProjectHistory(Base):
    """
    High-level project tracking across multiple runs.
    """
    __tablename__ = "project_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(200), default="")

    # Statistics
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    last_run_id = Column(String(50), nullable=True)
    last_status = Column(String(20), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EngineerProfile(Base):
    """
    Stores engineer personal details for document automation.
    One-to-one relationship with user (by user_id or default for single user).
    """
    __tablename__ = "engineer_profiles"

    id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(100), nullable=True, unique=True, index=True)

    # Basic Info
    full_name = Column(String(200), nullable=False)
    id_number = Column(String(9), nullable=False)  # Israeli ID: 9 digits
    engineer_license = Column(String(50), nullable=True)

    # Contact Info
    email = Column(String(200), nullable=False)
    email_provider = Column(String(20), default="gmail")  # gmail, outlook, icloud, other
    custom_email = Column(String(200), nullable=True)
    phone = Column(String(20), nullable=False)

    # Stamp & Signature
    stamp_signature_url = Column(String(500), nullable=True)
    stamp_signature_path = Column(String(500), nullable=True)

    # API Keys (stored as JSON, encrypted in production)
    api_keys_json = Column(Text, default="{}")

    # Adobe License
    adobe_license = Column(String(200), nullable=True)

    # Cloud Storage (stored as JSON)
    cloud_storage_json = Column(Text, default="{}")

    # Form State
    is_locked = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_api_keys(self) -> dict:
        """Retrieve API keys from JSON."""
        return json.loads(self.api_keys_json) if self.api_keys_json else {}

    def set_api_keys(self, keys: dict):
        """Store API keys as JSON."""
        self.api_keys_json = json.dumps(keys)

    def get_cloud_storage(self) -> dict:
        """Retrieve cloud storage config from JSON."""
        return json.loads(self.cloud_storage_json) if self.cloud_storage_json else {}

    def set_cloud_storage(self, config: dict):
        """Store cloud storage config as JSON."""
        self.cloud_storage_json = json.dumps(config)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "id_number": self.id_number,
            "engineer_license": self.engineer_license,
            "email": self.email,
            "email_provider": self.email_provider,
            "custom_email": self.custom_email,
            "phone": self.phone,
            "stamp_signature_url": self.stamp_signature_url,
            "api_keys": self.get_api_keys(),
            "adobe_license": self.adobe_license,
            "cloud_storage": self.get_cloud_storage(),
            "is_locked": self.is_locked,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SkillExecution(Base):
    """
    Universal Skill Execution Audit Trail.

    Tracks every skill execution through the Universal Orchestrator.
    Provides the "Traceability" required for engineering liability.
    """
    __tablename__ = "skill_executions"

    id = Column(String(50), primary_key=True, index=True)
    skill_id = Column(String(100), nullable=False, index=True)
    project_id = Column(String(100), nullable=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)

    # Status tracking
    status = Column(String(20), default="queued")  # queued, validating, running, success, failed, cancelled, timeout
    current_stage = Column(String(50), default="queued")
    progress_percent = Column(Integer, default=0)

    # Input/Output (stored as JSON)
    input_params_json = Column(Text, default="{}")
    result_data_json = Column(Text, nullable=True)

    # Artifacts (stored as JSON array)
    artifacts_json = Column(Text, default="[]")

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    execution_time_ms = Column(Integer, default=0)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Metadata (stored as JSON)
    metadata_json = Column(Text, default="{}")

    # Parent task (for chained executions)
    parent_task_id = Column(String(50), nullable=True, index=True)

    def set_input_params(self, params: dict):
        """Store input parameters as JSON."""
        self.input_params_json = json.dumps(params)

    def get_input_params(self) -> dict:
        """Retrieve input parameters from JSON."""
        return json.loads(self.input_params_json) if self.input_params_json else {}

    def set_result_data(self, data: dict):
        """Store result data as JSON."""
        self.result_data_json = json.dumps(data)

    def get_result_data(self) -> dict:
        """Retrieve result data from JSON."""
        return json.loads(self.result_data_json) if self.result_data_json else {}

    def set_artifacts(self, artifacts: list):
        """Store artifacts as JSON."""
        self.artifacts_json = json.dumps(artifacts)

    def get_artifacts(self) -> list:
        """Retrieve artifacts from JSON."""
        return json.loads(self.artifacts_json) if self.artifacts_json else []

    def set_metadata(self, metadata: dict):
        """Store metadata as JSON."""
        self.metadata_json = json.dumps(metadata)

    def get_metadata(self) -> dict:
        """Retrieve metadata from JSON."""
        return json.loads(self.metadata_json) if self.metadata_json else {}

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "status": self.status,
            "current_stage": self.current_stage,
            "progress_percent": self.progress_percent,
            "input_params": self.get_input_params(),
            "result_data": self.get_result_data(),
            "artifacts": self.get_artifacts(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "metadata": self.get_metadata(),
            "parent_task_id": self.parent_task_id,
        }


# Create tables
def init_db():
    """Initialize the database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI - yields database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize on import
init_db()
