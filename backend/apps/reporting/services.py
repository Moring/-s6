"""
Services for report generation.
"""
from typing import Optional
from django.contrib.auth import get_user_model
from .models import Report
from .renderers import render_report_text, render_report_html

User = get_user_model()


def create_report(
    kind: str,
    content: dict,
    user: Optional[User] = None,
    metadata: Optional[dict] = None
) -> Report:
    """Create a new report."""
    rendered_text = render_report_text(kind, content)
    rendered_html = render_report_html(kind, content)
    
    return Report.objects.create(
        user=user,
        kind=kind,
        content=content,
        rendered_text=rendered_text,
        rendered_html=rendered_html,
        metadata=metadata or {}
    )


def update_report(report_id: int, **kwargs) -> Optional[Report]:
    """Update a report."""
    try:
        report = Report.objects.get(id=report_id)
        
        # Re-render if content changed
        if 'content' in kwargs:
            kwargs['rendered_text'] = render_report_text(report.kind, kwargs['content'])
            kwargs['rendered_html'] = render_report_html(report.kind, kwargs['content'])
        
        for key, value in kwargs.items():
            setattr(report, key, value)
        report.save()
        return report
    except Report.DoesNotExist:
        return None
