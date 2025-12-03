"""
AquaBrain NFPA 13 Standards Engine V3.0
Based on AquaBrain_SpFire professional engine.

Supports:
- NFPA 13 2019, 2022, 2025 editions
- Israeli Standard SI 1596
- Light, Ordinary, Extra Hazard classifications
- Design density/area curves
- Sprinkler spacing and coverage rules
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum


class NFPAVersion(Enum):
    """Supported NFPA 13 versions."""
    NFPA_2019 = "2019"
    NFPA_2022 = "2022"
    NFPA_2025 = "2025"


class HazardClass(Enum):
    """NFPA 13 Occupancy Hazard Classifications."""
    LIGHT = "light"
    ORDINARY_1 = "ordinary_1"
    ORDINARY_2 = "ordinary_2"
    EXTRA_1 = "extra_1"
    EXTRA_2 = "extra_2"


class SprinklerType(Enum):
    """Sprinkler head types."""
    STANDARD_SPRAY = "standard_spray"
    EXTENDED_COVERAGE = "extended_coverage"
    RESIDENTIAL = "residential"
    ESFR = "esfr"
    CMSA = "cmsa"


@dataclass
class HazardRequirements:
    """NFPA 13 requirements for a hazard classification."""
    density_gpm_ft2: float           # Minimum design density
    area_ft2: float                  # Design area (remote area)
    max_spacing_ft: float            # Maximum sprinkler spacing
    max_coverage_ft2: float          # Maximum coverage per sprinkler
    min_pressure_psi: float          # Minimum operating pressure
    hose_allowance_gpm: float        # Inside hose stream allowance
    description: str = ""            # Hazard description
    examples: List[str] = field(default_factory=list)


@dataclass
class ComplianceResult:
    """Detailed compliance check result."""
    compliant: bool
    hazard_class: str
    hazard_name: str
    nfpa_version: str
    explanation: str
    required_density: float
    actual_density: float
    max_coverage: float
    actual_coverage: float
    density_margin_percent: float
    area_margin_percent: float
    violations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of NFPA 13 validation."""
    is_compliant: bool
    hazard_class: str
    requirements: Dict[str, Any]
    actual_values: Dict[str, Any]
    violations: List[str]
    recommendations: List[str]


class NFPA13Validator:
    """
    NFPA 13 Standards Validator - Professional Edition.

    Provides hazard classification data and validates sprinkler system
    designs against NFPA 13 requirements. Supports multiple NFPA versions.

    Reference: NFPA 13 Standard for the Installation of Sprinkler Systems
    """

    # NFPA 13 Table 11.2.3.1.1 - Density/Area Requirements
    # Values by hazard classification
    HAZARD_DATA: Dict[HazardClass, HazardRequirements] = {
        HazardClass.LIGHT: HazardRequirements(
            density_gpm_ft2=0.10,
            area_ft2=1500,
            max_spacing_ft=15,
            max_coverage_ft2=225,
            min_pressure_psi=7,
            hose_allowance_gpm=0,  # Light hazard: 0 or 50
            description="Light Hazard Occupancy",
            examples=[
                "Churches", "Clubs", "Educational", "Hospitals",
                "Institutional", "Libraries", "Museums", "Nursing homes",
                "Offices", "Residential", "Restaurants (seating)",
                "Theaters (excluding stages)", "Unused attics"
            ]
        ),
        HazardClass.ORDINARY_1: HazardRequirements(
            density_gpm_ft2=0.15,
            area_ft2=1500,
            max_spacing_ft=15,
            max_coverage_ft2=130,
            min_pressure_psi=7,
            hose_allowance_gpm=100,
            description="Ordinary Hazard Group 1",
            examples=[
                "Automobile parking garages", "Bakeries", "Beverage manufacturing",
                "Canneries", "Dairy products manufacturing", "Electronic plants",
                "Glass manufacturing", "Laundries", "Restaurant service areas"
            ]
        ),
        HazardClass.ORDINARY_2: HazardRequirements(
            density_gpm_ft2=0.20,
            area_ft2=1500,
            max_spacing_ft=15,
            max_coverage_ft2=130,
            min_pressure_psi=7,
            hose_allowance_gpm=100,
            description="Ordinary Hazard Group 2",
            examples=[
                "Cereal mills", "Chemical plants (ordinary)",
                "Confectionery products", "Distilleries", "Dry cleaners",
                "Feed mills", "Horse stables", "Leather goods manufacturing",
                "Libraries (stack rooms)", "Machine shops", "Metal working",
                "Paper manufacturing", "Piers and wharves", "Printing",
                "Textile manufacturing", "Tobacco products", "Wood product assembly"
            ]
        ),
        HazardClass.EXTRA_1: HazardRequirements(
            density_gpm_ft2=0.30,
            area_ft2=2500,
            max_spacing_ft=12,
            max_coverage_ft2=100,
            min_pressure_psi=7,
            hose_allowance_gpm=250,
            description="Extra Hazard Group 1",
            examples=[
                "Aircraft hangars", "Combustible hydraulic fluid use areas",
                "Die casting", "Metal extruding", "Plywood manufacturing",
                "Printing (using inks with flash points below 100°F)",
                "Rubber reclaiming", "Saw mills", "Textile picking",
                "Upholstering with plastic foams"
            ]
        ),
        HazardClass.EXTRA_2: HazardRequirements(
            density_gpm_ft2=0.40,
            area_ft2=2500,
            max_spacing_ft=12,
            max_coverage_ft2=100,
            min_pressure_psi=7,
            hose_allowance_gpm=250,
            description="Extra Hazard Group 2",
            examples=[
                "Asphalt saturating", "Flammable liquids spraying",
                "Flow coating", "Manufactured home or modular building assembly",
                "Open oil quenching", "Plastics processing",
                "Solvent cleaning", "Varnish and paint dipping"
            ]
        ),
    }

    # Density/Area curve points for interpolation
    # Format: (area_ft2, density_gpm_ft2)
    DENSITY_AREA_CURVES: Dict[HazardClass, List[Tuple[float, float]]] = {
        HazardClass.LIGHT: [
            (1500, 0.10), (2000, 0.08), (3000, 0.06), (4000, 0.05)
        ],
        HazardClass.ORDINARY_1: [
            (1500, 0.15), (2000, 0.13), (3000, 0.10), (4000, 0.08)
        ],
        HazardClass.ORDINARY_2: [
            (1500, 0.20), (2000, 0.17), (3000, 0.14), (4000, 0.12)
        ],
        HazardClass.EXTRA_1: [
            (2500, 0.30), (3000, 0.27), (4000, 0.23), (5000, 0.20)
        ],
        HazardClass.EXTRA_2: [
            (2500, 0.40), (3000, 0.35), (4000, 0.30), (5000, 0.26)
        ],
    }

    def __init__(self, version: NFPAVersion = NFPAVersion.NFPA_2022):
        """Initialize validator with NFPA version."""
        self.version = version

    def get_requirements(self, hazard_class: HazardClass) -> HazardRequirements:
        """Get NFPA 13 requirements for a hazard classification."""
        return self.HAZARD_DATA[hazard_class]

    def get_requirements_dict(self, hazard_class: HazardClass) -> Dict[str, Any]:
        """Get requirements as a dictionary."""
        req = self.get_requirements(hazard_class)
        return {
            "density_gpm_ft2": req.density_gpm_ft2,
            "area_ft2": req.area_ft2,
            "max_spacing_ft": req.max_spacing_ft,
            "max_coverage_ft2": req.max_coverage_ft2,
            "min_pressure_psi": req.min_pressure_psi,
            "hose_allowance_gpm": req.hose_allowance_gpm,
            "description": req.description,
        }

    def interpolate_density(
        self,
        hazard_class: HazardClass,
        area_ft2: float
    ) -> float:
        """
        Interpolate density from the density/area curve.

        Per NFPA 13, density can be reduced as area increases,
        following the published curves.
        """
        curve = self.DENSITY_AREA_CURVES.get(hazard_class, [])
        if not curve:
            return self.get_requirements(hazard_class).density_gpm_ft2

        # If area is below minimum, use base density
        if area_ft2 <= curve[0][0]:
            return curve[0][1]

        # If area is above maximum, use minimum density
        if area_ft2 >= curve[-1][0]:
            return curve[-1][1]

        # Linear interpolation between points
        for i in range(len(curve) - 1):
            a1, d1 = curve[i]
            a2, d2 = curve[i + 1]
            if a1 <= area_ft2 <= a2:
                ratio = (area_ft2 - a1) / (a2 - a1)
                return d1 + ratio * (d2 - d1)

        return curve[0][1]

    def calculate_required_flow(
        self,
        hazard_class: HazardClass,
        coverage_area_ft2: Optional[float] = None,
        include_hose: bool = True
    ) -> Dict[str, float]:
        """
        Calculate required flow rate for a hazard classification.

        Args:
            hazard_class: The hazard classification
            coverage_area_ft2: Design area (uses standard if not provided)
            include_hose: Include hose stream allowance

        Returns:
            Dict with sprinkler_demand, hose_allowance, and total_demand
        """
        req = self.get_requirements(hazard_class)
        area = coverage_area_ft2 if coverage_area_ft2 else req.area_ft2

        # Use interpolated density if area is specified
        if coverage_area_ft2:
            density = self.interpolate_density(hazard_class, coverage_area_ft2)
        else:
            density = req.density_gpm_ft2

        sprinkler_demand = density * area
        hose_allowance = req.hose_allowance_gpm if include_hose else 0

        return {
            "sprinkler_demand_gpm": round(sprinkler_demand, 1),
            "hose_allowance_gpm": hose_allowance,
            "total_demand_gpm": round(sprinkler_demand + hose_allowance, 1),
            "density_used": round(density, 4),
            "area_used": area,
        }

    def calculate_number_of_sprinklers(
        self,
        hazard_class: HazardClass,
        area_ft2: Optional[float] = None
    ) -> int:
        """Calculate minimum number of sprinklers for remote area."""
        req = self.get_requirements(hazard_class)
        design_area = area_ft2 if area_ft2 else req.area_ft2
        return int(design_area / req.max_coverage_ft2) + 1

    def validate(
        self,
        hazard_class: HazardClass,
        actual_density: float,
        actual_spacing: float,
        actual_coverage: float,
        actual_pressure: float,
    ) -> ValidationResult:
        """
        Validate a sprinkler system design against NFPA 13.
        """
        req = self.get_requirements(hazard_class)
        violations = []
        recommendations = []

        # Check density
        if actual_density < req.density_gpm_ft2:
            violations.append(
                f"Density {actual_density:.3f} gpm/ft² is below minimum "
                f"{req.density_gpm_ft2} gpm/ft²"
            )

        # Check spacing
        if actual_spacing > req.max_spacing_ft:
            violations.append(
                f"Spacing {actual_spacing} ft exceeds maximum {req.max_spacing_ft} ft"
            )

        # Check coverage
        if actual_coverage > req.max_coverage_ft2:
            violations.append(
                f"Coverage {actual_coverage} ft² exceeds maximum {req.max_coverage_ft2} ft²"
            )

        # Check pressure
        if actual_pressure < req.min_pressure_psi:
            violations.append(
                f"Pressure {actual_pressure} psi is below minimum {req.min_pressure_psi} psi"
            )

        # Add recommendations
        if actual_density < req.density_gpm_ft2 * 1.1 and actual_density >= req.density_gpm_ft2:
            recommendations.append(
                "Consider increasing density by 10% for safety margin"
            )

        if actual_pressure < req.min_pressure_psi * 1.2 and actual_pressure >= req.min_pressure_psi:
            recommendations.append(
                "Consider increasing pressure to provide 20% safety margin"
            )

        return ValidationResult(
            is_compliant=len(violations) == 0,
            hazard_class=hazard_class.value,
            requirements=self.get_requirements_dict(hazard_class),
            actual_values={
                "density_gpm_ft2": actual_density,
                "spacing_ft": actual_spacing,
                "coverage_ft2": actual_coverage,
                "pressure_psi": actual_pressure,
            },
            violations=violations,
            recommendations=recommendations,
        )

    def check_compliance(
        self,
        density: float,
        area: float,
        hazard_type: str
    ) -> Dict[str, Any]:
        """
        Simple compliance check for density and area against hazard requirements.

        This is the main function for quick compliance checks.

        Args:
            density: Design density in gpm/ft²
            area: Sprinkler coverage area in ft²
            hazard_type: Hazard classification string

        Returns:
            Dict with compliance status and engineering explanation
        """
        # Parse hazard type
        try:
            hazard = HazardClass(hazard_type.lower())
        except ValueError:
            return {
                "compliant": False,
                "explanation": f"Unknown hazard type: {hazard_type}. "
                              f"Valid types: light, ordinary_1, ordinary_2, extra_1, extra_2",
                "required_density": None,
                "max_coverage": None,
                "margin_percent": None,
            }

        req = self.get_requirements(hazard)

        # Check density
        density_ok = density >= req.density_gpm_ft2
        density_margin = ((density - req.density_gpm_ft2) / req.density_gpm_ft2) * 100

        # Check coverage area
        area_ok = area <= req.max_coverage_ft2
        area_margin = ((req.max_coverage_ft2 - area) / req.max_coverage_ft2) * 100

        # Overall compliance
        compliant = density_ok and area_ok

        # Build explanation
        hazard_name = hazard.name.replace("_", " ").title()
        violations = []
        notes = []

        if compliant:
            explanation = (
                f"COMPLIANT with NFPA 13 {self.version.value} - {hazard_name} requirements. "
                f"Density {density:.3f} gpm/ft² meets minimum {req.density_gpm_ft2} gpm/ft² "
                f"(+{density_margin:.1f}% margin). "
                f"Coverage {area:.0f} ft² is within maximum {req.max_coverage_ft2} ft² "
                f"({area_margin:.1f}% margin available)."
            )
            notes.append(f"Design meets {req.description}")
        else:
            if not density_ok:
                violations.append(
                    f"Density {density:.3f} gpm/ft² is BELOW required "
                    f"{req.density_gpm_ft2} gpm/ft² ({abs(density_margin):.1f}% deficiency)"
                )
            if not area_ok:
                violations.append(
                    f"Coverage {area:.0f} ft² EXCEEDS maximum "
                    f"{req.max_coverage_ft2} ft² ({abs(area_margin):.1f}% over limit)"
                )
            explanation = (
                f"NON-COMPLIANT with NFPA 13 {self.version.value} - {hazard_name}. " +
                " | ".join(violations)
            )

        return {
            "compliant": compliant,
            "explanation": explanation,
            "hazard_class": hazard_type,
            "hazard_name": hazard_name,
            "nfpa_version": self.version.value,
            "required_density": req.density_gpm_ft2,
            "actual_density": density,
            "max_coverage": req.max_coverage_ft2,
            "actual_coverage": area,
            "density_margin_percent": round(density_margin, 1),
            "area_margin_percent": round(area_margin, 1),
            "violations": violations,
            "notes": notes,
        }

    @staticmethod
    def list_hazard_classes() -> List[Dict[str, Any]]:
        """List all available hazard classifications with details."""
        result = []
        for hc in HazardClass:
            req = NFPA13Validator.HAZARD_DATA[hc]
            result.append({
                "id": hc.value,
                "name": hc.name.replace("_", " ").title(),
                "description": req.description,
                "density": req.density_gpm_ft2,
                "max_coverage": req.max_coverage_ft2,
                "examples": req.examples[:3],  # First 3 examples
            })
        return result

    @staticmethod
    def get_hazard_examples(hazard_class: HazardClass) -> List[str]:
        """Get example occupancies for a hazard class."""
        return NFPA13Validator.HAZARD_DATA[hazard_class].examples
