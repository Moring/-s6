"""
Services for skill business logic.
"""
from typing import Optional
from django.contrib.auth import get_user_model
from .models import Skill, SkillEvidence
from .normalization import normalize_skill_name

User = get_user_model()


def create_skill(
    name: str,
    user: Optional[User] = None,
    confidence: float = 0.0,
    level: Optional[str] = None,
    metadata: Optional[dict] = None
) -> Skill:
    """Create or update a skill."""
    normalized = normalize_skill_name(name)
    skill, created = Skill.objects.update_or_create(
        user=user,
        normalized=normalized,
        defaults={
            'name': name,
            'confidence': confidence,
            'level': level,
            'metadata': metadata or {}
        }
    )
    return skill


def add_skill_evidence(
    skill: Skill,
    source_type: str,
    source_id: int,
    excerpt: str = '',
    weight: float = 1.0
) -> SkillEvidence:
    """Add evidence for a skill."""
    return SkillEvidence.objects.create(
        skill=skill,
        source_type=source_type,
        source_id=source_id,
        excerpt=excerpt,
        weight=weight
    )
