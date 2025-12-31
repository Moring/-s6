"""
Tool: Persist reward events (XP grants, badge awards, etc) with idempotency.
"""
import logging
from typing import Dict, Any, Optional
from django.db import IntegrityError, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def persist_xp_event(user, amount: int, reason: str, worklog_entry, 
                     idempotency_key: str, metadata: Dict = None) -> Optional[Dict]:
    """
    Persist an XP grant event (idempotent).
    
    Args:
        user: User instance
        amount: XP amount to grant
        reason: Reason for XP grant
        worklog_entry: WorkLog instance (nullable)
        idempotency_key: Unique key to prevent double-grant
        metadata: Additional metadata
    
    Returns:
        Event details if created, None if duplicate
    """
    from apps.gamification.models import XPEvent, UserXP
    
    try:
        with transaction.atomic():
            # Try to create event
            event = XPEvent.objects.create(
                user=user,
                amount=amount,
                reason=reason,
                worklog_entry=worklog_entry,
                idempotency_key=idempotency_key,
                metadata=metadata or {}
            )
            
            # Update user's total XP
            user_xp, _ = UserXP.objects.get_or_create(user=user)
            user_xp.total_xp += amount
            user_xp.daily_xp += amount
            
            # Update level (simple formula: level = 1 + total_xp // 100)
            new_level = 1 + (user_xp.total_xp // 100)
            level_up = new_level > user_xp.level
            user_xp.level = new_level
            
            user_xp.save()
            
            logger.info(f"Persisted XP event: user={user.id}, amount={amount}, new_total={user_xp.total_xp}, level={new_level}")
            
            return {
                'event_id': str(event.id),
                'amount': amount,
                'new_total': user_xp.total_xp,
                'new_level': user_xp.level,
                'level_up': level_up,
            }
    
    except IntegrityError:
        logger.info(f"XP event already exists with key {idempotency_key}, skipping")
        return None


def persist_events(xp_result: Dict, user, worklog_entry, job_id: str) -> Dict[str, Any]:
    """
    Persist all reward events from a DAG run.
    
    Args:
        xp_result: XP calculation result
        user: User instance
        worklog_entry: WorkLog instance
        job_id: Job ID for idempotency
    
    Returns:
        Summary of persisted events
    """
    summary = {
        'xp_granted': False,
        'xp_amount': 0,
        'errors': []
    }
    
    try:
        if xp_result['total_xp'] > 0:
            idempotency_key = f"xp:{user.id}:{worklog_entry.id}:{job_id}"
            result = persist_xp_event(
                user=user,
                amount=xp_result['total_xp'],
                reason=xp_result['reason'],
                worklog_entry=worklog_entry,
                idempotency_key=idempotency_key,
                metadata={
                    'breakdown': xp_result['breakdown'],
                    'capped': xp_result['capped'],
                    'job_id': job_id,
                }
            )
            
            if result:
                summary['xp_granted'] = True
                summary['xp_amount'] = result['amount']
                summary['level_up'] = result.get('level_up', False)
    
    except Exception as e:
        logger.error(f"Error persisting XP event: {e}", exc_info=True)
        summary['errors'].append(f"XP persist error: {str(e)}")
    
    return summary
