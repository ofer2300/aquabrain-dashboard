"""
Integration Flow Tests
======================
End-to-end tests for the engineering pipeline.
"""

import sys
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestAPIEndpoints:
    """Test suite for API endpoints."""

    def test_health_endpoint(self, client):
        """Test enhanced health check endpoint."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "checks" in data
        assert "disk" in data["checks"]
        assert "memory" in data["checks"]
        assert "bridge" in data["checks"]
        assert "uptime_seconds" in data

    def test_status_endpoint(self, client):
        """Test system status endpoint."""
        response = client.get("/api/status")

        assert response.status_code == 200
        data = response.json()
        assert data["system"] == "AquaBrain"
        assert data["status"] == "LIVE"
        assert "ai_engine" in data

    def test_hydraulic_calculation(self, client, sample_hydraulic_input):
        """Test hydraulic calculation endpoint."""
        response = client.post("/api/calc/hydraulic", json=sample_hydraulic_input)

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "pressure_loss" in data
        assert "velocity" in data
        assert "compliant" in data
        assert "notes" in data

        # Check values are reasonable
        assert data["pressure_loss"] > 0
        assert data["velocity"] > 0
        assert isinstance(data["compliant"], bool)

    def test_hydraulic_validation_error(self, client):
        """Test hydraulic endpoint rejects invalid input."""
        invalid_input = {
            "flow": -100,  # Negative flow
            "length": 50,
            "diameter": 2,
        }

        response = client.post("/api/calc/hydraulic", json=invalid_input)

        # Should return validation error
        assert response.status_code == 422

    def test_engineering_process_endpoint(self, client, sample_engineering_request):
        """Test the main engineering pipeline endpoint."""
        response = client.post(
            "/api/engineering/start-process",
            json=sample_engineering_request
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "project_id" in data
        assert "status" in data
        assert "traffic_light" in data

        # Check traffic light
        traffic = data["traffic_light"]
        assert traffic["status"] in ["GREEN", "YELLOW", "RED"]
        assert "message" in traffic
        assert "details" in traffic
        assert "metrics" in traffic

        # Check metrics
        metrics = traffic["metrics"]
        assert "maxVelocity" in metrics
        assert "pressureLoss" in metrics
        assert "clashCount" in metrics
        assert "nfpaCompliant" in metrics

    def test_engineering_process_completes(self, client, sample_engineering_request):
        """Test that pipeline completes all stages."""
        response = client.post(
            "/api/engineering/start-process",
            json=sample_engineering_request
        )

        data = response.json()

        # Should have all stages completed
        expected_stages = ["extract", "voxelize", "route", "calculate", "validate", "generate", "signal"]
        assert data["stages_completed"] == expected_stages

    def test_engineering_process_returns_summaries(self, client, sample_engineering_request):
        """Test that pipeline returns all summary data."""
        response = client.post(
            "/api/engineering/start-process",
            json=sample_engineering_request
        )

        data = response.json()

        # Check geometry summary
        assert "geometry_summary" in data
        geo = data["geometry_summary"]
        assert "floors" in geo
        assert "total_area_sqm" in geo

        # Check routing summary
        assert "routing_summary" in data
        routing = data["routing_summary"]
        assert "total_segments" in routing
        assert "total_length_m" in routing
        assert "total_sprinklers" in routing

        # Check hydraulic summary
        assert "hydraulic_summary" in data
        hydraulic = data["hydraulic_summary"]
        assert "main_line" in hydraulic
        assert "totals" in hydraulic

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "AquaBrain" in data["message"]


class TestTrafficLightLogic:
    """Test suite for Traffic Light decision logic."""

    def test_green_light_conditions(self, client):
        """Test conditions that produce GREEN light."""
        request = {
            "project_id": "TEST-GREEN",
            "hazard_class": "light",
            "notes": ""
        }

        response = client.post("/api/engineering/start-process", json=request)
        data = response.json()

        # With default simulation, should get GREEN
        assert data["traffic_light"]["status"] == "GREEN"
        assert data["traffic_light"]["metrics"]["nfpaCompliant"] is True

    def test_traffic_light_has_details(self, client):
        """Test that traffic light includes detailed information."""
        request = {
            "project_id": "TEST-DETAILS",
            "hazard_class": "light",
            "notes": ""
        }

        response = client.post("/api/engineering/start-process", json=request)
        data = response.json()

        traffic = data["traffic_light"]

        # Should have Hebrew message
        assert len(traffic["message"]) > 0

        # Should have multiple detail items
        assert len(traffic["details"]) >= 3

        # Should have confidence score
        assert 0 < traffic["confidence"] <= 1.0
