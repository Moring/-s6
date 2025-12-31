"""
Services for worklog business logic.
"""
from datetime import date
from typing import Optional
from django.contrib.auth import get_user_model
from .models import WorkLog

User = get_user_model()


def create_worklog(
    date: date,
    content: str,
    source: str = 'manual',
    user: Optional[User] = None,
    metadata: Optional[dict] = None
) -> WorkLog:
    """Create a new work log entry."""
    worklog = WorkLog.objects.create(
        user=user,
        date=date,
        content=content,
        source=source,
        metadata=metadata or {}
    )
    
    # Trigger reward evaluation asynchronously
    if user:
        from apps.gamification.services import trigger_reward_evaluation
        trigger_reward_evaluation(worklog.id, user.id)
    
    return worklog


def update_worklog(worklog_id: int, **kwargs) -> Optional[WorkLog]:
    """Update a work log entry."""
    try:
        worklog = WorkLog.objects.get(id=worklog_id)
        for key, value in kwargs.items():
            setattr(worklog, key, value)
        worklog.save()
        
        # Trigger reward evaluation asynchronously on update
        if worklog.user:
            from apps.gamification.services import trigger_reward_evaluation
            trigger_reward_evaluation(worklog.id, worklog.user.id)
        
        return worklog
    except WorkLog.DoesNotExist:
        return None
