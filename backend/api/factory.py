"""
AquaBrain Skill Factory API
============================
LLM-powered skill generation - "The System Builds Itself"

Endpoints:
- POST /api/factory/generate - Generate a new skill from description
- GET /api/factory/custom - List all custom skills
- DELETE /api/factory/custom/{skill_id} - Delete a custom skill
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from services.factory import get_factory, generate_skill

router = APIRouter(prefix="/api/factory", tags=["Skill Factory"])


class GenerateSkillRequest(BaseModel):
    """Request to generate a new skill."""
    description: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Natural language description of what the skill should do"
    )
    use_llm: bool = Field(
        False,
        description="Use LLM for generation (requires ANTHROPIC_API_KEY)"
    )


class GenerateSkillResponse(BaseModel):
    """Response from skill generation."""
    skill_id: str
    name: str
    description: str
    category: str
    icon: str
    color: str
    fields_count: int
    file_path: str
    generated_at: str


@router.post("/generate", response_model=GenerateSkillResponse)
async def generate_new_skill(request: GenerateSkillRequest):
    """
    🏭 Generate a New Skill from Description

    The LLM Contractor - converts natural language into functional skills.

    Example:
    ```json
    POST /api/factory/generate
    {
        "description": "Calculate the area of a rectangle given width and height",
        "use_llm": false
    }
    ```

    Returns the generated skill metadata. The skill is immediately
    registered and available via /api/orchestrator/trigger.
    """
    try:
        result = generate_skill(
            description=request.description,
            use_llm=request.use_llm
        )

        return GenerateSkillResponse(
            skill_id=result["skill_id"],
            name=result["name"],
            description=result["description"],
            category=result["category"],
            icon=result["icon"],
            color=result["color"],
            fields_count=result["fields_count"],
            file_path=result["file_path"],
            generated_at=result["generated_at"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill generation failed: {str(e)}")


@router.get("/custom")
async def list_custom_skills():
    """
    📋 List Custom Skills

    Returns all skills generated via the factory.
    """
    factory = get_factory()
    skills = factory.list_custom_skills()

    return {
        "skills": skills,
        "total": len(skills),
        "output_dir": str(factory.output_dir)
    }


@router.delete("/custom/{skill_id}")
async def delete_custom_skill(skill_id: str):
    """
    🗑️ Delete a Custom Skill

    Remove a generated skill from the registry and filesystem.
    """
    factory = get_factory()

    if factory.delete_custom_skill(skill_id):
        return {"message": f"Skill '{skill_id}' deleted", "skill_id": skill_id}
    else:
        raise HTTPException(status_code=404, detail=f"Custom skill '{skill_id}' not found")


@router.get("/history")
async def get_generation_history():
    """
    📜 Get Generation History

    Returns history of all skills generated in this session.
    """
    factory = get_factory()

    return {
        "generated_skills": factory.generated_skills,
        "total": len(factory.generated_skills)
    }
