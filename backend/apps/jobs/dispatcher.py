"""
Job dispatcher - enqueues jobs for execution.
"""
from typing import Optional
from datetime import datetime
from django.contrib.auth import get_user_model
from .models import Job

User = get_user_model()


def enqueue(
    job_type: str,
    payload: dict,
    trigger: str = 'api',
    user: Optional[User] = None,
    parent_job: Optional[Job] = None,
    scheduled_for: Optional[datetime] = None,
    max_retries: int = 3
) -> Job:
    """
    Enqueue a job for execution.
    
    Args:
        job_type: Type of job (maps to workflow)
        payload: Job parameters
        trigger: How the job was triggered
        user: User who triggered the job
        parent_job: Parent job if this is a child
        scheduled_for: Schedule for future execution
        max_retries: Maximum retry attempts
    
    Returns:
        Created Job instance
    """
    job = Job.objects.create(
        type=job_type,
        status='queued',
        trigger=trigger,
        payload=payload,
        user=user,
        parent_job=parent_job,
        scheduled_for=scheduled_for,
        max_retries=max_retries
    )
    
    # Import here to avoid circular dependency
    from apps.workers.execute_job import execute_job
    
    # Enqueue to Huey
    if scheduled_for:
        execute_job.schedule(args=(str(job.id),), eta=scheduled_for)
    else:
        execute_job(str(job.id))
    
    return job
