"""
AquaBrain Skills API
====================
API for skill catalog browsing and custom skill management.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from skills.base import skill_registry, SkillCategory

router = APIRouter(prefix="/api/skills", tags=["Skills"])


class SkillSearchRequest(BaseModel):
    """Search request for skills."""
    query: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


@router.get("/catalog")
async def get_skill_catalog():
    """
    📚 Get Full Skill Catalog

    Returns all registered skills organized by category.
    Useful for building skill browser UIs.
    """
    skills = skill_registry.list_all()

    # Group by category
    by_category = {}
    for skill in skills:
        cat = skill.metadata.category.value
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append({
            "id": skill.metadata.id,
            "name": skill.metadata.name,
            "description": skill.metadata.description,
            "icon": skill.metadata.icon,
            "color": skill.metadata.color,
            "tags": skill.metadata.tags,
        })

    return {
        "categories": by_category,
        "total_skills": len(skills),
        "category_counts": {cat: len(skills) for cat, skills in by_category.items()}
    }


@router.post("/search")
async def search_skills(request: SkillSearchRequest):
    """
    🔍 Search Skills

    Search for skills by name, description, or tags.
    Supports filtering by category.
    """
    skills = skill_registry.list_all()

    # Filter by query
    if request.query:
        query = request.query.lower()
        skills = [
            s for s in skills
            if (query in s.metadata.name.lower() or
                query in s.metadata.description.lower() or
                any(query in tag.lower() for tag in s.metadata.tags))
        ]

    # Filter by category
    if request.category:
        try:
            cat = SkillCategory(request.category)
            skills = [s for s in skills if s.metadata.category == cat]
        except ValueError:
            pass

    # Filter by tags
    if request.tags:
        skills = [
            s for s in skills
            if any(tag in s.metadata.tags for tag in request.tags)
        ]

    return {
        "results": [
            {
                "id": s.metadata.id,
                "name": s.metadata.name,
                "description": s.metadata.description,
                "category": s.metadata.category.value,
                "icon": s.metadata.icon,
                "color": s.metadata.color,
                "tags": s.metadata.tags,
            }
            for s in skills
        ],
        "total": len(skills)
    }


@router.get("/categories")
async def list_categories():
    """
    📂 List Skill Categories

    Returns all available skill categories with counts.
    """
    skills = skill_registry.list_all()

    # Count by category
    counts = {}
    for cat in SkillCategory:
        count = len([s for s in skills if s.metadata.category == cat])
        counts[cat.value] = {
            "name": cat.value.replace("_", " ").title(),
            "count": count
        }

    return {"categories": counts}


@router.get("/{skill_id}/schema")
async def get_skill_schema(skill_id: str):
    """
    📝 Get Skill Input Schema

    Returns the JSON Schema for a skill's inputs.
    Use this to dynamically generate forms.
    """
    skill = skill_registry.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    return {
        "skill_id": skill_id,
        "schema": skill.input_schema.to_json_schema(),
        "fields": [f.model_dump() for f in skill.input_schema.fields]
    }
