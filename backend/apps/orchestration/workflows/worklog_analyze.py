"""
Worklog analysis workflow.
"""
from apps.jobs.registry import register
from apps.observability.services import log_event
from apps.observability.decorators import trace_step
from apps.agents.worklog_agent import WorklogAgent
from apps.orchestration.persist import persist_result


@register('worklog.analyze')
def analyze_worklog(ctx, payload: dict) -> dict:
    """
    Analyze a work log entry.
    
    Payload:
        worklog_id: ID of the work log to analyze
    
    Returns:
        analysis: dict with extracted insights
    """
    from apps.worklog.selectors import get_worklog
    
    worklog_id = payload['worklog_id']
    
    log_event(ctx, f"Analyzing worklog {worklog_id}", source='workflow')
    
    # Load worklog
    worklog = get_worklog(worklog_id)
    if not worklog:
        raise ValueError(f"WorkLog {worklog_id} not found")
    
    # Run agent
    agent = WorklogAgent()
    analysis = agent.analyze(ctx, worklog.content)
    
    # Update worklog metadata
    worklog.metadata['last_analysis'] = analysis
    worklog.save(update_fields=['metadata'])
    
    result = {
        'worklog_id': worklog_id,
        'analysis': analysis
    }
    
    return persist_result(ctx, result, f"worklog analysis for {worklog_id}")
