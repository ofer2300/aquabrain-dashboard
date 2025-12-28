"""
AquaBrain Skill System V2.0
===========================
Dynamic skill factory with auto-registration.

Features:
- AquaSkill base class with standardized interface
- InputSchema for dynamic form generation
- SkillRegistry for skill discovery and management
- @register_skill decorator for auto-registration
"""

from .base import (
    AquaSkill,
    SkillMetadata,
    InputSchema,
    InputField,
    FieldType,
    SkillCategory,
    ExecutionResult,
    ExecutionStatus,
    skill_registry,
    register_skill,
)

# Import builtin skills to register them
from . import builtin

# Import native skills (platform core)
from . import native

# Import library skills (WhatsApp, Email, etc.)
try:
    from . import library
except ImportError as e:
    print(f"[WARN] Library skills not loaded: {e}")

__all__ = [
    'AquaSkill',
    'SkillMetadata',
    'InputSchema',
    'InputField',
    'FieldType',
    'SkillCategory',
    'ExecutionResult',
    'ExecutionStatus',
    'skill_registry',
    'register_skill',
]
