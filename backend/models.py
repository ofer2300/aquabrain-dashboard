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
