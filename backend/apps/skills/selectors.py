"""
Selectors for skills queries.
"""
from typing import Optional
from django.contrib.auth import get_user_model
from .models import Skill, SkillEvidence

User = get_user_model()


def list_skills(user: Optional[User] = None, limit: int = 100):
    """List skills, optionally filtered by user."""
    qs = Skill.objects.all()
    if user:
        qs = qs.filter(user=user)
    return qs[:limit]


def get_skill(skill_id: int) -> Optional[Skill]:
    """Get a single skill by ID."""
    try:
        return Skill.objects.get(id=skill_id)
    except Skill.DoesNotExist:
        return None


def list_skill_evidence(skill_id: int, limit: int = 50):
    """List evidence for a skill."""
    return SkillEvidence.objects.filter(skill_id=skill_id)[:limit]
