"""
Observability services for logging events and metrics.
"""
import logging
from typing import Optional
from .models import Event, Metric
from .context import ExecutionContext

logger = logging.getLogger(__name__)


def log_event(
    ctx: ExecutionContext,
    message: str,
    level: str = 'info',
    source: str = 'system',
    **data
) -> Event:
    """
    Log an event to the job timeline.
    
    Args:
        ctx: Execution context
        message: Event message
        level: Event level (debug/info/warning/error)
        source: Event source (system/worker/workflow/agent/llm)
        **data: Additional structured data
    """
    from apps.jobs.models import Job
    
    try:
        job = Job.objects.get(id=ctx.job_id)
        event = Event.objects.create(
            job=job,
            level=level,
            source=source,
            message=message,
            data=data
        )
        
        # Also log to standard logging
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(
            log_level,
            f"[{ctx.trace_id}] [{source}] {message}",
            extra={'job_id': ctx.job_id, 'trace_id': ctx.trace_id, **data}
        )
        
        return event
    except Job.DoesNotExist:
        logger.error(f"Cannot log event: Job {ctx.job_id} not found")
        return None


def log_metric(
    name: str,
    value: float,
    tags: Optional[dict] = None
) -> Metric:
    """
    Log a system metric.
    
    Args:
        name: Metric name
        value: Metric value
        tags: Optional tags for filtering/grouping
    """
    return Metric.objects.create(
        name=name,
        value=value,
        tags=tags or {}
    )


def get_job_events(job_id: str, level: Optional[str] = None):
    """Get events for a job, optionally filtered by level."""
    from apps.jobs.models import Job
    
    try:
        job = Job.objects.get(id=job_id)
        qs = job.events.all()
        if level:
            qs = qs.filter(level=level)
        return qs
    except Job.DoesNotExist:
        return Event.objects.none()
