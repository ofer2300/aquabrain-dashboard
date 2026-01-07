# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Backend Overview

FastAPI backend for AquaBrain - fire sprinkler MEP engineering platform. Provides the Universal Orchestrator, skill execution system, hydraulic calculations, and Revit/AutoCAD integration bridges.

## Quick Commands

```bash
# Start backend server (port 8000)
python main.py

# Run tests
python -m pytest tests/ -v                           # All tests
python -m pytest tests/unit/test_hydraulics.py -v    # Single file
python -m pytest tests/unit/ -v                      # Unit tests only
python -m pytest tests/integration/ -v               # Integration tests

# API docs after starting server
http://localhost:8000/docs   # Swagger UI
http://localhost:8000/redoc  # ReDoc
```

## Architecture

### Universal Orchestrator

Single endpoint for all skill execution: `POST /api/orchestrator/trigger`

```python
# Request
{"skill_id": "hydraulic-calc", "payload": {"flow_gpm": 100, "pipe_diameter_in": 2}}

# Response
{"task_id": "uuid", "status": "COMPLETED", "result": {...}}
```

Flow: Request → Skill Registry lookup → Input validation → TaskRecord created → SkillRunner executes → Audit trail saved

### Skill System

All skills inherit from `AquaSkill` in `skills/base.py`:

```python
@register_skill
class MySkill(AquaSkill):
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(name="...", category=SkillCategory.CUSTOM)

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[InputField(name="x", type=FieldType.TEXT)])

    def execute(self, inputs: dict) -> ExecutionResult:
        return ExecutionResult(status=ExecutionStatus.SUCCESS, output={...})
```

**Skill locations:**
- `skills/builtin/` - Official skills (hydraulic_calc, revit_extract)
- `skills/native/` - Native integrations (revit_autopilot)
- `skills/custom/` - AI-generated skills (hot-reloadable)

### Module Responsibilities

| Module | Purpose |
|--------|---------|
| `modules/hydraulics.py` | Hazen-Williams calculations, LOD 500 pipe data |
| `modules/standards.py` | NFPA 13 compliance validation |
| `modules/revit_bridge.py` | WSL2 → Revit API bridge |
| `services/ai_engine.py` | Multi-model AI router (Ollama/Gemini/Claude) |
| `services/voxelizer.py` | 3D space voxelization for routing |
| `services/pathfinder.py` | A* pipe routing algorithm |
| `engines/voxel_engine.py` | NumPy/SciPy high-performance voxel grid |

### AI Engine Routing

```python
from services.ai_engine import ask_ai, ask_aquabrain

# Direct provider
response = ask_ai("Generate Python code", provider="ollama")  # Local RTX 4060 Ti
response = ask_ai("Explain strategy", provider="gemini")      # Cloud fallback

# Smart router (auto-selects based on content)
response = ask_aquabrain("Calculate sprinkler coverage")  # Engineering system prompt
```

Smart router logic:
- Code/Python/Private keywords → Ollama (local, zero latency)
- Complex reasoning/strategy → Gemini (cloud)
- Ollama failure → Auto-fallback to Gemini

### Database Models

SQLite (`aquabrain.db`) with SQLAlchemy:

```python
from models import ProjectRun, SkillExecution, EngineerProfile

# Pipeline execution tracking
ProjectRun(status="PROCESSING", results_json={...})

# Skill audit trail
SkillExecution(skill_id="hydraulic-calc", status="SUCCESS", result_json={...})
```

## Key API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/orchestrator/trigger` | POST | Execute any skill |
| `/api/orchestrator/skills` | GET | List all skills |
| `/api/orchestrator/tasks/{id}` | GET | Poll task status |
| `/api/calc/hydraulic` | POST | Hazen-Williams calculation |
| `/api/research` | POST | Local LLM research (Ollama) |
| `/api/engineering/start-process` | POST | Launch async pipeline |
| `/api/engineering/status/{run_id}` | GET | Poll pipeline progress |

## Engineering Formulas

**Hazen-Williams** (`modules/hydraulics.py`):
```
P = 4.52 × Q^1.85 / (C^1.85 × d^4.87) × L
```
- Uses SCH40/SCH10 actual internal diameters (ANSI/ASME B36.10M)
- Velocity validation: max 32 fps (recommended < 20 fps per NFPA 13)

**Traffic Light System:**
- GREEN: Compliant, velocity < 20 fps
- YELLOW: Warnings (20-32 fps)
- RED: Critical failures

## Testing

Fixtures in `tests/conftest.py`:
- `test_client`: FastAPI TestClient
- `hydraulic_input`: Sample pipe calculation input
- `engineering_request`: Full pipeline request fixture

## Async Execution

Celery with Redis (filesystem fallback if Redis unavailable):

```python
# Trigger async task
from tasks import run_engineering_pipeline
result = run_engineering_pipeline.delay(project_data)

# Check status via API
GET /api/engineering/status/{task_id}
```

## Voxel Engine

High-performance 3D grid using NumPy/SciPy (`engines/voxel_engine.py`):

```python
from engines.voxel_engine import VoxelEngine

engine = VoxelEngine(resolution=0.2, padding=1.0)
grid = engine.create_grid(bounds_min=[0,0,0], bounds_max=[10,10,5])
engine.burn_obstacle(grid, obs_min=[2,2,0], obs_max=[3,3,5])
engine.apply_safety_dilation(grid, iterations=1)  # Safety buffer
```

Coordinate sync: `grid.world_to_grid(x,y,z)` ↔ `grid.grid_to_world(i,j,k)`

## Adding New Endpoints

1. Create router in `api/` if new domain
2. Register in `main.py`: `app.include_router(my_router, prefix="/api/my")`
3. Use Pydantic models for request/response validation
4. Add to appropriate test file in `tests/`

## Environment Variables

Required in `.env`:
```
GEMINI_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434
```

## Ports

- Backend: 8000
- Ollama: 11434
- Redis: 6379
- Bridge: 8085
- Flower (Celery monitor): 5555
