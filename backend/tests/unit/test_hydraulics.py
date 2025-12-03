"""
Hydraulic Calculation Tests
===========================
Unit tests for Hazen-Williams calculations.
"""

import sys
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.hydraulics import HydraulicCalculator, PipeData


class TestHydraulicCalculator:
    """Test suite for HydraulicCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return HydraulicCalculator()

    def test_velocity_calculation(self, calculator):
        """Test velocity calculation with known values."""
        # 100 GPM through 2" pipe
        velocity = calculator.calculate_velocity(100, 2.067)  # Actual ID

        # Expected: ~9.5 fps (V = 0.408 * Q / d^2)
        assert 9.0 < velocity < 10.0
        assert velocity > 0

    def test_pressure_loss_calculation(self, calculator):
        """Test Hazen-Williams pressure loss calculation."""
        pipe = PipeData(
            flow_gpm=100,
            diameter_inch=2.0,
            length_ft=100,
            c_factor=120,
            use_nominal=True,
            schedule="40"
        )

        result = calculator.calculate(pipe)

        # Pressure loss should be positive
        assert result.pressure_loss_psi > 0
        # Velocity should be calculated
        assert result.velocity_fps > 0
        # With 100 GPM through 2" pipe, should be compliant
        assert result.velocity_ok is True

    def test_high_velocity_warning(self, calculator):
        """Test that high velocity (>20 fps) triggers warning."""
        # High flow through small pipe
        pipe = PipeData(
            flow_gpm=150,
            diameter_inch=1.0,
            length_ft=50,
            c_factor=120,
            use_nominal=True,
            schedule="40"
        )

        result = calculator.calculate(pipe)

        # Velocity should exceed 20 fps (warning threshold)
        assert result.velocity_fps > 20
        # Should have warnings
        assert len(result.warnings) > 0

    def test_sch40_diameter_conversion(self, calculator):
        """Test SCH 40 nominal to actual diameter conversion."""
        pipe = PipeData(
            flow_gpm=50,
            diameter_inch=2.0,  # Nominal
            length_ft=50,
            c_factor=120,
            use_nominal=True,
            schedule="40"
        )

        result = calculator.calculate(pipe)

        # Should use actual ID of 2.067"
        assert result.actual_diameter == pytest.approx(2.067, rel=0.01)

    def test_sch10_diameter_conversion(self, calculator):
        """Test SCH 10 nominal to actual diameter conversion."""
        pipe = PipeData(
            flow_gpm=50,
            diameter_inch=2.0,  # Nominal
            length_ft=50,
            c_factor=120,
            use_nominal=True,
            schedule="10"
        )

        result = calculator.calculate(pipe)

        # SCH 10 has larger ID than SCH 40
        assert result.actual_diameter > 2.0

    def test_c_factor_impact(self, calculator):
        """Test that C-factor affects pressure loss."""
        base_pipe = PipeData(
            flow_gpm=100,
            diameter_inch=2.0,
            length_ft=100,
            c_factor=120,  # Standard
            use_nominal=True,
            schedule="40"
        )

        old_pipe = PipeData(
            flow_gpm=100,
            diameter_inch=2.0,
            length_ft=100,
            c_factor=100,  # Corroded pipe
            use_nominal=True,
            schedule="40"
        )

        result_new = calculator.calculate(base_pipe)
        result_old = calculator.calculate(old_pipe)

        # Lower C-factor = higher friction loss
        assert result_old.pressure_loss_psi > result_new.pressure_loss_psi

    def test_zero_flow_handling(self, calculator):
        """Test handling of edge cases."""
        # Velocity at zero flow should be zero
        velocity = calculator.calculate_velocity(0, 2.0)
        assert velocity == 0

    def test_velocity_compliance_threshold(self, calculator):
        """Test 32 fps max velocity (NFPA 13)."""
        # Create a pipe with velocity just under 32 fps
        pipe_ok = PipeData(
            flow_gpm=100,
            diameter_inch=1.5,
            length_ft=50,
            c_factor=120,
            use_nominal=True,
            schedule="40"
        )

        result = calculator.calculate(pipe_ok)

        # Should be compliant if under 32 fps
        if result.velocity_fps < 32:
            assert result.velocity_ok is True
