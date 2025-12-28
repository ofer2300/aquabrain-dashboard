"""
AquaBrain Pipeline Executor V3.3
================================
Visual Workflow Execution Engine

Executes skill pipelines step-by-step, passing outputs between nodes.
Supports:
- Sequential execution with data flow
- Parallel node execution (when no dependencies)
- Real-time progress tracking
- Error handling and rollback

The heart of "Own the Factory" - users build automation workflows visually.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import asyncio
import uuid
from collections import defaultdict

from skills.base import (
    skill_registry,
    pipeline_registry,
    PipelineDefinition,
    PipelineNode,
    PipelineEdge,
    PipelineExecutionResult,
    PipelineExecutionStatus,
    PipelineNodeResult,
    ExecutionStatus,
)


class PipelineExecutor:
    """
    Executes skill pipelines with intelligent data flow.

    Features:
    - Topological sorting for execution order
    - Parallel execution of independent nodes
    - Data passing between connected nodes
    - Real-time progress callbacks
    """

    def __init__(self):
        self._active_runs: Dict[str, PipelineExecutionResult] = {}

    def get_execution_order(self, pipeline: PipelineDefinition) -> List[List[str]]:
        """
        Compute execution order using topological sort.
        Returns list of "levels" - nodes at same level can run in parallel.

        Example: [[A], [B, C], [D]] means:
        - First run A
        - Then B and C in parallel
        - Finally D
        """
        # Build adjacency and in-degree maps
        in_degree: Dict[str, int] = defaultdict(int)
        adjacency: Dict[str, List[str]] = defaultdict(list)
        node_ids = {node.id for node in pipeline.nodes}

        for node_id in node_ids:
            in_degree[node_id] = 0

        for edge in pipeline.edges:
            if edge.source in node_ids and edge.target in node_ids:
                adjacency[edge.source].append(edge.target)
                in_degree[edge.target] += 1

        # Kahn's algorithm with level tracking
        levels: List[List[str]] = []
        current_level = [n for n in node_ids if in_degree[n] == 0]

        while current_level:
            levels.append(sorted(current_level))  # Sort for determinism
            next_level = []

            for node_id in current_level:
                for neighbor in adjacency[node_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_level.append(neighbor)

            current_level = next_level

        return levels

    def resolve_inputs(
        self,
        node: PipelineNode,
        node_outputs: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Resolve inputs for a node by combining static inputs and mapped outputs.

        Args:
            node: The node to resolve inputs for
            node_outputs: Dict of {node_id: {output_key: value}}

        Returns:
            Merged inputs dictionary
        """
        inputs = dict(node.inputs)  # Start with static inputs

        # Apply mappings from previous node outputs
        for local_key, mapping in node.input_mappings.items():
            # Mapping format: "source_node_id.output_key"
            if "." in mapping:
                source_node, output_key = mapping.rsplit(".", 1)
                if source_node in node_outputs:
                    source_outputs = node_outputs[source_node]
                    if output_key in source_outputs:
                        inputs[local_key] = source_outputs[output_key]
            else:
                # Direct reference to node output (full object)
                if mapping in node_outputs:
                    inputs[local_key] = node_outputs[mapping]

        return inputs

    async def execute_node(
        self,
        node: PipelineNode,
        resolved_inputs: Dict[str, Any],
    ) -> PipelineNodeResult:
        """Execute a single pipeline node."""
        start_time = datetime.now()

        # Get the skill
        skill = skill_registry.get(node.skill_id)
        if not skill:
            return PipelineNodeResult(
                node_id=node.id,
                skill_id=node.skill_id,
                status=ExecutionStatus.FAILED,
                started_at=start_time,
                completed_at=datetime.now(),
                error=f"Skill '{node.skill_id}' not found in registry",
            )

        # Execute the skill
        try:
            result = skill.safe_execute(resolved_inputs)

            return PipelineNodeResult(
                node_id=node.id,
                skill_id=node.skill_id,
                status=result.status,
                started_at=start_time,
                completed_at=result.completed_at or datetime.now(),
                duration_ms=result.duration_ms,
                output=result.output,
                error=result.error,
            )
        except Exception as e:
            return PipelineNodeResult(
                node_id=node.id,
                skill_id=node.skill_id,
                status=ExecutionStatus.FAILED,
                started_at=start_time,
                completed_at=datetime.now(),
                error=str(e),
            )

    async def execute(
        self,
        pipeline: PipelineDefinition,
        initial_inputs: Optional[Dict[str, Any]] = None,
        on_progress: Optional[callable] = None,
    ) -> PipelineExecutionResult:
        """
        Execute a complete pipeline.

        Args:
            pipeline: The pipeline definition
            initial_inputs: Optional inputs to inject into first nodes
            on_progress: Callback for progress updates

        Returns:
            Complete execution result
        """
        run_id = str(uuid.uuid4())
        start_time = datetime.now()

        result = PipelineExecutionResult(
            pipeline_id=pipeline.id,
            run_id=run_id,
            status=PipelineExecutionStatus.RUNNING,
            started_at=start_time,
        )

        self._active_runs[run_id] = result

        try:
            # Get execution order
            execution_levels = self.get_execution_order(pipeline)

            if not execution_levels:
                result.status = PipelineExecutionStatus.COMPLETED
                result.completed_at = datetime.now()
                result.progress_percent = 100.0
                return result

            # Node lookup map
            nodes_map = {node.id: node for node in pipeline.nodes}

            # Track outputs from each node
            node_outputs: Dict[str, Dict[str, Any]] = {}

            # Inject initial inputs as "virtual" node output
            if initial_inputs:
                node_outputs["_initial"] = initial_inputs

            total_nodes = len(pipeline.nodes)
            completed_nodes = 0

            # Execute level by level
            for level in execution_levels:
                level_tasks = []

                for node_id in level:
                    node = nodes_map.get(node_id)
                    if not node:
                        continue

                    # Resolve inputs for this node
                    resolved_inputs = self.resolve_inputs(node, node_outputs)

                    # Add initial inputs if this is a root node
                    if initial_inputs and not any(
                        e.target == node_id for e in pipeline.edges
                    ):
                        resolved_inputs = {**initial_inputs, **resolved_inputs}

                    result.current_node = node_id

                    # Execute node
                    level_tasks.append(
                        self.execute_node(node, resolved_inputs)
                    )

                # Run all nodes in this level (could be parallel)
                if level_tasks:
                    level_results = await asyncio.gather(*level_tasks)

                    for node_result in level_results:
                        result.node_results.append(node_result)

                        # Store outputs for next level
                        if node_result.output:
                            node_outputs[node_result.node_id] = node_result.output

                        # Check for failure
                        if node_result.status == ExecutionStatus.FAILED:
                            result.status = PipelineExecutionStatus.FAILED
                            result.error = node_result.error
                            result.error_node = node_result.node_id
                            result.completed_at = datetime.now()
                            result.total_duration_ms = int(
                                (result.completed_at - start_time).total_seconds() * 1000
                            )
                            return result

                        completed_nodes += 1
                        result.progress_percent = (completed_nodes / total_nodes) * 100

                        if on_progress:
                            on_progress(result)

            # Success - get final output from last executed node
            if result.node_results:
                last_result = result.node_results[-1]
                result.final_output = last_result.output

            result.status = PipelineExecutionStatus.COMPLETED
            result.completed_at = datetime.now()
            result.total_duration_ms = int(
                (result.completed_at - start_time).total_seconds() * 1000
            )
            result.progress_percent = 100.0
            result.current_node = None

            return result

        except Exception as e:
            result.status = PipelineExecutionStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.now()
            result.total_duration_ms = int(
                (result.completed_at - start_time).total_seconds() * 1000
            )
            return result

        finally:
            # Clean up active run
            if run_id in self._active_runs:
                del self._active_runs[run_id]

    def get_run_status(self, run_id: str) -> Optional[PipelineExecutionResult]:
        """Get status of an active run."""
        return self._active_runs.get(run_id)

    def cancel_run(self, run_id: str) -> bool:
        """Cancel an active run."""
        if run_id in self._active_runs:
            self._active_runs[run_id].status = PipelineExecutionStatus.CANCELLED
            return True
        return False


# Global executor instance
_executor: Optional[PipelineExecutor] = None


def get_executor() -> PipelineExecutor:
    """Get or create the global executor."""
    global _executor
    if _executor is None:
        _executor = PipelineExecutor()
    return _executor


async def execute_pipeline(
    pipeline_id: str,
    initial_inputs: Optional[Dict[str, Any]] = None,
) -> PipelineExecutionResult:
    """
    Execute a saved pipeline by ID.

    Convenience function for API use.
    """
    pipeline = pipeline_registry.get(pipeline_id)
    if not pipeline:
        return PipelineExecutionResult(
            pipeline_id=pipeline_id,
            status=PipelineExecutionStatus.FAILED,
            error=f"Pipeline '{pipeline_id}' not found",
        )

    executor = get_executor()
    return await executor.execute(pipeline, initial_inputs)


async def execute_pipeline_definition(
    pipeline: PipelineDefinition,
    initial_inputs: Optional[Dict[str, Any]] = None,
) -> PipelineExecutionResult:
    """
    Execute a pipeline definition directly (without saving).

    Useful for one-off executions or testing.
    """
    executor = get_executor()
    return await executor.execute(pipeline, initial_inputs)


# ============================================================================
# PRESET PIPELINES
# ============================================================================

def create_engineering_pipeline() -> PipelineDefinition:
    """
    Create the standard AquaBrain engineering pipeline.

    Flow: Revit Extract → Hydraulic Calc → Report Generator
    """
    return PipelineDefinition(
        id="pipeline_engineering_standard",
        name="Full Engineering Pipeline",
        description="Complete flow: Extract from Revit → Calculate hydraulics → Generate report",
        category="engineering",
        icon="Workflow",
        color="#4FACFE",
        tags=["engineering", "revit", "hydraulics", "report"],
        nodes=[
            PipelineNode(
                id="node_extract",
                skill_id="builtin_revit_extract",
                inputs={"project_id": "current"},
                position={"x": 100, "y": 100},
            ),
            PipelineNode(
                id="node_hydraulic",
                skill_id="builtin_hydraulic",
                input_mappings={
                    "pipe_data": "node_extract.pipes",
                },
                position={"x": 400, "y": 100},
            ),
            PipelineNode(
                id="node_report",
                skill_id="builtin_report_gen",
                input_mappings={
                    "calculation_results": "node_hydraulic.results",
                    "project_data": "node_extract.project",
                },
                position={"x": 700, "y": 100},
            ),
        ],
        edges=[
            PipelineEdge(
                id="edge_1",
                source="node_extract",
                target="node_hydraulic",
            ),
            PipelineEdge(
                id="edge_2",
                source="node_hydraulic",
                target="node_report",
            ),
            PipelineEdge(
                id="edge_3",
                source="node_extract",
                target="node_report",
            ),
        ],
    )


def register_preset_pipelines():
    """Register preset pipelines on startup."""
    preset_pipelines = [
        create_engineering_pipeline(),
    ]

    for pipeline in preset_pipelines:
        pipeline_registry.save(pipeline)
