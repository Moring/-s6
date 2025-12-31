"""
Report generation workflow.
"""
from apps.jobs.registry import register
from apps.observability.services import log_event
from apps.agents.report_agent import ReportAgent
from apps.orchestration.persist import persist_result


@register('report.generate')
def generate_report(ctx, payload: dict) -> dict:
    """
    Generate a report (status, standup, etc).
    
    Payload:
        user_id: User ID (optional)
        kind: Report kind (status, standup, summary)
        window_days: Number of days to include (default 7)
    
    Returns:
        report_id: ID of created report
    """
    from apps.reporting.services import create_report
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    user_id = payload.get('user_id')
    kind = payload.get('kind', 'status')
    window_days = payload.get('window_days', 7)
    
    user = User.objects.get(id=user_id) if user_id else None
    
    log_event(ctx, f"Generating {kind} report for user {user_id}", source='workflow')
    
    # Run agent
    agent = ReportAgent()
    report_content = agent.generate_report(ctx, user=user, kind=kind, window_days=window_days)
    
    # Create report
    report = create_report(
        kind=kind,
        content=report_content,
        user=user,
        metadata={'window_days': window_days}
    )
    
    result = {
        'report_id': report.id,
        'kind': kind,
        'user_id': user_id
    }
    
    return persist_result(ctx, result, f"{kind} report generated")
