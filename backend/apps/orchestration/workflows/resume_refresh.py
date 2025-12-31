"""
Resume refresh workflow.
"""
from apps.jobs.registry import register
from apps.observability.services import log_event
from apps.agents.resume_agent import ResumeAgent
from apps.orchestration.persist import persist_result


@register('resume.refresh')
def refresh_resume(ctx, payload: dict) -> dict:
    """
    Refresh user's resume.
    
    Payload:
        user_id: User ID (optional)
    
    Returns:
        report_id: ID of created resume report
    """
    from apps.reporting.services import create_report
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    user_id = payload.get('user_id')
    user = User.objects.get(id=user_id) if user_id else None
    
    log_event(ctx, f"Refreshing resume for user {user_id}", source='workflow')
    
    # Run agent
    agent = ResumeAgent()
    resume_content = agent.generate_resume(ctx, user=user)
    
    # Create report
    report = create_report(
        kind='resume',
        content=resume_content,
        user=user,
        metadata={'auto_generated': True}
    )
    
    result = {
        'report_id': report.id,
        'user_id': user_id
    }
    
    return persist_result(ctx, result, "resume refreshed")
