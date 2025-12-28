"""
Document Automation API
=======================
Endpoints for automated document generation with dynamic stamps.

POST /api/automation/plumbing-affidavit - Generate plumbing affidavit
POST /api/automation/generate - Generic document generation
GET /api/automation/templates - List available templates
"""

import os
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from fastapi.responses import FileResponse

from api.engineer_profile import get_engineer_profile_sync
from services.document_automation.generator import DocumentGenerator
from services.document_automation.templates import TemplateManager, TEMPLATES

router = APIRouter(prefix="/api/automation", tags=["Document Automation"])

# Initialize services
doc_generator = DocumentGenerator()
template_manager = TemplateManager()


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class PlumbingAffidavitRequest(BaseModel):
    """Request for plumbing affidavit generation."""
    project_id: str
    template_type: str = "after_execution"  # after_execution | completion
    # Project details (can be fetched from DB or provided)
    project_address: Optional[str] = None
    gush_chalka: Optional[str] = None
    permit_number: Optional[str] = None
    work_description: Optional[str] = None
    inspection_date: Optional[str] = None


class GenericDocumentRequest(BaseModel):
    """Request for generic document generation."""
    template_id: str
    project_id: Optional[str] = None
    data: dict = {}
    output_format: str = "pdf"
    add_stamp: bool = True


class TemplateInfo(BaseModel):
    """Template information for API response."""
    id: str
    name_he: str
    name_en: str
    description_he: str
    description_en: str
    category: str
    placeholders: List[dict]


class DocumentGenerationResponse(BaseModel):
    """Response from document generation."""
    success: bool
    document_id: Optional[str] = None
    filename: Optional[str] = None
    path: Optional[str] = None
    download_url: Optional[str] = None
    format: Optional[str] = None
    error: Optional[str] = None
    warnings: Optional[List[str]] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_project_data(project_id: str) -> dict:
    """
    Fetch project data from database.
    TODO: Implement actual DB lookup.
    """
    # Mock project data for now
    return {
        "id": project_id,
        "name": f"Project {project_id}",
        "address": "רחוב הדוגמה 123, תל אביב",
        "gush_chalka": "6789/123",
        "permit_number": "2024-12345",
        "client_name": "לקוח לדוגמה",
    }


def notify_user(user_id: str, message: str, document_url: str):
    """
    Send notification to user about generated document.
    TODO: Implement WhatsApp/Email/Teams notification.
    """
    print(f"[NOTIFY] User {user_id}: {message}")
    print(f"[NOTIFY] Document URL: {document_url}")


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/templates", response_model=List[TemplateInfo])
async def list_templates(category: Optional[str] = None):
    """
    List available document templates.

    Args:
        category: Filter by category (plumbing, electrical, etc.)
    """
    templates = template_manager.list_templates(category)
    return [
        TemplateInfo(
            id=t.id,
            name_he=t.name_he,
            name_en=t.name_en,
            description_he=t.description_he,
            description_en=t.description_en,
            category=t.category,
            placeholders=[
                {
                    "key": p.key,
                    "label_he": p.label_he,
                    "label_en": p.label_en,
                    "source": p.source,
                    "required": p.required,
                }
                for p in t.placeholders
            ],
        )
        for t in templates
    ]


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get details for a specific template."""
    template = template_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "id": template.id,
        "name_he": template.name_he,
        "name_en": template.name_en,
        "description_he": template.description_he,
        "description_en": template.description_en,
        "category": template.category,
        "filename": template.filename,
        "placeholders": [
            {
                "key": p.key,
                "label_he": p.label_he,
                "label_en": p.label_en,
                "source": p.source,
                "required": p.required,
                "default": p.default,
            }
            for p in template.placeholders
        ],
    }


@router.post("/plumbing-affidavit", response_model=DocumentGenerationResponse)
async def generate_plumbing_affidavit(
    request: PlumbingAffidavitRequest,
    background_tasks: BackgroundTasks,
):
    """
    Generate plumbing engineer affidavit.

    This is the main automation endpoint that:
    1. Fetches engineer profile
    2. Fetches/uses project data
    3. Fills template with all placeholders
    4. Converts to PDF
    5. Adds dynamic stamp
    6. Saves and returns download link

    Args:
        request: Plumbing affidavit request with project details

    Returns:
        Document generation response with download URL
    """
    print(f"\n{'='*60}")
    print(f"[AUTOMATION] Generating Plumbing Affidavit")
    print(f"[AUTOMATION] Project: {request.project_id}")
    print(f"[AUTOMATION] Type: {request.template_type}")
    print(f"{'='*60}\n")

    # 1. Get engineer profile
    engineer_profile = get_engineer_profile_sync()
    if not engineer_profile:
        return DocumentGenerationResponse(
            success=False,
            error="Engineer profile not found. Please fill in your details first.",
        )

    print(f"[AUTOMATION] Engineer: {engineer_profile.get('full_name')}")

    # 2. Get project data
    project_data = get_project_data(request.project_id)

    # Override with request data if provided
    if request.project_address:
        project_data["address"] = request.project_address
    if request.gush_chalka:
        project_data["gush_chalka"] = request.gush_chalka
    if request.permit_number:
        project_data["permit_number"] = request.permit_number

    print(f"[AUTOMATION] Project Address: {project_data.get('address')}")

    # 3. Determine template
    template_id = "plumbing_affidavit_after" if request.template_type == "after_execution" else "plumbing_completion"

    # 4. Additional data
    manual_data = {}
    if request.work_description:
        manual_data["work_description"] = request.work_description
    if request.inspection_date:
        manual_data["inspection_date"] = request.inspection_date

    # 5. Generate document
    result = doc_generator.generate(
        template_id=template_id,
        data=manual_data,
        engineer_profile=engineer_profile,
        project_data=project_data,
        output_format="pdf",
        add_stamp=True,
    )

    if not result["success"]:
        return DocumentGenerationResponse(
            success=False,
            error=result.get("error", "Unknown error"),
        )

    # 6. Prepare response
    filename = result["filename"]
    filepath = result["path"]
    download_url = f"/api/automation/download/{filename}"

    # 7. Schedule notification (background)
    background_tasks.add_task(
        notify_user,
        user_id="default",
        message=f"התצהיר שלך נוצר ונחתם אוטומטית - {filename}",
        document_url=download_url,
    )

    print(f"\n[AUTOMATION] Document generated successfully!")
    print(f"[AUTOMATION] File: {filename}")
    print(f"[AUTOMATION] Download: {download_url}\n")

    return DocumentGenerationResponse(
        success=True,
        document_id=filename.replace(".pdf", "").replace(".docx", ""),
        filename=filename,
        path=filepath,
        download_url=download_url,
        format=result.get("format", "pdf"),
        warnings=[result.get("warning")] if result.get("warning") else None,
    )


@router.post("/generate", response_model=DocumentGenerationResponse)
async def generate_document(
    request: GenericDocumentRequest,
    background_tasks: BackgroundTasks,
):
    """
    Generic document generation endpoint.

    Generates any supported document template with provided data.
    """
    # Validate template exists
    template = template_manager.get_template(request.template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {request.template_id}")

    # Get engineer profile
    engineer_profile = get_engineer_profile_sync() if request.add_stamp else None

    # Get project data if provided
    project_data = get_project_data(request.project_id) if request.project_id else None

    # Generate document
    result = doc_generator.generate(
        template_id=request.template_id,
        data=request.data,
        engineer_profile=engineer_profile,
        project_data=project_data,
        output_format=request.output_format,
        add_stamp=request.add_stamp,
    )

    if not result["success"]:
        return DocumentGenerationResponse(
            success=False,
            error=result.get("error", "Unknown error"),
        )

    filename = result["filename"]
    download_url = f"/api/automation/download/{filename}"

    return DocumentGenerationResponse(
        success=True,
        document_id=filename.replace(".pdf", "").replace(".docx", ""),
        filename=filename,
        path=result["path"],
        download_url=download_url,
        format=result.get("format", "pdf"),
    )


@router.get("/download/{filename}")
async def download_document(filename: str):
    """
    Download a generated document.
    """
    # Check in outputs directory
    filepath = Path("outputs/documents") / filename
    if not filepath.exists():
        # Check in temp directory
        filepath = Path("temp/documents") / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    # Determine media type
    media_type = "application/pdf" if filename.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type=media_type,
    )


@router.get("/history")
async def get_generation_history(limit: int = 20):
    """
    Get history of generated documents.
    TODO: Implement DB-backed history.
    """
    # List files in output directory
    output_dir = Path("outputs/documents")
    if not output_dir.exists():
        return []

    files = sorted(output_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]

    return [
        {
            "filename": f.name,
            "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            "size_bytes": f.stat().st_size,
            "download_url": f"/api/automation/download/{f.name}",
        }
        for f in files
        if f.is_file()
    ]
