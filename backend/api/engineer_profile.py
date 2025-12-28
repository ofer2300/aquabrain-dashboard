"""
Engineer Profile API
====================
Endpoints for managing engineer personal details and document automation.
"""

import os
import uuid
import shutil
from datetime import datetime
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, EmailStr, field_validator

from models import SessionLocal, EngineerProfile, init_db

# Ensure DB is initialized
init_db()

router = APIRouter(prefix="/api/engineer-profile", tags=["Engineer Profile"])

# Storage paths
UPLOAD_DIR = Path("uploads/stamps")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class EngineerProfileCreate(BaseModel):
    """Request model for creating/updating engineer profile."""
    full_name: str
    id_number: str
    engineer_license: Optional[str] = None
    email: EmailStr
    email_provider: str = "gmail"
    custom_email: Optional[str] = None
    phone: str
    stamp_signature_url: Optional[str] = None
    api_keys: Optional[dict] = None
    adobe_license: Optional[str] = None
    cloud_storage: Optional[dict] = None
    is_locked: bool = False

    @field_validator('id_number')
    @classmethod
    def validate_id_number(cls, v):
        if not v or len(v) != 9 or not v.isdigit():
            raise ValueError('ID number must be exactly 9 digits')
        return v

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        # Remove dashes and validate
        clean = v.replace('-', '').replace(' ', '')
        if not clean.startswith('05') or len(clean) != 10:
            raise ValueError('Invalid Israeli phone number')
        return v

    @field_validator('email_provider')
    @classmethod
    def validate_email_provider(cls, v):
        valid_providers = ['gmail', 'outlook', 'icloud', 'other']
        if v not in valid_providers:
            raise ValueError(f'Email provider must be one of: {valid_providers}')
        return v


class EngineerProfileResponse(BaseModel):
    """Response model for engineer profile."""
    id: str
    user_id: Optional[str]
    full_name: str
    id_number: str
    engineer_license: Optional[str]
    email: str
    email_provider: str
    custom_email: Optional[str]
    phone: str
    stamp_signature_url: Optional[str]
    api_keys: Optional[dict]
    adobe_license: Optional[str]
    cloud_storage: Optional[dict]
    is_locked: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def get_default_profile(db) -> Optional[EngineerProfile]:
    """Get the default engineer profile (for single-user mode)."""
    return db.query(EngineerProfile).filter(
        EngineerProfile.user_id == None
    ).first()


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("", response_model=Optional[EngineerProfileResponse])
async def get_engineer_profile():
    """
    Get the current engineer profile.

    In single-user mode, returns the default profile.
    In multi-user mode, would filter by authenticated user_id.
    """
    db = get_db()
    try:
        profile = get_default_profile(db)
        if not profile:
            return None
        return profile.to_dict()
    finally:
        db.close()


@router.post("", response_model=EngineerProfileResponse)
async def create_or_update_profile(data: EngineerProfileCreate):
    """
    Create or update engineer profile.

    If profile exists, updates it. Otherwise, creates a new one.
    """
    db = get_db()
    try:
        profile = get_default_profile(db)

        if profile:
            # Update existing profile
            profile.full_name = data.full_name
            profile.id_number = data.id_number
            profile.engineer_license = data.engineer_license
            profile.email = data.email
            profile.email_provider = data.email_provider
            profile.custom_email = data.custom_email
            profile.phone = data.phone
            if data.stamp_signature_url:
                profile.stamp_signature_url = data.stamp_signature_url
            if data.api_keys:
                profile.set_api_keys(data.api_keys)
            profile.adobe_license = data.adobe_license
            if data.cloud_storage:
                profile.set_cloud_storage(data.cloud_storage)
            profile.is_locked = data.is_locked
            profile.updated_at = datetime.utcnow()
        else:
            # Create new profile
            profile = EngineerProfile(
                id=f"ENG-{uuid.uuid4().hex[:12].upper()}",
                user_id=None,  # Single user mode
                full_name=data.full_name,
                id_number=data.id_number,
                engineer_license=data.engineer_license,
                email=data.email,
                email_provider=data.email_provider,
                custom_email=data.custom_email,
                phone=data.phone,
                stamp_signature_url=data.stamp_signature_url,
                adobe_license=data.adobe_license,
                is_locked=data.is_locked,
            )
            if data.api_keys:
                profile.set_api_keys(data.api_keys)
            if data.cloud_storage:
                profile.set_cloud_storage(data.cloud_storage)
            db.add(profile)

        db.commit()
        db.refresh(profile)

        print(f"[PROFILE] Saved engineer profile: {profile.full_name} ({profile.id})")
        return profile.to_dict()

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to save profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/upload-stamp")
async def upload_stamp_signature(file: UploadFile = File(...)):
    """
    Upload stamp and signature image.

    Accepts PNG or JPEG images, max 2MB.
    Returns the URL to access the uploaded file.
    """
    # Validate file type
    allowed_types = ['image/png', 'image/jpeg', 'image/jpg']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {allowed_types}"
        )

    # Validate file size (2MB max)
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size must be less than 2MB"
        )

    # Generate unique filename
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    filename = f"stamp_{uuid.uuid4().hex[:12]}.{ext}"
    filepath = UPLOAD_DIR / filename

    # Save file
    with open(filepath, 'wb') as f:
        f.write(contents)

    # Return URL (relative to static files)
    url = f"/uploads/stamps/{filename}"

    # Update profile with stamp URL
    db = get_db()
    try:
        profile = get_default_profile(db)
        if profile:
            profile.stamp_signature_url = url
            profile.stamp_signature_path = str(filepath)
            db.commit()
    finally:
        db.close()

    print(f"[UPLOAD] Stamp uploaded: {filename}")

    return {
        "success": True,
        "filename": filename,
        "url": url,
        "size": len(contents),
    }


@router.delete("/stamp")
async def delete_stamp_signature():
    """
    Delete the current stamp and signature image.
    """
    db = get_db()
    try:
        profile = get_default_profile(db)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Delete file if exists
        if profile.stamp_signature_path:
            filepath = Path(profile.stamp_signature_path)
            if filepath.exists():
                filepath.unlink()

        # Clear URLs
        profile.stamp_signature_url = None
        profile.stamp_signature_path = None
        db.commit()

        return {"success": True, "message": "Stamp deleted"}

    finally:
        db.close()


@router.post("/unlock")
async def unlock_profile():
    """
    Unlock the profile for editing.
    """
    db = get_db()
    try:
        profile = get_default_profile(db)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        profile.is_locked = False
        db.commit()

        return {"success": True, "is_locked": False}

    finally:
        db.close()


# =============================================================================
# GLOBAL ACCESSOR
# =============================================================================

def get_engineer_profile_sync() -> Optional[dict]:
    """
    Synchronous accessor for engineer profile.

    Used by automation workflows to get profile data.
    Returns profile as dictionary or None if not found.
    """
    db = get_db()
    try:
        profile = get_default_profile(db)
        if profile:
            return profile.to_dict()
        return None
    finally:
        db.close()
