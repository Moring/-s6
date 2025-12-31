"""
Selectors for worklog queries.
"""
from typing import Optional
from django.contrib.auth import get_user_model
from .models import WorkLog

User = get_user_model()


def list_worklogs(user: Optional[User] = None, limit: int = 50):
    """List work logs, optionally filtered by user."""
    qs = WorkLog.objects.all()
    if user:
        qs = qs.filter(user=user)
    return qs[:limit]


def get_worklog(worklog_id: int) -> Optional[WorkLog]:
    """Get a single work log by ID."""
    try:
        return WorkLog.objects.get(id=worklog_id)
    except WorkLog.DoesNotExist:
        return None
