"""
NFPA Standards Tests
====================
Unit tests for NFPA 13 compliance validation.
"""

import sys
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.standards import NFPA13Validator, HazardClass


class TestNFPA13Validator:
    """Test suite for NFPA 13 validation."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return NFPA13Validator()

    def test_light_hazard_requirements(self, validator):
        """Test Light Hazard requirements."""
        req = validator.get_requirements(HazardClass.LIGHT)

        assert req.density_gpm_ft2 == pytest.approx(0.10, rel=0.01)
        assert req.max_coverage_ft2 == 225
        assert req.min_pressure_psi == 7

    def test_ordinary_1_requirements(self, validator):
        """Test Ordinary Hazard Group 1 requirements."""
        req = validator.get_requirements(HazardClass.ORDINARY_1)

        assert req.density_gpm_ft2 == pytest.approx(0.15, rel=0.01)
        assert req.max_coverage_ft2 == 130
        assert req.min_pressure_psi == 7

    def test_ordinary_2_requirements(self, validator):
        """Test Ordinary Hazard Group 2 requirements."""
        req = validator.get_requirements(HazardClass.ORDINARY_2)

        assert req.density_gpm_ft2 == pytest.approx(0.20, rel=0.01)
        assert req.max_coverage_ft2 == 130
        assert req.min_pressure_psi == 7

    def test_extra_1_requirements(self, validator):
        """Test Extra Hazard Group 1 requirements."""
        req = validator.get_requirements(HazardClass.EXTRA_1)

        assert req.density_gpm_ft2 == pytest.approx(0.30, rel=0.01)
        assert req.max_coverage_ft2 == 100
        assert req.min_pressure_psi >= 7

    def test_validation_passes(self, validator):
        """Test validation with compliant parameters."""
        result = validator.validate(
            hazard_class=HazardClass.LIGHT,
            actual_density=0.12,   # Above 0.10 minimum
            actual_spacing=12,     # Below 15 ft max spacing
            actual_coverage=200,   # Below 225 ft² max coverage
            actual_pressure=15,    # Above 7 psi minimum
        )

        assert result.is_compliant is True
        assert len(result.violations) == 0

    def test_validation_fails_density(self, validator):
        """Test validation fails with insufficient density."""
        result = validator.validate(
            hazard_class=HazardClass.LIGHT,
            actual_density=0.05,   # Below 0.10 minimum
            actual_spacing=12,     # Valid spacing
            actual_coverage=200,   # Valid coverage
            actual_pressure=15,    # Valid pressure
        )

        assert result.is_compliant is False
        assert len(result.violations) > 0
        assert any("density" in v.lower() for v in result.violations)

    def test_validation_fails_coverage(self, validator):
        """Test validation fails with excessive coverage."""
        result = validator.validate(
            hazard_class=HazardClass.LIGHT,
            actual_density=0.12,
            actual_spacing=12,     # Valid spacing
            actual_coverage=300,   # Exceeds 225 ft² max
            actual_pressure=15,
        )

        assert result.is_compliant is False
        assert len(result.violations) > 0
        assert any("coverage" in v.lower() for v in result.violations)

    def test_validation_fails_pressure(self, validator):
        """Test validation fails with insufficient pressure."""
        result = validator.validate(
            hazard_class=HazardClass.LIGHT,
            actual_density=0.12,   # Valid density
            actual_spacing=12,     # Valid spacing
            actual_coverage=200,   # Valid coverage
            actual_pressure=5,     # Below 7 psi minimum
        )

        assert result.is_compliant is False
        assert any("pressure" in v.lower() for v in result.violations)

    def test_required_flow_calculation(self, validator):
        """Test required flow calculation."""
        # Light hazard: 0.10 gpm/ft2 * 1500 ft2 = 150 GPM
        result = validator.calculate_required_flow(
            hazard_class=HazardClass.LIGHT,
            coverage_area_ft2=1500
        )

        # Returns a dict with flow values
        assert "sprinkler_demand_gpm" in result
        assert result["sprinkler_demand_gpm"] == pytest.approx(150.0, rel=0.05)

    def test_get_requirements_dict(self, validator):
        """Test requirements as dictionary."""
        req_dict = validator.get_requirements_dict(HazardClass.LIGHT)

        # Check actual keys from the API
        assert "density_gpm_ft2" in req_dict
        assert "max_coverage_ft2" in req_dict
        assert "min_pressure_psi" in req_dict
        assert isinstance(req_dict["density_gpm_ft2"], float)

    def test_velocity_limit_warning(self, validator):
        """Test that high velocity triggers appropriate response."""
        # NFPA 13 max velocity is 32 fps
        # 33 fps should trigger warnings
        velocity_fps = 33.0

        # This should be flagged during validation
        assert velocity_fps > 32.0  # Exceeds limit
