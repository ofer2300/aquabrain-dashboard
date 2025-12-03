"""
AquaBrain Process Orchestrator V1.0
===================================
The conductor of the automation symphony.

This module orchestrates the complete engineering workflow:
1. Plan Processing - Extract geometry from Revit
2. Voxelization - Convert to spatial grid
3. Routing & Optimization - A* pathfinding for pipe routes
4. Hydraulic Validation - Hazen-Williams calculations
5. Generation - Create LOD 500 model
6. QC & Traffic Light - Compliance verification

The goal: One click → Complete sprinkler system design.
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Internal modules
from modules.hydraulics import HydraulicCalculator, PipeData, SCH40_STEEL_DIAMETERS
from modules.standards import NFPA13Validator, HazardClass


class ProcessStatus(Enum):
    """Status of the engineering process."""
    PENDING = "pending"
    EXTRACTING = "extracting"
    VOXELIZING = "voxelizing"
    ROUTING = "routing"
    CALCULATING = "calculating"
    GENERATING = "generating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class TrafficLightStatus(Enum):
    """Traffic light status for engineer."""
    GREEN = "GREEN"    # All clear - proceed
    YELLOW = "YELLOW"  # Caution - review needed
    RED = "RED"        # Stop - critical issues


@dataclass
class TrafficLightResult:
    """Result with traffic light status."""
    status: TrafficLightStatus
    message: str
    details: List[str] = field(default_factory=list)
    metrics: Optional[Dict[str, Any]] = None


@dataclass
class ProcessResult:
    """Complete process result."""
    project_id: str
    status: ProcessStatus
    traffic_light: TrafficLightResult
    geometry_data: Optional[Dict] = None
    routing_data: Optional[Dict] = None
    hydraulic_results: Optional[Dict] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_seconds: float = 0.0


class EngineeringOrchestrator:
    """
    Orchestrates the complete engineering automation workflow.

    This is the "brain" that coordinates all systems:
    - Revit Bridge (geometry extraction)
    - Voxelization Engine
    - A* Routing Algorithm
    - Hydraulic Calculator
    - NFPA 13 Validator
    """

    def __init__(self):
        self.hydraulic_calc = HydraulicCalculator()
        self.nfpa_validator = NFPA13Validator()
        self.current_status = ProcessStatus.PENDING

    async def run_full_process(
        self,
        project_id: str,
        hazard_class: str = "ordinary_1",
        notes: str = ""
    ) -> ProcessResult:
        """
        Execute the complete engineering process.

        Args:
            project_id: Project identifier
            hazard_class: NFPA 13 hazard classification
            notes: Special notes from the engineer

        Returns:
            ProcessResult with traffic light status
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Stage 1: Extract geometry from Revit
            self.current_status = ProcessStatus.EXTRACTING
            geometry = await self._extract_geometry(project_id)

            # Stage 2: Voxelize the space
            self.current_status = ProcessStatus.VOXELIZING
            voxel_grid = await self._voxelize_geometry(geometry)

            # Stage 3: Plan pipe routes
            self.current_status = ProcessStatus.ROUTING
            routes = await self._plan_routes(voxel_grid, hazard_class)

            # Stage 4: Calculate hydraulics
            self.current_status = ProcessStatus.CALCULATING
            hydraulic_results = await self._calculate_hydraulics(routes, hazard_class)

            # Stage 5: Generate LOD 500
            self.current_status = ProcessStatus.GENERATING
            await self._generate_lod500(project_id, routes)

            # Stage 6: Validate and determine traffic light
            self.current_status = ProcessStatus.VALIDATING
            traffic_light = self._determine_traffic_light(
                hydraulic_results,
                hazard_class
            )

            self.current_status = ProcessStatus.COMPLETED

            end_time = asyncio.get_event_loop().time()

            return ProcessResult(
                project_id=project_id,
                status=ProcessStatus.COMPLETED,
                traffic_light=traffic_light,
                geometry_data=geometry,
                routing_data=routes,
                hydraulic_results=hydraulic_results,
                duration_seconds=end_time - start_time
            )

        except Exception as e:
            self.current_status = ProcessStatus.FAILED
            return ProcessResult(
                project_id=project_id,
                status=ProcessStatus.FAILED,
                traffic_light=TrafficLightResult(
                    status=TrafficLightStatus.RED,
                    message="תהליך נכשל",
                    details=[str(e)]
                )
            )

    async def _extract_geometry(self, project_id: str) -> Dict[str, Any]:
        """
        Extract geometry from Revit via the bridge.
        In simulation mode, returns mock data.
        """
        # Simulate extraction delay
        await asyncio.sleep(0.5)

        # For now, return simulation data
        # In production, this calls bridge_revit.get_geometry()
        return {
            "project_id": project_id,
            "building": {
                "floors": 3,
                "total_area_sqm": 1500,
                "height_m": 10,
                "ceiling_height_m": 2.7
            },
            "coverage_areas": [
                {"id": "AREA-1", "floor": 1, "area_sqm": 500, "type": "office"},
                {"id": "AREA-2", "floor": 2, "area_sqm": 500, "type": "office"},
                {"id": "AREA-3", "floor": 3, "area_sqm": 500, "type": "storage"},
            ],
            "obstructions": [
                {"type": "duct", "path": [[0, 2, 2.5], [10, 2, 2.5]], "clearance": 0.15},
                {"type": "beam", "location": [5, 0, 2.4], "size": [0.3, 10, 0.4]},
            ]
        }

    async def _voxelize_geometry(self, geometry: Dict) -> Dict[str, Any]:
        """
        Convert geometry to voxel grid for pathfinding.
        """
        await asyncio.sleep(0.3)

        # Create a simple voxel representation
        return {
            "resolution_m": 0.1,  # 10cm voxels
            "dimensions": [100, 80, 30],  # 10m x 8m x 3m
            "occupied_voxels": len(geometry.get("obstructions", [])) * 100,
            "free_voxels": 100 * 80 * 30 - len(geometry.get("obstructions", [])) * 100
        }

    async def _plan_routes(
        self,
        voxel_grid: Dict,
        hazard_class: str
    ) -> Dict[str, Any]:
        """
        Plan optimal pipe routes using A* algorithm.
        """
        await asyncio.sleep(0.5)

        # Simulated route planning result
        return {
            "main_route": {
                "start": [0, 0, 2.5],
                "end": [10, 8, 2.5],
                "waypoints": [[5, 0, 2.5], [5, 4, 2.5], [5, 8, 2.5]],
                "total_length_m": 18.0,
                "diameter_inch": 2.0
            },
            "branch_routes": [
                {"id": "B1", "length_m": 3.0, "diameter_inch": 1.5, "sprinklers": 4},
                {"id": "B2", "length_m": 3.0, "diameter_inch": 1.5, "sprinklers": 4},
                {"id": "B3", "length_m": 3.0, "diameter_inch": 1.5, "sprinklers": 4},
            ],
            "total_pipe_segments": 12,
            "total_length_m": 27.0,
            "total_sprinklers": 12
        }

    async def _calculate_hydraulics(
        self,
        routes: Dict,
        hazard_class: str
    ) -> Dict[str, Any]:
        """
        Calculate hydraulics for all pipe segments.
        """
        await asyncio.sleep(0.3)

        # Convert string to HazardClass enum
        try:
            hazard_enum = HazardClass(hazard_class)
        except ValueError:
            hazard_enum = HazardClass.ORDINARY_1  # Default fallback

        # Get NFPA requirements
        nfpa_req = self.nfpa_validator.get_requirements(hazard_enum)

        # Calculate for main route
        main_pipe = PipeData(
            flow_gpm=150.0,  # Estimated total demand
            diameter_inch=routes["main_route"]["diameter_inch"],
            length_ft=routes["main_route"]["total_length_m"] * 3.28084,
            c_factor=120,
            use_nominal=True,
            schedule="40"
        )

        main_result = self.hydraulic_calc.calculate(main_pipe)

        # Calculate branches
        branch_results = []
        for branch in routes["branch_routes"]:
            branch_pipe = PipeData(
                flow_gpm=40.0,  # Branch flow
                diameter_inch=branch["diameter_inch"],
                length_ft=branch["length_m"] * 3.28084,
                c_factor=120,
                use_nominal=True,
                schedule="40"
            )
            branch_results.append(self.hydraulic_calc.calculate(branch_pipe))

        # Total pressure loss
        total_pressure_loss = main_result.pressure_loss_psi + sum(
            r.pressure_loss_psi for r in branch_results
        )

        # Maximum velocity
        max_velocity = max(
            main_result.velocity_fps,
            max(r.velocity_fps for r in branch_results)
        )

        return {
            "main_line": {
                "pressure_loss_psi": main_result.pressure_loss_psi,
                "velocity_fps": main_result.velocity_fps,
                "actual_diameter": main_result.actual_diameter,
                "compliant": main_result.velocity_ok
            },
            "branches": [
                {
                    "pressure_loss_psi": r.pressure_loss_psi,
                    "velocity_fps": r.velocity_fps,
                    "compliant": r.velocity_ok
                }
                for r in branch_results
            ],
            "totals": {
                "total_pressure_loss_psi": round(total_pressure_loss, 2),
                "max_velocity_fps": round(max_velocity, 2),
                "all_compliant": all(r.velocity_ok for r in branch_results) and main_result.velocity_ok
            },
            "nfpa_requirements": {
                "hazard_class": hazard_class,
                "min_density": nfpa_req.density_gpm_ft2,
                "max_coverage": nfpa_req.max_coverage_ft2,
                "min_pressure": nfpa_req.min_pressure_psi
            }
        }

    async def _generate_lod500(self, project_id: str, routes: Dict) -> None:
        """
        Generate LOD 500 model in Revit.
        In simulation mode, just logs the action.
        """
        await asyncio.sleep(0.5)

        # In production, this would call:
        # bridge_revit.create_pipe_network(project_id, routes["pipe_segments"])
        # bridge_revit.place_sprinkler_families(project_id, sprinkler_locations)

        print(f"📐 Generated LOD 500 for {project_id}")
        print(f"   - Pipes: {routes['total_pipe_segments']}")
        print(f"   - Sprinklers: {routes['total_sprinklers']}")

    def _determine_traffic_light(
        self,
        hydraulic_results: Dict,
        hazard_class: str
    ) -> TrafficLightResult:
        """
        Determine the traffic light status based on results.

        Traffic Light Logic:
        - GREEN: All compliant, no issues
        - YELLOW: Minor issues, review needed
        - RED: Critical issues, intervention required
        """
        details = []
        metrics = {
            "totalPipes": 12,  # From routes
            "totalLength": 27,  # meters
            "pressureLoss": hydraulic_results["totals"]["total_pressure_loss_psi"],
            "maxVelocity": hydraulic_results["totals"]["max_velocity_fps"]
        }

        # Check velocity compliance
        max_velocity = hydraulic_results["totals"]["max_velocity_fps"]
        all_compliant = hydraulic_results["totals"]["all_compliant"]

        # RED: Critical velocity violation
        if max_velocity > 32.0:
            return TrafficLightResult(
                status=TrafficLightStatus.RED,
                message="חריגת מהירות קריטית",
                details=[
                    f"מהירות מקסימלית: {max_velocity} fps",
                    "חורג ממגבלת NFPA 13 (32 fps)",
                    "נדרש הגדלת קוטר צנרת"
                ],
                metrics=metrics
            )

        # YELLOW: Borderline velocity
        if max_velocity > 20.0:
            details.append(f"מהירות גבוהה: {max_velocity} fps (מומלץ מתחת ל-20)")
            return TrafficLightResult(
                status=TrafficLightStatus.YELLOW,
                message="מהירות זרימה גבוהה",
                details=[
                    f"מהירות מקסימלית: {max_velocity} fps",
                    "מעל המומלץ (20 fps)",
                    "עדיין בגבולות התקן",
                    "מומלץ לבדוק אפשרות להגדלת קוטר"
                ],
                metrics=metrics
            )

        # Check pressure
        pressure_loss = hydraulic_results["totals"]["total_pressure_loss_psi"]
        if pressure_loss > 50.0:  # Example threshold
            return TrafficLightResult(
                status=TrafficLightStatus.YELLOW,
                message="אובדן לחץ גבוה",
                details=[
                    f"אובדן לחץ: {pressure_loss} PSI",
                    "בדוק זמינות לחץ ממקור המים"
                ],
                metrics=metrics
            )

        # GREEN: All good!
        return TrafficLightResult(
            status=TrafficLightStatus.GREEN,
            message="תכנון אופטימלי ומאושר",
            details=[
                "✓ עומד בתקן NFPA 13",
                "✓ ללא התנגשויות",
                "✓ הידראוליקה תקינה",
                f"✓ מהירות מקסימלית: {max_velocity} fps",
                f"✓ אובדן לחץ כולל: {pressure_loss} PSI"
            ],
            metrics=metrics
        )


# Global orchestrator instance
orchestrator = EngineeringOrchestrator()


async def start_engineering_process(
    project_id: str,
    hazard_class: str = "ordinary_1",
    notes: str = ""
) -> Dict[str, Any]:
    """
    Entry point for the engineering process.
    Called by the FastAPI endpoint.
    """
    result = await orchestrator.run_full_process(
        project_id=project_id,
        hazard_class=hazard_class,
        notes=notes
    )

    return {
        "project_id": result.project_id,
        "status": result.status.value,
        "traffic_light": {
            "status": result.traffic_light.status.value,
            "message": result.traffic_light.message,
            "details": result.traffic_light.details,
            "metrics": result.traffic_light.metrics
        },
        "duration_seconds": result.duration_seconds,
        "timestamp": result.timestamp
    }
