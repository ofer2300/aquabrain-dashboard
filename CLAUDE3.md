# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AquaBrain is an AI-powered MEP (Mechanical, Electrical, Plumbing) engineering platform for fire sprinkler system design. It automates hydraulic calculations, clash detection, and LOD 500 model generation with NFPA 13 compliance validation.

**Hybrid Local-First Architecture:** Gemini (Cloud Brain) + Claude Code CLI (Hands) + Ollama (Local Brain)

## Development Commands

```bash
# Full stack launch (recommended)
./start_aquabrain.sh

# Backend only (port 8000)
cd backend && source venv/bin/activate && python main.py

# Frontend only (port 3000)
cd frontend && npm run dev

# Local Bridge Server (port 8085) - Required for Claude Agent
# Note: Airflow uses 8080, so bridge moved to 8085
cd local-server && npm install && node bridge.js

# Build frontend
cd frontend && npm run build

# Frontend linting
cd frontend && npm run lint

# Run all backend tests
cd backend && source venv/bin/activate && python -m pytest tests/ -v

# Run single test file
python -m pytest tests/unit/test_hydraulics.py -v

# Test Gemini AI connection
cd backend && python scripts/test_gemini_rest.py
```

**Ports:** Backend: 8000 | Frontend: 3000 | Bridge: 8085 | Redis: 6379 | Flower: 5555

## Environment Setup

Create `backend/.env` with required secrets:
```
GEMINI_API_KEY=<your-gemini-api-key>
OLLAMA_BASE_URL=http://localhost:11434
# RPA credentials (optional)
MEI_AVIVIM_ID=<id>
GMAIL_USER=<email>
GMAIL_USER_PASSWORD=<password>
```

## Architecture

### Hybrid Local-First Architecture (Triangular AI System)

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INPUT                               │
│                         │                                    │
│         ┌───────────────┼───────────────┐                   │
│         ▼               ▼               ▼                   │
│   ┌───────────┐   ┌───────────┐   ┌──────────────┐         │
│   │ 🏠 OLLAMA │   │ ☁️ GEMINI │   │ 🤖 CLAUDE    │         │
│   │ LOCAL     │   │ CLOUD     │   │ EXECUTION    │         │
│   │ BRAIN     │   │ BRAIN     │   │ HANDS        │         │
│   │           │   │           │   │              │         │
│   │ • Code    │   │ • Strategy│   │ • Execute    │         │
│   │ • Tactics │   │ • Planning│   │ • Write      │         │
│   │ • Research│   │ • Reason  │   │ • Run        │         │
│   │ • Private │   │ • General │   │ • Revit      │         │
│   └───────────┘   └───────────┘   └──────────────┘         │
│   RTX 4060 Ti      Cloud API       Bridge (8085)            │
│   16GB VRAM        (Fallback)                               │
│   Zero Latency                                              │
└─────────────────────────────────────────────────────────────┘
```

**The Three Pillars:**

1. **LOCAL BRAIN (Ollama)**: `qwen2.5-coder:7b` running on RTX 4060 Ti (16GB VRAM) via port 11434
   - Handles tactical code generation & privacy-focused research
   - Temperature: 0.2 (engineering precision)
   - Context window: 4096 tokens
   - Zero latency, zero cost, full privacy

2. **CLOUD BRAIN (Gemini)**: Strategic reasoning and complex analysis
   - Fallback when local fails
   - Wide world knowledge
   - Complex multi-step reasoning

3. **EXECUTION HANDS (Claude Code CLI)**: Real-world execution
   - Filesystem operations
   - CLI commands
   - Revit automation via Bridge

**Smart Router Logic:**
```
IF prompt contains ["python", "code", "script", "private", "refactor"] → USE OLLAMA (Local)
IF prompt contains ["why", "explain", "strategy", "compare"] → USE GEMINI (Cloud)
IF Local fails → Auto-fallback to Cloud
```

### Three-Layer System

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js 16 + React 19)                           │
│  └─ UnifiedCommandBar: Gemini + Claude Agent toggle         │
│  └─ /autopilot → ProjectCapsule (async polling)             │
│  └─ /projects/[id] → Skills Grid + Auto-Pilot tabs          │
├─────────────────────────────────────────────────────────────┤
│  UNIVERSAL ORCHESTRATOR + LOCAL BRIDGE                       │
│  └─ POST /api/orchestrator/trigger ← "One Endpoint"         │
│  └─ WebSocket Bridge (8085) → Claude Code CLI execution     │
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

**AI Engine** (`backend/services/ai_engine.py`):
- Multi-model support: Ollama (local) + Gemini (cloud) + Claude (cloud)
- Smart Router: Auto-routes queries based on content
  - Code/Python/Private → Ollama (local, zero latency)
  - Complex reasoning → Gemini (cloud fallback)
- Providers:
  - `ollama`: Local inference on RTX 4060 Ti (16GB VRAM)
    - Default model: `qwen2.5-coder:7b`
    - URL: `http://localhost:11434`
  - `gemini`: Cloud API (fallback)
    - Models: `pro` (25/day), `flash` (500/day), `fast` (1500/day)
  - `claude`: Cloud API (optional)
    - Models: `haiku`, `sonnet`, `opus`
- Unified interface: `ask_ai(prompt, provider="ollama"|"gemini"|"claude")`
- `ask_aquabrain(prompt)` with engineering system prompt (NFPA 13 + ת"י 1596)
- `analyze_ifc_element(data)` for IFC/BIM analysis

**RPA / Web Agents** (`backend/skills/custom/`):
- Playwright-based browser automation
- Email OTP interception via IMAP (`services/email_reader.py`)
- Base web agent class (`services/web_agent.py`)
- Example: `mei_avivim_bot.py` for utility submissions

**Local Bridge Server** (`local-server/bridge.js`):
- WebSocket server on port 8085 for real-time command execution
- Enables Claude Code CLI integration from the browser
- Supports: PowerShell, Bash (WSL), Python, pyRevit, file operations
- Message types: `claude_agent`, `powershell`, `bash`, `python`, `pyrevit`
- Real-time streaming output back to frontend via WebSocket
- Platform detection: Windows native or WSL2

## Core API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/orchestrator/trigger` | Execute any skill by ID |
| `GET /api/orchestrator/skills` | List all registered skills |
| `POST /api/engineering/start-process` | Launch full pipeline (async) |
| `GET /api/engineering/status/{run_id}` | Poll job progress |
| `POST /api/factory/generate` | Create new skill from description |
| `POST /api/calc/hydraulic` | Hazen-Williams calculation |
| `POST /api/chat/interact` | Command Bar AI router |
| `POST /api/research` | **LOCAL BRAIN** - Research via Ollama (RTX 4060 Ti) |

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
4. Define `metadata` and `input_schema` properties

```python
from skills.base import (
    AquaSkill, ExecutionResult, ExecutionStatus,
    SkillMetadata, SkillCategory, InputSchema, InputField, FieldType,
    register_skill
)

@register_skill
class MySkill(AquaSkill):
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="My Custom Skill",
            description="Does something useful",
            category=SkillCategory.CUSTOM,
            icon="Cog"
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(name="value", label="Input Value", type=FieldType.TEXT)
        ])

    def execute(self, inputs: dict) -> ExecutionResult:
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            skill_id=self.metadata.id,
            message="Done!",
            output={"result": inputs.get("value")}
        )
```

**Skill Categories**: `REVIT`, `AUTOCAD`, `HYDRAULICS`, `DOCUMENTATION`, `FILE_PROCESSING`, `DATA_ANALYSIS`, `REPORTING`, `INTEGRATION`, `RPA`, `RESEARCH`, `CUSTOM`

- `RESEARCH`: Autonomous web scraping and technical summarization using Local LLM (Ollama)

## UI Guidelines

- **Glassmorphism**: `backdrop-blur-xl`, `bg-slate-900/80`, `border-white/10`
- **Status Colors**: `status-success` (green), `status-warning` (yellow), `status-error` (red), `status-ai` (purple)
- **RTL Support**: Hebrew UI with `dir="rtl"` on containers

## Database

SQLite (`aquabrain.db`) with tables:
- `project_runs`: Pipeline execution history with JSON result storage
- `skill_executions`: Audit trail for skill invocations

## Frontend Context System

**LanguageContext** (`frontend/src/contexts/LanguageContext.tsx`):
- Hebrew/English switching via `useLanguage()` hook
- `t(key)` function for translations
- RTL support with `dir="rtl"` on Hebrew containers

**ProjectContext** (`frontend/src/hooks/useProjectContext.tsx`):
- Project state persistence in LocalStorage
- `useProject()` hook for current project data
- Preserves state across browser sessions

## Key Frontend Components

- `UnifiedCommandBar.tsx`: Dual-AI interface (Gemini + Claude Agent toggle)
  - Gemini Flash/Pro+ for chat and reasoning
  - Claude Agent mode for code execution via CLI
  - Live Operations Log with status indicators (pending → processing → success/error)
- `ProjectCapsule.tsx`: Main Auto-Pilot dashboard with Traffic Light status
- `CommandBar.tsx`: AI chat interface, supports `/command` syntax
- `SkillsGrid.tsx`: Grid of available skills with dynamic forms
- `DynamicSkillForm.tsx`: Auto-generates forms from skill input schemas

## Frontend Hooks

- `useLocalBridge.ts`: WebSocket connection to local bridge server
  - `runCommand(cmd, type)`: Execute command (powershell/bash/claude_agent)
  - `runClaudeAgent(prompt)`: Send prompt to Claude Code CLI
  - `logs`: Real-time output stream
  - `isConnected`: Bridge connection status
