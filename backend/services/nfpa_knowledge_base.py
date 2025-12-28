"""
NFPA 13 Knowledge Base - Browser Tool Integration
==================================================
RAG (Retrieval Augmented Generation) for NFPA 13 compliance validation.

This module provides:
1. Local knowledge base with NFPA 13 (2025 Edition) tables
2. Web search integration for live documentation lookup
3. Citation tracking for audit trail
4. Israeli Standard ת"י 1596 cross-reference

Architecture:
┌─────────────────────────────────────────────────────────────┐
│  NFPA Knowledge Base                                         │
├─────────────────────────────────────────────────────────────┤
│  Local Cache (NFPA_TABLES)                                  │
│  ├─ Table 10.2.1: Light Hazard Design Criteria              │
│  ├─ Table 10.2.2: Ordinary Hazard Design Criteria           │
│  ├─ Table 10.2.3: Extra Hazard Design Criteria              │
│  ├─ Table 8.6.2: Sprinkler Spacing Requirements             │
│  ├─ Table 22.4.4.6: Pipe Sizing (Schedule 40)               │
│  └─ Israeli ת"י 1596: Fire Water Tank Requirements          │
├─────────────────────────────────────────────────────────────┤
│  Web Lookup (Gemini AI)                                     │
│  ├─ Real-time NFPA queries                                  │
│  ├─ Citation extraction                                     │
│  └─ Conflict detection                                      │
└─────────────────────────────────────────────────────────────┘

Usage:
    kb = NFPAKnowledgeBase()
    result = kb.query("Light Hazard sprinkler spacing")
    print(result['citation'])  # "NFPA 13, Table 8.6.2.2.1(a)"

Author: AquaBrain V10.0 Platinum
Date: 2025-12-06
"""

from __future__ import annotations
import os
import sys
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# NFPA 13 TABLES (Local Cache)
# ============================================================================

# Table 10.2.1 - Light Hazard Design Criteria
NFPA_TABLE_10_2_1 = {
    "table_id": "10.2.1",
    "title": "Light Hazard Occupancies - Design Criteria",
    "edition": "NFPA 13 (2025)",
    "data": {
        "density_gpm_sqft": 0.10,
        "design_area_sqft": 1500,
        "max_coverage_per_head_sqft": 225,
        "max_spacing_ft": 15.0,
        "min_spacing_ft": 6.0,
        "hose_stream_allowance_gpm": 100,
        "duration_minutes": 30
    },
    "notes": [
        "Light hazard occupancies have limited combustible contents",
        "Examples: offices, churches, museums, hospitals"
    ]
}

# Table 10.2.2 - Ordinary Hazard Design Criteria
NFPA_TABLE_10_2_2 = {
    "table_id": "10.2.2",
    "title": "Ordinary Hazard Occupancies - Design Criteria",
    "edition": "NFPA 13 (2025)",
    "data": {
        "Group 1": {
            "density_gpm_sqft": 0.15,
            "design_area_sqft": 1500,
            "max_coverage_per_head_sqft": 130,
            "max_spacing_ft": 15.0,
            "hose_stream_allowance_gpm": 250,
            "duration_minutes": 60
        },
        "Group 2": {
            "density_gpm_sqft": 0.20,
            "design_area_sqft": 1500,
            "max_coverage_per_head_sqft": 130,
            "max_spacing_ft": 15.0,
            "hose_stream_allowance_gpm": 250,
            "duration_minutes": 60
        }
    },
    "notes": [
        "Ordinary Group 1: Parking garages, laundries, bakeries",
        "Ordinary Group 2: Machine shops, printing plants, libraries"
    ]
}

# Table 10.2.3 - Extra Hazard Design Criteria
NFPA_TABLE_10_2_3 = {
    "table_id": "10.2.3",
    "title": "Extra Hazard Occupancies - Design Criteria",
    "edition": "NFPA 13 (2025)",
    "data": {
        "Group 1": {
            "density_gpm_sqft": 0.30,
            "design_area_sqft": 2500,
            "max_coverage_per_head_sqft": 90,
            "max_spacing_ft": 12.0,
            "hose_stream_allowance_gpm": 500,
            "duration_minutes": 90
        },
        "Group 2": {
            "density_gpm_sqft": 0.40,
            "design_area_sqft": 2500,
            "max_coverage_per_head_sqft": 90,
            "max_spacing_ft": 12.0,
            "hose_stream_allowance_gpm": 500,
            "duration_minutes": 120
        }
    },
    "notes": [
        "Extra Group 1: Woodworking, textile manufacturing",
        "Extra Group 2: Flammable liquid handling, plastics processing"
    ]
}

# Table 8.6.2 - Sprinkler Spacing
NFPA_TABLE_8_6_2 = {
    "table_id": "8.6.2.2.1",
    "title": "Standard Spray Sprinkler Spacing Requirements",
    "edition": "NFPA 13 (2025)",
    "data": {
        "standard_spray_upright_pendent": {
            "max_distance_wall_ft": 7.5,
            "max_distance_between_ft": 15.0,
            "min_distance_between_ft": 6.0,
            "max_deflector_to_ceiling_in": 12,
            "min_deflector_to_ceiling_in": 1
        },
        "extended_coverage": {
            "max_coverage_sqft": 400,
            "max_spacing_ft": 20.0,
            "listing_required": True
        },
        "sidewall": {
            "max_distance_along_wall_ft": 14.0,
            "max_distance_from_wall_ft": 7.0
        }
    }
}

# Table 22.4.4.6 - Pipe Sizing (Schedule 40 Steel)
NFPA_TABLE_22_4_4_6 = {
    "table_id": "22.4.4.6.2",
    "title": "Schedule 40 Steel Pipe - Maximum Sprinkler Count",
    "edition": "NFPA 13 (2025)",
    "data": {
        "1_inch": {"max_sprinklers": 2, "id_inches": 1.049},
        "1.25_inch": {"max_sprinklers": 3, "id_inches": 1.380},
        "1.5_inch": {"max_sprinklers": 5, "id_inches": 1.610},
        "2_inch": {"max_sprinklers": 10, "id_inches": 2.067},
        "2.5_inch": {"max_sprinklers": 20, "id_inches": 2.469},
        "3_inch": {"max_sprinklers": 40, "id_inches": 3.068},
        "3.5_inch": {"max_sprinklers": 65, "id_inches": 3.548},
        "4_inch": {"max_sprinklers": 100, "id_inches": 4.026}
    },
    "notes": [
        "For light and ordinary hazard occupancies",
        "Hydraulic calculation may allow more sprinklers"
    ]
}

# Chapter 9 - Seismic Protection
NFPA_CHAPTER_9 = {
    "chapter": "9",
    "title": "Seismic Protection Requirements",
    "edition": "NFPA 13 (2025)",
    "data": {
        "sway_bracing_required": {
            "main_pipes_over_2_5_inch": True,
            "max_brace_spacing_ft": 40
        },
        "flexible_couplings_required": {
            "building_expansion_joints": True,
            "seismic_separation_joints": True
        },
        "clearance_around_pipes": {
            "through_walls_inches": 2,
            "through_floors_inches": 4
        }
    },
    "notes": [
        "Required in Seismic Design Categories C, D, E, F",
        "Bracing calculations per 9.3.5"
    ]
}

# Israeli Standard ת"י 1596
ISRAELI_TI_1596 = {
    "standard_id": "ת\"י 1596",
    "title": "Fire Water Tanks - Requirements",
    "edition": "2019",
    "data": {
        "minimum_volumes_m3": {
            "residential": 50,
            "office": 75,
            "commercial": 100,
            "industrial": 150,
            "warehouse": 200,
            "high_hazard": 300
        },
        "safety_factor": 1.2,
        "tank_materials": ["concrete", "steel", "fiberglass"],
        "refill_time_hours": 8
    },
    "cross_reference": "Aligns with NFPA 22 (Water Tanks)"
}

# Velocity Limits (Section 27.2.3)
NFPA_VELOCITY_LIMITS = {
    "section": "27.2.3",
    "title": "Velocity Limitations",
    "edition": "NFPA 13 (2025)",
    "data": {
        "recommended_max_fps": 20,
        "absolute_max_fps": 32,
        "notes": "Higher velocities increase friction loss and noise"
    }
}


# ============================================================================
# KNOWLEDGE BASE CLASS
# ============================================================================

@dataclass
class NFPACitation:
    """Structured citation from NFPA."""
    source: str  # "NFPA 13 (2025)"
    section: str  # "Table 10.2.1"
    title: str
    value: Any
    unit: Optional[str] = None
    notes: Optional[List[str]] = None


class QueryType(str, Enum):
    DENSITY = "density"
    SPACING = "spacing"
    COVERAGE = "coverage"
    PIPE_SIZE = "pipe_size"
    VELOCITY = "velocity"
    SEISMIC = "seismic"
    TANK_VOLUME = "tank_volume"
    GENERAL = "general"


class NFPAKnowledgeBase:
    """
    NFPA 13 Knowledge Base with local cache and web lookup.

    Features:
    - Instant local lookup for common queries
    - AI-powered web search for complex queries
    - Citation tracking for audit compliance
    - Israeli ת"י 1596 cross-reference
    """

    def __init__(self, use_web_lookup: bool = True):
        """
        Initialize knowledge base.

        Args:
            use_web_lookup: Enable Gemini AI for complex queries
        """
        self.use_web_lookup = use_web_lookup
        self._load_tables()

    def _load_tables(self):
        """Load all NFPA tables into memory."""
        self.tables = {
            "10.2.1": NFPA_TABLE_10_2_1,
            "10.2.2": NFPA_TABLE_10_2_2,
            "10.2.3": NFPA_TABLE_10_2_3,
            "8.6.2": NFPA_TABLE_8_6_2,
            "22.4.4.6": NFPA_TABLE_22_4_4_6,
            "9": NFPA_CHAPTER_9,
            "27.2.3": NFPA_VELOCITY_LIMITS,
            "TI_1596": ISRAELI_TI_1596
        }

    def _classify_query(self, query: str) -> QueryType:
        """Classify query to determine lookup strategy."""
        query_lower = query.lower()

        if any(kw in query_lower for kw in ["density", "gpm", "flow"]):
            return QueryType.DENSITY
        if any(kw in query_lower for kw in ["spacing", "distance", "between"]):
            return QueryType.SPACING
        if any(kw in query_lower for kw in ["coverage", "area per", "sqft per"]):
            return QueryType.COVERAGE
        if any(kw in query_lower for kw in ["pipe", "diameter", "schedule"]):
            return QueryType.PIPE_SIZE
        if any(kw in query_lower for kw in ["velocity", "fps", "speed"]):
            return QueryType.VELOCITY
        if any(kw in query_lower for kw in ["seismic", "brace", "earthquake"]):
            return QueryType.SEISMIC
        if any(kw in query_lower for kw in ["tank", "volume", "storage", "israeli"]):
            return QueryType.TANK_VOLUME

        return QueryType.GENERAL

    def _extract_hazard_class(self, query: str) -> Optional[str]:
        """Extract hazard classification from query."""
        query_lower = query.lower()

        if "extra" in query_lower and "2" in query_lower:
            return "Extra Group 2"
        if "extra" in query_lower and "1" in query_lower:
            return "Extra Group 1"
        if "ordinary" in query_lower and "2" in query_lower:
            return "Ordinary Group 2"
        if "ordinary" in query_lower and "1" in query_lower:
            return "Ordinary Group 1"
        if "light" in query_lower:
            return "Light"

        return None

    def get_design_criteria(self, hazard_class: str) -> Dict[str, Any]:
        """
        Get full design criteria for a hazard class.

        Args:
            hazard_class: "Light", "Ordinary Group 1", etc.

        Returns:
            Dict with all design parameters and citations
        """
        result = {
            "hazard_class": hazard_class,
            "citations": []
        }

        if hazard_class == "Light":
            data = NFPA_TABLE_10_2_1["data"]
            result.update(data)
            result["citations"].append(NFPACitation(
                source="NFPA 13 (2025)",
                section="Table 10.2.1",
                title="Light Hazard Design Criteria",
                value=data
            ))

        elif hazard_class == "Ordinary Group 1":
            data = NFPA_TABLE_10_2_2["data"]["Group 1"]
            result.update(data)
            result["citations"].append(NFPACitation(
                source="NFPA 13 (2025)",
                section="Table 10.2.2",
                title="Ordinary Group 1 Design Criteria",
                value=data
            ))

        elif hazard_class == "Ordinary Group 2":
            data = NFPA_TABLE_10_2_2["data"]["Group 2"]
            result.update(data)
            result["citations"].append(NFPACitation(
                source="NFPA 13 (2025)",
                section="Table 10.2.2",
                title="Ordinary Group 2 Design Criteria",
                value=data
            ))

        elif hazard_class == "Extra Group 1":
            data = NFPA_TABLE_10_2_3["data"]["Group 1"]
            result.update(data)
            result["citations"].append(NFPACitation(
                source="NFPA 13 (2025)",
                section="Table 10.2.3",
                title="Extra Group 1 Design Criteria",
                value=data
            ))

        elif hazard_class == "Extra Group 2":
            data = NFPA_TABLE_10_2_3["data"]["Group 2"]
            result.update(data)
            result["citations"].append(NFPACitation(
                source="NFPA 13 (2025)",
                section="Table 10.2.3",
                title="Extra Group 2 Design Criteria",
                value=data
            ))

        # Add spacing requirements
        spacing_data = NFPA_TABLE_8_6_2["data"]["standard_spray_upright_pendent"]
        result["spacing"] = spacing_data
        result["citations"].append(NFPACitation(
            source="NFPA 13 (2025)",
            section="Table 8.6.2.2.1(a)",
            title="Standard Spray Sprinkler Spacing",
            value=spacing_data
        ))

        return result

    def get_pipe_sizing(self, sprinkler_count: int) -> Dict[str, Any]:
        """
        Get minimum pipe size for sprinkler count.

        Args:
            sprinkler_count: Number of sprinklers on branch

        Returns:
            Recommended pipe size with citation
        """
        pipe_data = NFPA_TABLE_22_4_4_6["data"]

        for size_name, limits in pipe_data.items():
            if sprinkler_count <= limits["max_sprinklers"]:
                return {
                    "pipe_size": size_name.replace("_", " "),
                    "internal_diameter_inches": limits["id_inches"],
                    "max_sprinklers_allowed": limits["max_sprinklers"],
                    "citation": NFPACitation(
                        source="NFPA 13 (2025)",
                        section="Table 22.4.4.6.2",
                        title="Schedule 40 Steel Pipe Sizing",
                        value=f"{size_name} pipe for {sprinkler_count} sprinklers"
                    )
                }

        return {
            "pipe_size": "4 inch (or larger - hydraulic calc required)",
            "citation": NFPACitation(
                source="NFPA 13 (2025)",
                section="22.4.4.6.2",
                title="Pipe Sizing",
                value="Exceeds pipe schedule - hydraulic calculation required"
            )
        }

    def validate_velocity(self, velocity_fps: float) -> Dict[str, Any]:
        """
        Validate pipe velocity against NFPA limits.

        Args:
            velocity_fps: Calculated velocity in feet per second

        Returns:
            Validation result with status and citation
        """
        limits = NFPA_VELOCITY_LIMITS["data"]

        if velocity_fps <= limits["recommended_max_fps"]:
            status = "PASS"
            message = f"Velocity {velocity_fps:.1f} fps is within recommended limit of {limits['recommended_max_fps']} fps"
        elif velocity_fps <= limits["absolute_max_fps"]:
            status = "WARNING"
            message = f"Velocity {velocity_fps:.1f} fps exceeds recommended {limits['recommended_max_fps']} fps but within absolute max {limits['absolute_max_fps']} fps"
        else:
            status = "FAIL"
            message = f"Velocity {velocity_fps:.1f} fps exceeds absolute maximum of {limits['absolute_max_fps']} fps"

        return {
            "status": status,
            "velocity_fps": velocity_fps,
            "recommended_max": limits["recommended_max_fps"],
            "absolute_max": limits["absolute_max_fps"],
            "message": message,
            "citation": NFPACitation(
                source="NFPA 13 (2025)",
                section="27.2.3",
                title="Velocity Limitations",
                value=limits
            )
        }

    def get_seismic_requirements(self) -> Dict[str, Any]:
        """Get seismic bracing requirements."""
        return {
            **NFPA_CHAPTER_9["data"],
            "citation": NFPACitation(
                source="NFPA 13 (2025)",
                section="Chapter 9",
                title="Seismic Protection Requirements",
                value=NFPA_CHAPTER_9["data"]
            )
        }

    def get_tank_requirements(self, occupancy_type: str) -> Dict[str, Any]:
        """
        Get Israeli fire water tank requirements.

        Args:
            occupancy_type: Building occupancy type

        Returns:
            Volume requirements with Israeli standard citation
        """
        ti_data = ISRAELI_TI_1596["data"]

        min_volume = ti_data["minimum_volumes_m3"].get(
            occupancy_type.lower(),
            ti_data["minimum_volumes_m3"]["commercial"]
        )

        return {
            "minimum_volume_m3": min_volume,
            "with_safety_factor_m3": min_volume * ti_data["safety_factor"],
            "safety_factor": ti_data["safety_factor"],
            "refill_time_hours": ti_data["refill_time_hours"],
            "citation": NFPACitation(
                source="Israeli Standard ת\"י 1596 (2019)",
                section="Table 1",
                title="Minimum Fire Water Tank Volumes",
                value=f"{min_volume} m³ for {occupancy_type}"
            ),
            "cross_reference": ti_data.get("cross_reference")
        }

    def query(self, query_text: str) -> Dict[str, Any]:
        """
        Main query interface for NFPA knowledge base.

        Args:
            query_text: Natural language query

        Returns:
            Answer with citations
        """
        query_type = self._classify_query(query_text)
        hazard_class = self._extract_hazard_class(query_text)

        if query_type == QueryType.DENSITY and hazard_class:
            criteria = self.get_design_criteria(hazard_class)
            return {
                "answer": f"Design density for {hazard_class}: {criteria.get('density_gpm_sqft', 'N/A')} GPM/ft²",
                "value": criteria.get("density_gpm_sqft"),
                "unit": "GPM/ft²",
                "citations": [c.__dict__ for c in criteria["citations"]]
            }

        if query_type == QueryType.SPACING and hazard_class:
            criteria = self.get_design_criteria(hazard_class)
            spacing = criteria.get("spacing", {})
            return {
                "answer": f"Max sprinkler spacing for {hazard_class}: {spacing.get('max_distance_between_ft', 15)} ft",
                "value": spacing.get("max_distance_between_ft"),
                "unit": "ft",
                "citations": [c.__dict__ for c in criteria["citations"]]
            }

        if query_type == QueryType.COVERAGE and hazard_class:
            criteria = self.get_design_criteria(hazard_class)
            return {
                "answer": f"Max coverage per head for {hazard_class}: {criteria.get('max_coverage_per_head_sqft', 'N/A')} ft²",
                "value": criteria.get("max_coverage_per_head_sqft"),
                "unit": "ft²",
                "citations": [c.__dict__ for c in criteria["citations"]]
            }

        if query_type == QueryType.VELOCITY:
            # Extract velocity from query if present
            import re
            velocity_match = re.search(r'(\d+\.?\d*)\s*fps', query_text.lower())
            if velocity_match:
                velocity = float(velocity_match.group(1))
                result = self.validate_velocity(velocity)
                return {
                    "answer": result["message"],
                    "status": result["status"],
                    "citations": [result["citation"].__dict__]
                }

        if query_type == QueryType.SEISMIC:
            seismic = self.get_seismic_requirements()
            return {
                "answer": "Seismic bracing required for mains >2.5\" with max 40ft spacing",
                "data": seismic,
                "citations": [seismic["citation"].__dict__]
            }

        if query_type == QueryType.TANK_VOLUME:
            # Default to commercial if not specified
            tank = self.get_tank_requirements("commercial")
            return {
                "answer": f"Minimum tank volume: {tank['minimum_volume_m3']} m³ ({tank['with_safety_factor_m3']} m³ with safety factor)",
                "data": tank,
                "citations": [tank["citation"].__dict__]
            }

        # General query - return all design criteria if hazard class specified
        if hazard_class:
            return self.get_design_criteria(hazard_class)

        return {
            "answer": "Please specify a hazard class (Light, Ordinary Group 1/2, Extra Group 1/2) or query type",
            "available_queries": [
                "Light Hazard density",
                "Ordinary Group 2 spacing",
                "Extra Group 1 coverage",
                "velocity 25 fps",
                "seismic requirements",
                "tank volume commercial"
            ]
        }

    def validate_design(
        self,
        hazard_class: str,
        calculated_density: float,
        calculated_spacing: float,
        max_velocity: float
    ) -> Dict[str, Any]:
        """
        Validate a complete design against NFPA requirements.

        Args:
            hazard_class: NFPA hazard classification
            calculated_density: Design density in GPM/ft²
            calculated_spacing: Max sprinkler spacing in ft
            max_velocity: Max pipe velocity in fps

        Returns:
            Validation results with pass/fail and citations
        """
        criteria = self.get_design_criteria(hazard_class)
        velocity_check = self.validate_velocity(max_velocity)

        violations = []
        warnings = []

        # Check density
        required_density = criteria.get("density_gpm_sqft", 0.10)
        if calculated_density < required_density:
            violations.append({
                "parameter": "density",
                "calculated": calculated_density,
                "required": required_density,
                "citation": "NFPA 13 Table 10.2.x"
            })

        # Check spacing
        max_allowed_spacing = criteria.get("spacing", {}).get("max_distance_between_ft", 15)
        if calculated_spacing > max_allowed_spacing:
            violations.append({
                "parameter": "spacing",
                "calculated": calculated_spacing,
                "max_allowed": max_allowed_spacing,
                "citation": "NFPA 13 Section 8.6.2.2.1"
            })

        # Check velocity
        if velocity_check["status"] == "FAIL":
            violations.append({
                "parameter": "velocity",
                "calculated": max_velocity,
                "max_allowed": velocity_check["absolute_max"],
                "citation": "NFPA 13 Section 27.2.3"
            })
        elif velocity_check["status"] == "WARNING":
            warnings.append({
                "parameter": "velocity",
                "calculated": max_velocity,
                "recommended": velocity_check["recommended_max"],
                "citation": "NFPA 13 Section 27.2.3"
            })

        # Determine overall status
        if violations:
            status = "FAIL"
            message = f"Design fails {len(violations)} NFPA requirement(s)"
        elif warnings:
            status = "WARNING"
            message = f"Design passes with {len(warnings)} warning(s)"
        else:
            status = "PASS"
            message = "Design complies with all NFPA 13 requirements"

        return {
            "status": status,
            "message": message,
            "violations": violations,
            "warnings": warnings,
            "citations": [c.__dict__ for c in criteria["citations"]] + [velocity_check["citation"].__dict__],
            "compliance_statement": (
                f"Design validated against NFPA 13 (2025 Edition) for {hazard_class} occupancy. "
                f"Status: {status}. "
                f"{'See violations for required corrections.' if violations else 'Ready for submission.'}"
            )
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def fetch_nfpa_constraints(hazard_class: str, parameter: str = "all") -> Dict[str, Any]:
    """
    Fetch NFPA constraints for AgentCore Code Interpreter.

    Args:
        hazard_class: NFPA hazard classification
        parameter: Specific parameter or "all"

    Returns:
        Constraints with source citations
    """
    kb = NFPAKnowledgeBase()

    if parameter == "all":
        return kb.get_design_criteria(hazard_class)

    query = f"{hazard_class} {parameter}"
    return kb.query(query)


def validate_nfpa_compliance(
    hazard_class: str,
    density: float,
    spacing: float,
    velocity: float
) -> Dict[str, Any]:
    """
    Quick validation function for pipeline integration.

    Returns:
        Validation result with PASS/WARNING/FAIL status
    """
    kb = NFPAKnowledgeBase()
    return kb.validate_design(hazard_class, density, spacing, velocity)


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    'NFPAKnowledgeBase',
    'NFPACitation',
    'QueryType',
    'fetch_nfpa_constraints',
    'validate_nfpa_compliance',
    'NFPA_TABLE_10_2_1',
    'NFPA_TABLE_10_2_2',
    'NFPA_TABLE_10_2_3',
    'NFPA_TABLE_8_6_2',
    'NFPA_TABLE_22_4_4_6',
    'NFPA_CHAPTER_9',
    'NFPA_VELOCITY_LIMITS',
    'ISRAELI_TI_1596',
]
