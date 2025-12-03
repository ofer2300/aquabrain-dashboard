"""
Pytest Configuration and Fixtures
==================================
Shared test fixtures for AquaBrain tests.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from main import app


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_hydraulic_input():
    """Sample hydraulic calculation input."""
    return {
        "flow": 100,
        "length": 50,
        "diameter": 2,
        "hazard": "light",
        "c_factor": 120,
        "schedule": "40"
    }


@pytest.fixture
def sample_engineering_request():
    """Sample engineering process request (sync mode for testing)."""
    return {
        "project_id": "TEST-001",
        "hazard_class": "light",
        "notes": "Test run",
        "async_mode": False,  # Use sync mode for testing
    }
