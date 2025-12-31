"""
Selectors for reporting queries.
"""
from typing import Optional
from django.contrib.auth import get_user_model
from .models import Report

User = get_user_model()


def list_reports(user: Optional[User] = None, kind: Optional[str] = None, limit: int = 50):
    """List reports, optionally filtered by user and kind."""
    qs = Report.objects.all()
    if user:
        qs = qs.filter(user=user)
    if kind:
        qs = qs.filter(kind=kind)
    return qs[:limit]


def get_report(report_id: int) -> Optional[Report]:
    """Get a single report by ID."""
    try:
        return Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return None


def get_latest_report(user: Optional[User] = None, kind: str = 'resume') -> Optional[Report]:
    """Get the most recent report of a given kind."""
    qs = Report.objects.filter(kind=kind)
    if user:
        qs = qs.filter(user=user)
    return qs.first()
