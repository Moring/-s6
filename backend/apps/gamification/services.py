"""
Gamification business logic services.
"""
import logging
from typing import Dict, Any
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.jobs.dispatcher import enqueue

User = get_user_model()
logger = logging.getLogger(__name__)


def trigger_reward_evaluation(entry_id: int, user_id: int) -> Dict[str, Any]:
    """
    Enqueue reward evaluation job for a worklog entry.
    
    Args:
        entry_id: WorkLog ID
        user_id: User ID (for tenant scoping)
    
    Returns:
        Job details
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'error': 'User not found'}
    
    job = enqueue(
        job_type='gamification.reward_evaluate',
        payload={'entry_id': entry_id},
        user=user,
        trigger='api'
    )
    
    logger.info(f"Enqueued reward evaluation job {job.id} for entry {entry_id}")
    
    return {
        'success': True,
        'job_id': str(job.id),
        'status': job.status
    }


@transaction.atomic
def manual_grant_xp(user_id: int, amount: int, reason: str, granted_by_user_id: int) -> Dict[str, Any]:
    """
    Manually grant XP to a user (admin action).
    
    Args:
        user_id: Target user ID
        amount: XP amount
        reason: Admin reason
        granted_by_user_id: Admin user ID
    
    Returns:
        Grant result
    """
    from apps.gamification.models import XPEvent, UserXP
    
    try:
        user = User.objects.get(id=user_id)
        granted_by = User.objects.get(id=granted_by_user_id)
    except User.DoesNotExist:
        return {'success': False, 'error': 'User not found'}
    
    idempotency_key = f"manual_xp:{user_id}:{granted_by_user_id}:{timezone.now().isoformat()}"
    
    event = XPEvent.objects.create(
        user=user,
        amount=amount,
        reason=f"Manual grant by admin: {reason}",
        worklog_entry=None,
        idempotency_key=idempotency_key,
        metadata={'granted_by': granted_by.id, 'admin_action': True}
    )
    
    user_xp, _ = UserXP.objects.get_or_create(user=user)
    user_xp.total_xp += amount
    new_level = 1 + (user_xp.total_xp // 100)
    user_xp.level = new_level
    user_xp.save()
    
    logger.info(f"Admin {granted_by.id} granted {amount} XP to user {user.id}")
    
    return {
        'success': True,
        'event_id': str(event.id),
        'new_total_xp': user_xp.total_xp,
        'new_level': user_xp.level,
    }


@transaction.atomic
def manual_revoke_badge(user_id: int, badge_code: str, reason: str, revoked_by_user_id: int) -> Dict[str, Any]:
    """
    Manually revoke a badge from a user (admin action).
    
    Args:
        user_id: Target user ID
        badge_code: Badge code to revoke
        reason: Admin reason
        revoked_by_user_id: Admin user ID
    
    Returns:
        Revoke result
    """
    from apps.gamification.models import BadgeDefinition, UserBadge
    
    try:
        user = User.objects.get(id=user_id)
        revoked_by = User.objects.get(id=revoked_by_user_id)
        badge_def = BadgeDefinition.objects.get(code=badge_code)
    except (User.DoesNotExist, BadgeDefinition.DoesNotExist):
        return {'success': False, 'error': 'User or badge not found'}
    
    try:
        user_badge = UserBadge.objects.get(user=user, badge=badge_def)
        user_badge.delete()
        
        logger.info(f"Admin {revoked_by.id} revoked badge {badge_code} from user {user.id}")
        
        return {'success': True, 'revoked': badge_code}
    
    except UserBadge.DoesNotExist:
        return {'success': False, 'error': 'User does not have this badge'}


from django.utils import timezone
