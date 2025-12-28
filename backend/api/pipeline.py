"""
AquaBrain Pipeline API V3.3
===========================
Visual Workflow Builder API

Endpoints:
- POST /api/pipelines - Create new pipeline
- GET /api/pipelines - List all pipelines
- GET /api/pipelines/{id} - Get pipeline details
- PUT /api/pipelines/{id} - Update pipeline
- DELETE /api/pipelines/{id} - Delete pipeline
- POST /api/pipelines/{id}/execute - Execute a pipeline
- POST /api/pipelines/execute-inline - Execute pipeline definition directly
- GET /api/pipelines/runs/{run_id} - Get run status
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from skills.base import (
    pipeline_registry,
    PipelineDefinition,
    PipelineNode,
    PipelineEdge,
    PipelineExecutionResult,
    PipelineExecutionStatus,
)
from services.pipeline import (
    get_executor,
    execute_pipeline,
    execute_pipeline_definition,
    register_preset_pipelines,
)

router = APIRouter(prefix="/api/pipelines", tags=["Pipeline Builder"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class PipelineNodeRequest(BaseModel):
    """Node in a pipeline request."""
    id: str
    skill_id: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    input_mappings: Dict[str, str] = Field(default_factory=dict)
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})


class PipelineEdgeRequest(BaseModel):
    """Edge in a pipeline request."""
    id: str
    source: str
    target: str
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None


class CreatePipelineRequest(BaseModel):
    """Request to create a new pipeline."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    nodes: List[PipelineNodeRequest] = Field(default_factory=list)
    edges: List[PipelineEdgeRequest] = Field(default_factory=list)
    category: str = Field(default="custom")
    icon: str = Field(default="GitBranch")
    color: str = Field(default="#9B59B6")
    tags: List[str] = Field(default_factory=list)


class UpdatePipelineRequest(BaseModel):
    """Request to update a pipeline."""
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[PipelineNodeRequest]] = None
    edges: Optional[List[PipelineEdgeRequest]] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    tags: Optional[List[str]] = None


class ExecutePipelineRequest(BaseModel):
    """Request to execute a pipeline."""
    initial_inputs: Dict[str, Any] = Field(default_factory=dict)
    async_mode: bool = Field(default=False, description="Run in background")


class PipelineResponse(BaseModel):
    """Pipeline response model."""
    id: str
    name: str
    description: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    category: str
    icon: str
    color: str
    tags: List[str]
    created_at: str
    updated_at: str
    version: str


class ExecutionResponse(BaseModel):
    """Execution result response."""
    run_id: str
    pipeline_id: str
    status: str
    progress_percent: float
    current_node: Optional[str]
    node_results: List[Dict[str, Any]]
    final_output: Optional[Dict[str, Any]]
    error: Optional[str]
    error_node: Optional[str]
    started_at: str
    completed_at: Optional[str]
    total_duration_ms: Optional[int]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.on_event("startup")
async def startup():
    """Register preset pipelines on startup."""
    register_preset_pipelines()


@router.post("", response_model=PipelineResponse)
async def create_pipeline(request: CreatePipelineRequest):
    """
    📐 Create a New Pipeline

    Define a visual workflow by specifying nodes (skills) and edges (connections).

    Example:
    ```json
    {
        "name": "My Engineering Flow",
        "description": "Extract → Calculate → Report",
        "nodes": [
            {"id": "n1", "skill_id": "builtin_revit_extract", "position": {"x": 100, "y": 100}},
            {"id": "n2", "skill_id": "builtin_hydraulic", "input_mappings": {"pipe_data": "n1.pipes"}, "position": {"x": 400, "y": 100}}
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2"}
        ]
    }
    ```
    """
    # Convert request to pipeline definition
    pipeline = PipelineDefinition(
        name=request.name,
        description=request.description,
        nodes=[
            PipelineNode(**node.model_dump())
            for node in request.nodes
        ],
        edges=[
            PipelineEdge(**edge.model_dump())
            for edge in request.edges
        ],
        category=request.category,
        icon=request.icon,
        color=request.color,
        tags=request.tags,
    )

    # Save to registry
    pipeline_registry.save(pipeline)

    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        description=pipeline.description,
        nodes=[n.model_dump() for n in pipeline.nodes],
        edges=[e.model_dump() for e in pipeline.edges],
        category=pipeline.category,
        icon=pipeline.icon,
        color=pipeline.color,
        tags=pipeline.tags,
        created_at=pipeline.created_at.isoformat(),
        updated_at=pipeline.updated_at.isoformat(),
        version=pipeline.version,
    )


@router.get("")
async def list_pipelines():
    """
    📋 List All Pipelines

    Returns all saved pipelines with metadata.
    """
    pipelines = pipeline_registry.list_all()

    return {
        "pipelines": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "category": p.category,
                "icon": p.icon,
                "color": p.color,
                "tags": p.tags,
                "node_count": len(p.nodes),
                "edge_count": len(p.edges),
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in pipelines
        ],
        "total": len(pipelines),
    }


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(pipeline_id: str):
    """
    🔍 Get Pipeline Details

    Returns full pipeline definition including all nodes and edges.
    """
    pipeline = pipeline_registry.get(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")

    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        description=pipeline.description,
        nodes=[n.model_dump() for n in pipeline.nodes],
        edges=[e.model_dump() for e in pipeline.edges],
        category=pipeline.category,
        icon=pipeline.icon,
        color=pipeline.color,
        tags=pipeline.tags,
        created_at=pipeline.created_at.isoformat(),
        updated_at=pipeline.updated_at.isoformat(),
        version=pipeline.version,
    )


@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(pipeline_id: str, request: UpdatePipelineRequest):
    """
    ✏️ Update Pipeline

    Update pipeline definition. Only provided fields are updated.
    """
    pipeline = pipeline_registry.get(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")

    # Update fields
    if request.name is not None:
        pipeline.name = request.name
    if request.description is not None:
        pipeline.description = request.description
    if request.nodes is not None:
        pipeline.nodes = [PipelineNode(**n.model_dump()) for n in request.nodes]
    if request.edges is not None:
        pipeline.edges = [PipelineEdge(**e.model_dump()) for e in request.edges]
    if request.category is not None:
        pipeline.category = request.category
    if request.icon is not None:
        pipeline.icon = request.icon
    if request.color is not None:
        pipeline.color = request.color
    if request.tags is not None:
        pipeline.tags = request.tags

    # Save updated pipeline
    pipeline_registry.save(pipeline)

    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        description=pipeline.description,
        nodes=[n.model_dump() for n in pipeline.nodes],
        edges=[e.model_dump() for e in pipeline.edges],
        category=pipeline.category,
        icon=pipeline.icon,
        color=pipeline.color,
        tags=pipeline.tags,
        created_at=pipeline.created_at.isoformat(),
        updated_at=pipeline.updated_at.isoformat(),
        version=pipeline.version,
    )


@router.delete("/{pipeline_id}")
async def delete_pipeline(pipeline_id: str):
    """
    🗑️ Delete Pipeline

    Remove a pipeline from the registry.
    """
    if pipeline_registry.delete(pipeline_id):
        return {"message": f"Pipeline '{pipeline_id}' deleted", "pipeline_id": pipeline_id}
    else:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")


@router.post("/{pipeline_id}/execute", response_model=ExecutionResponse)
async def execute_pipeline_by_id(
    pipeline_id: str,
    request: ExecutePipelineRequest,
    background_tasks: BackgroundTasks,
):
    """
    🚀 Execute Pipeline

    Run a saved pipeline. Optionally provide initial inputs.

    The pipeline executes skills in topological order:
    - Skills with no dependencies run first
    - Outputs from one skill become inputs to connected skills
    - Final output is from the last skill in the chain
    """
    pipeline = pipeline_registry.get(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")

    if request.async_mode:
        # Run in background (for long pipelines)
        # TODO: Implement background execution with status polling
        pass

    # Execute pipeline
    result = await execute_pipeline_definition(pipeline, request.initial_inputs)

    return ExecutionResponse(
        run_id=result.run_id,
        pipeline_id=result.pipeline_id,
        status=result.status.value,
        progress_percent=result.progress_percent,
        current_node=result.current_node,
        node_results=[nr.model_dump() for nr in result.node_results],
        final_output=result.final_output,
        error=result.error,
        error_node=result.error_node,
        started_at=result.started_at.isoformat(),
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
        total_duration_ms=result.total_duration_ms,
    )


@router.post("/execute-inline", response_model=ExecutionResponse)
async def execute_pipeline_inline(request: CreatePipelineRequest):
    """
    ⚡ Execute Pipeline Inline

    Execute a pipeline definition without saving it.
    Useful for testing or one-off executions.
    """
    # Convert to pipeline definition
    pipeline = PipelineDefinition(
        name=request.name,
        description=request.description,
        nodes=[PipelineNode(**n.model_dump()) for n in request.nodes],
        edges=[PipelineEdge(**e.model_dump()) for e in request.edges],
        category=request.category,
        icon=request.icon,
        color=request.color,
        tags=request.tags,
    )

    # Execute
    result = await execute_pipeline_definition(pipeline)

    return ExecutionResponse(
        run_id=result.run_id,
        pipeline_id=result.pipeline_id,
        status=result.status.value,
        progress_percent=result.progress_percent,
        current_node=result.current_node,
        node_results=[nr.model_dump() for nr in result.node_results],
        final_output=result.final_output,
        error=result.error,
        error_node=result.error_node,
        started_at=result.started_at.isoformat(),
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
        total_duration_ms=result.total_duration_ms,
    )


@router.get("/runs/{run_id}")
async def get_run_status(run_id: str):
    """
    📊 Get Run Status

    Check the status of a pipeline execution.
    """
    executor = get_executor()
    result = executor.get_run_status(run_id)

    if not result:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    return ExecutionResponse(
        run_id=result.run_id,
        pipeline_id=result.pipeline_id,
        status=result.status.value,
        progress_percent=result.progress_percent,
        current_node=result.current_node,
        node_results=[nr.model_dump() for nr in result.node_results],
        final_output=result.final_output,
        error=result.error,
        error_node=result.error_node,
        started_at=result.started_at.isoformat(),
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
        total_duration_ms=result.total_duration_ms,
    )


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    """
    ⛔ Cancel Pipeline Run

    Cancel an active pipeline execution.
    """
    executor = get_executor()
    if executor.cancel_run(run_id):
        return {"message": f"Run '{run_id}' cancelled", "run_id": run_id}
    else:
        raise HTTPException(status_code=404, detail=f"Active run '{run_id}' not found")
