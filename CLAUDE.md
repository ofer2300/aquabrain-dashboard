# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AquaBrain is an AI-powered MEP (Mechanical, Electrical, Plumbing) engineering platform for fire sprinkler system design. It automates hydraulic calculations, clash detection, and LOD 500 model generation with NFPA 13 compliance validation.

## Development Commands

```bash
# Full stack launch (recommended)
./start_aquabrain.sh

# Backend only
cd backend && source venv/bin/activate && python main.py

# Frontend only
cd frontend && npm run dev

# Run tests
cd backend && source venv/bin/activate && python -m pytest tests/ -v

# Run single test file
python -m pytest tests/unit/test_hydraulics.py -v
```

**Ports:** Backend: 8000 | Frontend: 3000 | Redis: 6379 | Flower: 5555

## Architecture

### Three-Layer System

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js 16 + React 19)                           │
│  └─ /autopilot → ProjectCapsule (async polling)             │
│  └─ /projects/[id] → Skills Grid + Auto-Pilot tabs          │
├─────────────────────────────────────────────────────────────┤
│  UNIVERSAL ORCHESTRATOR                                      │
│  └─ POST /api/orchestrator/trigger ← "One Endpoint"         │
│  └─ Skill Registry (auto-discovery via @register_skill)     │
│  └─ Celery/Redis async queue (thread fallback)              │
├─────────────────────────────────────────────────────────────┤
│  REVIT BRIDGE (WSL → PowerShell → COM → Revit)              │
│  └─ Mock Mode: Hyper-realistic simulation for dev/demos     │
│  └─ Multi-version: 2024, 2025, 2026, auto-detect            │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Patterns

**Skill System** (`backend/skills/`):
- All skills inherit from `AquaSkill` base class
- `@register_skill` decorator auto-registers to global `SKILL_REGISTRY`
- Input schemas generate dynamic frontend forms
- Three skill types: `builtin/`, `native/`, `custom/` (AI-generated)

**Async Pipeline** (`backend/worker.py`):
- Celery tasks with Redis broker (filesystem fallback)
- `ProjectRun` table tracks job status (QUEUED → PROCESSING → COMPLETED)
- Frontend polls `/api/engineering/status/{run_id}` every 1 second

**Revit Bridge** (`backend/scripts/bridge_revit.py`):
- PowerShell subprocess from WSL2 to Windows
- `mock_mode=True` returns simulated LOD 500 data
- Semantic extraction: fire ratings, materials, assembly codes

## Core API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/orchestrator/trigger` | Execute any skill by ID |
| `GET /api/orchestrator/skills` | List all registered skills |
| `POST /api/engineering/start-process` | Launch full pipeline (async) |
| `GET /api/engineering/status/{run_id}` | Poll job progress |
| `POST /api/factory/generate` | Create new skill from description |
| `POST /api/calc/hydraulic` | Hazen-Williams calculation |

## Engineering Domain

**Hazen-Williams Formula** (`backend/modules/hydraulics.py`):
```
P = 4.52 × Q^1.85 / (C^1.85 × d^4.87) × L
```
- P: Pressure loss (PSI)
- Q: Flow rate (GPM)
- C: Pipe roughness coefficient
- d: Internal diameter (inches)
- L: Pipe length (feet)

**NFPA 13 Hazard Classes** (`backend/modules/standards.py`):
- `light`: 0.10 GPM/ft², 225 ft² coverage
- `ordinary_1`: 0.15 GPM/ft², 130 ft² coverage
- `ordinary_2`: 0.20 GPM/ft², 130 ft² coverage
- `extra_1`: 0.30 GPM/ft², 90 ft² coverage
- `extra_2`: 0.40 GPM/ft², 90 ft² coverage

**Traffic Light System**:
- GREEN: NFPA compliant, velocity < 20 fps, no clashes
- YELLOW: Warnings (velocity 20-32 fps, minor issues)
- RED: Critical failures, non-compliance

## Creating New Skills

1. Create file in `backend/skills/builtin/` or `backend/skills/native/`
2. Inherit from `AquaSkill` and implement `execute()`
3. Use `@register_skill` decorator
4. Define `input_schema` for dynamic form generation

```python
from skills.base import AquaSkill, SkillResult, register_skill

@register_skill
class MySkill(AquaSkill):
    id = "my_skill"
    name = "My Custom Skill"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {...}}

    async def execute(self, inputs: dict, context: dict) -> SkillResult:
        # Implementation
        return SkillResult(success=True, data={...})
```

## UI Guidelines

- **Glassmorphism**: `backdrop-blur-xl`, `bg-slate-900/80`, `border-white/10`
- **Status Colors**: `status-success` (green), `status-warning` (yellow), `status-error` (red), `status-ai` (purple)
- **RTL Support**: Hebrew UI with `dir="rtl"` on containers

## Database

SQLite (`aquabrain.db`) with tables:
- `project_runs`: Pipeline execution history with JSON result storage
- `skill_executions`: Audit trail for skill invocations
