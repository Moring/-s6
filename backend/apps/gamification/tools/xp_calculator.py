"""
Tool: Compute XP for worklog entry based on quality signals.
"""
import logging
import json
from typing import Dict, Any
from django.utils import timezone

logger = logging.getLogger(__name__)


def compute_xp(entry, attachments_count: int, tags: list, config: Dict) -> Dict[str, Any]:
    """
    Calculate XP award for a worklog entry based on quality signals.
    
    Args:
        entry: WorkLog instance
        attachments_count: Number of attachments
        tags: List of tags/skills referenced
        config: Reward configuration with XP rules
    
    Returns:
        {
            'total_xp': int,
            'breakdown': Dict[str, int],
            'capped': bool,
            'reason': str
        }
    """
    xp_rules = config.get('xp_rules', {})
    base_xp = xp_rules.get('base_entry', 10)
    attachment_xp = xp_rules.get('per_attachment', 5)
    tag_xp = xp_rules.get('per_tag', 3)
    length_bonus_threshold = xp_rules.get('length_bonus_threshold', 200)
    length_bonus_xp = xp_rules.get('length_bonus', 10)
    max_daily_xp = config.get('max_daily_xp', 200)
    
    breakdown = {
        'base': base_xp,
        'attachments': 0,
        'tags': 0,
        'length_bonus': 0,
        'metadata_bonus': 0,
    }
    
    # Attachment bonus (cap at 3 for XP)
    attachment_cap = min(attachments_count, 3)
    breakdown['attachments'] = attachment_cap * attachment_xp
    
    # Tag bonus (cap at 5 for XP)
    tag_cap = min(len(tags), 5)
    breakdown['tags'] = tag_cap * tag_xp
    
    # Length bonus
    content_length = len(entry.content.strip()) if entry.content else 0
    if content_length >= length_bonus_threshold:
        breakdown['length_bonus'] = length_bonus_xp
    
    # Metadata quality signals (outcomes, metrics, agile fields)
    metadata = entry.metadata if entry.metadata else {}
    if metadata.get('outcome') or metadata.get('impact'):
        breakdown['metadata_bonus'] += 15
    if metadata.get('metrics') or metadata.get('measurement'):
        breakdown['metadata_bonus'] += 10
    if metadata.get('blockers') or metadata.get('challenges'):
        breakdown['metadata_bonus'] += 5
    
    total_xp = sum(breakdown.values())
    
    # Check daily cap
    from apps.gamification.models import UserXP
    user_xp, _ = UserXP.objects.get_or_create(user=entry.user)
    
    today = timezone.now().date()
    if user_xp.daily_xp_date != today:
        # Reset daily counter
        user_xp.daily_xp = 0
        user_xp.daily_xp_date = today
    
    capped = False
    if user_xp.daily_xp + total_xp > max_daily_xp:
        capped = True
        total_xp = max(0, max_daily_xp - user_xp.daily_xp)
        logger.info(f"XP capped for user {entry.user.id} at daily limit {max_daily_xp}")
    
    result = {
        'total_xp': total_xp,
        'breakdown': breakdown,
        'capped': capped,
        'reason': f"Entry {entry.id} quality assessment"
    }
    
    logger.info(f"Computed XP for entry {entry.id}: {total_xp} (breakdown: {json.dumps(breakdown)})")
    
    return result
