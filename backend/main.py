#!/usr/bin/env python3
"""
AquaBrain Backend API
FastAPI server for the AquaBrain Dashboard
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
import uvicorn
import asyncio
import random

from fastapi import UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import base64

from clash_service import resolve_clash, ClashData
from modules.hydraulics import HydraulicCalculator, PipeData
from modules.standards import NFPA13Validator, HazardClass
from modules.ingestion import ingestion_manager, ProjectStatus
from services.orchestrator import run_engineering_process

app = FastAPI(
    title="AquaBrain API",
    description="Backend API for AquaBrain MEP Clash Detection System",
    version="1.0.0"
)

# CORS middleware for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Response Models ===
class SystemStatus(BaseModel):
    system: str
    status: str
    ai_engine: str
    timestamp: str
    uptime_seconds: Optional[int] = None


class ClashResolution(BaseModel):
    clash_id: str
    resolution: str
    confidence: float
    suggested_action: str


class ChatMessage(BaseModel):
    message: str
    context: Optional[str] = None


class ChatResponse(BaseModel):
    message: str
    analysis: Optional[str] = None
    confidence: Optional[float] = None
    timestamp: str


# === Hydraulic Calculation Models ===
class HydraulicInput(BaseModel):
    """Input for hydraulic calculation - simplified format."""
    flow: float = Field(..., gt=0, description="Flow rate in GPM")
    length: float = Field(..., gt=0, description="Pipe length in feet")
    diameter: float = Field(..., gt=0, description="Nominal pipe diameter in inches")
    hazard: str = Field(default="light", description="NFPA 13 hazard classification")
    c_factor: float = Field(default=120, gt=0, description="Hazen-Williams C-factor")
    schedule: str = Field(default="40", description="Pipe schedule (40 or 10)")


class HydraulicOutput(BaseModel):
    """Output from hydraulic calculation - simplified format."""
    pressure_loss: float
    velocity: float
    compliant: bool
    notes: List[str]
    # Extended data
    actual_diameter: float
    friction_per_ft: float
    nfpa_requirements: dict
    timestamp: str


# === AI Response Templates ===
AI_RESPONSES = [
    {
        "pattern": ["התנגשות", "clash", "קונפליקט"],
        "responses": [
            "קיבלתי. אני מנתח את ההתנגשות בקומה 3... מזהה חפיפה בין צינור HVAC לקו מים ראשי.",
            "מריץ סימולציה על ההתנגשות... הפתרון המומלץ: הסטת הצינור ב-15 ס\"מ מערבה.",
            "ניתחתי את הבעיה. יש 3 אפשרויות פתרון. הטובה ביותר: שינוי גובה ב-20 ס\"מ.",
        ]
    },
    {
        "pattern": ["ספרינקלר", "sprinkler", "כיבוי אש"],
        "responses": [
            "בודק תאימות למערכת הספרינקלרים... הכל תקין לפי NFPA 13.",
            "מחשב מרווחים נדרשים לספרינקלרים... נדרש מרווח מינימלי של 45 ס\"מ.",
            "סורק את תכנון הספרינקלרים... מזהה 2 ראשים שדורשים התאמה.",
        ]
    },
    {
        "pattern": ["תקן", "nfpa", "קוד"],
        "responses": [
            "בודק עמידה בתקן... העיצוב עומד בדרישות NFPA 13 ו-NFPA 25.",
            "ניתוח תקינה הושלם. אין חריגות מהתקן.",
            "מצאתי סטייה קטנה מתקן NFPA 13 סעיף 8.5.2. ממליץ על תיקון.",
        ]
    },
    {
        "pattern": [],  # Default
        "responses": [
            "קיבלתי את ההודעה. אני מעבד את המידע ומכין ניתוח מפורט...",
            "מריץ אלגוריתם AI על הנתונים... אחזור עם תוצאות בקרוב.",
            "הבנתי. בודק את מסד הנתונים ומחפש פתרונות רלוונטיים...",
        ]
    }
]


# === Startup time tracking ===
startup_time = datetime.now()


# === API Endpoints ===

@app.get("/api/status", response_model=SystemStatus)
async def get_status():
    """
    Get system status.
    Returns the current state of AquaBrain system.
    """
    uptime = (datetime.now() - startup_time).seconds
    return SystemStatus(
        system="AquaBrain",
        status="LIVE",
        ai_engine="READY",
        timestamp=datetime.now().isoformat(),
        uptime_seconds=uptime
    )


@app.post("/api/clash/resolve", response_model=ClashResolution)
async def resolve_clash_endpoint(clash_data: ClashData):
    """
    Resolve a MEP clash.
    Analyzes clash data and returns engineering solution.
    """
    resolution = resolve_clash(clash_data)
    return resolution


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    """
    AI Chat endpoint.
    Receives a message, simulates AI thinking, and returns an engineering response.
    """
    # Simulate AI thinking time (1-3 seconds)
    thinking_time = random.uniform(1, 3)
    await asyncio.sleep(thinking_time)

    # Find matching response based on keywords
    message_lower = chat_message.message.lower()
    response_text = None

    for category in AI_RESPONSES:
        if not category["pattern"]:  # Default category
            continue
        for keyword in category["pattern"]:
            if keyword in message_lower:
                response_text = random.choice(category["responses"])
                break
        if response_text:
            break

    # Use default if no match found
    if not response_text:
        default_category = [c for c in AI_RESPONSES if not c["pattern"]][0]
        response_text = random.choice(default_category["responses"])

    return ChatResponse(
        message=response_text,
        analysis=f"Processed in {thinking_time:.1f}s",
        confidence=round(random.uniform(0.75, 0.98), 2),
        timestamp=datetime.now().isoformat()
    )


# === Engineering Calculation Endpoints ===

# Initialize engineering modules
hydraulic_calc = HydraulicCalculator()
nfpa_validator = NFPA13Validator()


@app.post("/api/calc/hydraulic", response_model=HydraulicOutput)
async def calculate_hydraulic(data: HydraulicInput):
    """
    Calculate hydraulic parameters for a pipe segment.

    Input format:
        { flow: 100, length: 50, diameter: 2, hazard: 'light' }

    Output format:
        { pressure_loss: 5.2, velocity: 10.5, compliant: true, notes: [...] }

    Uses Hazen-Williams formula with SCH 40/10 pipe data for LOD 500 accuracy.
    """
    # Create pipe data with nominal-to-actual conversion
    pipe = PipeData(
        flow_gpm=data.flow,
        diameter_inch=data.diameter,
        length_ft=data.length,
        c_factor=data.c_factor,
        use_nominal=True,
        schedule=data.schedule,
    )

    # Run hydraulic calculation
    result = hydraulic_calc.calculate(pipe)

    # Get NFPA requirements for hazard class
    try:
        hazard = HazardClass(data.hazard)
    except ValueError:
        hazard = HazardClass.LIGHT

    nfpa_req = nfpa_validator.get_requirements_dict(hazard)

    # Compliance check based on velocity
    compliant = result.velocity_ok

    # Combine warnings and notes
    all_notes = result.notes + result.warnings

    return HydraulicOutput(
        pressure_loss=round(result.pressure_loss_psi, 2),
        velocity=result.velocity_fps,
        compliant=compliant,
        notes=all_notes,
        actual_diameter=result.actual_diameter,
        friction_per_ft=result.friction_loss_per_ft,
        nfpa_requirements=nfpa_req,
        timestamp=datetime.now().isoformat(),
    )


# === Project & Ingestion Endpoints ===

class ProjectCreateRequest(BaseModel):
    name: str
    standard: str = "NFPA 13"
    hazard_class: str = "light"
    water_pressure_bar: float = 4.0


class FileUploadRequest(BaseModel):
    filename: str
    content_base64: str  # Base64 encoded file content


@app.post("/api/projects")
async def create_project(request: ProjectCreateRequest):
    """
    Create a new project.
    The Engineer's first command - initializing the cockpit.
    """
    project = ingestion_manager.create_project(
        name=request.name,
        settings={
            "standard": request.standard,
            "hazard_class": request.hazard_class,
            "water_pressure_bar": request.water_pressure_bar,
        }
    )
    return {
        "success": True,
        "project_id": project.id,
        "name": project.name,
        "status": project.status.value,
        "message": f"Project '{project.name}' created. Ready for file upload."
    }


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get project status and details."""
    status = ingestion_manager.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return status


@app.post("/api/projects/{project_id}/upload")
async def upload_file(project_id: str, request: FileUploadRequest):
    """
    Upload architectural files (DWG, PDF, RVT).
    The pilot loads the mission parameters.
    """
    try:
        content = base64.b64decode(request.content_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 content")

    result = ingestion_manager.handle_file_upload(
        project_id=project_id,
        filename=request.filename,
        content=content
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.post("/api/projects/{project_id}/start")
async def start_pipeline(project_id: str):
    """
    🚀 THE GO BUTTON - IGNITE ENGINE
    Triggers the entire processing pipeline.
    This is the moment the engineer takes control.
    """
    result = ingestion_manager.trigger_processing_pipeline(project_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.get("/api/tasks/pending")
async def get_pending_tasks():
    """
    Get pending tasks for workers (Revit Agent, AI Worker).
    This endpoint is polled by external processing agents.
    """
    tasks = ingestion_manager.get_pending_tasks()
    return {"tasks": tasks, "count": len(tasks)}


@app.post("/api/tasks/{task_id}/update")
async def update_task(task_id: str, status: str, stage: Optional[str] = None):
    """Update task status from worker."""
    ingestion_manager.update_task_status(task_id, status, stage)
    return {"success": True, "task_id": task_id, "status": status}


@app.get("/api/health")
async def health_check():
    """
    Enhanced health check endpoint.
    Checks system resources and component availability.
    """
    import psutil
    from pathlib import Path

    # Disk check for logs
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    disk = psutil.disk_usage(str(log_dir))
    disk_free_gb = disk.free / (1024 ** 3)
    disk_ok = disk_free_gb > 1.0  # Require at least 1 GB

    # Memory check
    memory = psutil.virtual_memory()
    memory_ok = memory.percent < 90

    # Bridge check (Mock mode = always OK)
    bridge_status = "mock_mode"
    bridge_ok = True

    # Overall health
    all_ok = disk_ok and memory_ok and bridge_ok

    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": {
            "disk": {
                "ok": disk_ok,
                "free_gb": round(disk_free_gb, 2),
                "message": "OK" if disk_ok else "Low disk space"
            },
            "memory": {
                "ok": memory_ok,
                "used_percent": memory.percent,
                "message": "OK" if memory_ok else "High memory usage"
            },
            "bridge": {
                "ok": bridge_ok,
                "mode": bridge_status,
                "message": "Running in mock mode"
            }
        },
        "uptime_seconds": (datetime.now() - startup_time).seconds
    }


# === Engineering Auto-Pilot Endpoint ===

class EngineeringProcessRequest(BaseModel):
    """Request to start the engineering process."""
    project_id: str
    notes: str = ""
    hazard_class: str = "ordinary_1"
    async_mode: bool = True  # Use async (Celery) by default


class AsyncJobResponse(BaseModel):
    """Response for async job submission."""
    run_id: str
    status: str
    message: str


@app.post("/api/engineering/start-process")
async def start_engineering_process_endpoint(request: EngineeringProcessRequest):
    """
    🚀 THE CAPSULE - One Click Engineering (V2.0 Async)

    This is the "Tesla of Engineering" endpoint.
    One click triggers the complete automation workflow:

    1. Extract geometry from Revit (via WSL Bridge)
    2. Voxelize the space for pathfinding
    3. Run A* algorithm for optimal pipe routing
    4. Calculate hydraulics (Hazen-Williams LOD 500)
    5. Generate LOD 500 model in Revit
    6. Return Traffic Light status (GREEN/YELLOW/RED)

    V2.0: Now supports async mode (default) for enterprise scalability.

    Async Mode (async_mode=true):
        - Returns immediately with run_id
        - Poll /api/engineering/status/{run_id} for progress
        - Scales to thousands of concurrent requests

    Sync Mode (async_mode=false):
        - Waits for completion (legacy behavior)
        - Simpler for single-user scenarios
    """
    if request.async_mode:
        # ASYNC MODE: Queue task and return immediately
        try:
            from worker import create_run, run_engineering_job

            # Create run record in DB
            run_id = create_run(
                project_id=request.project_id,
                hazard_class=request.hazard_class,
                notes=request.notes,
            )

            # Queue Celery task (will run if worker is available)
            # For now, run synchronously in background thread as fallback
            import threading

            def run_task():
                try:
                    run_engineering_job(
                        run_id=run_id,
                        project_id=request.project_id,
                        hazard_class=request.hazard_class,
                        notes=request.notes,
                    )
                except Exception as e:
                    print(f"[ERROR] Background task failed: {e}")

            thread = threading.Thread(target=run_task, daemon=True)
            thread.start()

            return {
                "run_id": run_id,
                "status": "QUEUED",
                "message": "Engineering job queued. Poll /api/engineering/status/{run_id} for progress.",
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to queue job: {str(e)}")

    else:
        # SYNC MODE: Wait for completion (legacy behavior)
        result = await run_engineering_process(
            project_id=request.project_id,
            hazard_class=request.hazard_class,
            notes=request.notes
        )
        return result


@app.get("/api/engineering/status/{run_id}")
async def get_engineering_status(run_id: str):
    """
    📊 Get Engineering Job Status

    Poll this endpoint to track progress of an async engineering job.

    Returns:
        - status: QUEUED | PROCESSING | COMPLETED | FAILED
        - current_stage: Current pipeline stage
        - progress_percent: 0-100
        - traffic_light: Full results when completed
        - All summary data when completed
    """
    try:
        from worker import get_run_status

        run_data = get_run_status(run_id)

        if not run_data:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        return run_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@app.get("/api/engineering/history/{project_id}")
async def get_project_history(project_id: str, limit: int = 10):
    """
    📜 Get Project Run History

    Returns the history of all engineering runs for a project.
    Useful for comparing results over time.
    """
    try:
        from worker import get_project_history

        history = get_project_history(project_id, limit=limit)

        return {
            "project_id": project_id,
            "total_runs": len(history),
            "runs": history,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "message": "Welcome to AquaBrain API",
        "docs": "/docs",
        "status_endpoint": "/api/status"
    }


if __name__ == "__main__":
    print("\n🧠 Starting AquaBrain Backend...")
    print("📡 API Docs: http://localhost:8000/docs")
    print("🔗 Status: http://localhost:8000/api/status\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
