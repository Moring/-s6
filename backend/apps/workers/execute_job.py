"""
Main job execution worker task.
"""
import logging
from datetime import datetime
from django.utils import timezone
from .queue import db_task

logger = logging.getLogger(__name__)


@db_task()
def execute_job(job_id: str):
    """
    Execute a job by ID.
    
    This is the main worker task that:
    1. Loads the job
    2. Transitions to running
    3. Executes the workflow
    4. Stores results
    5. Handles errors and retries
    6. Releases concurrency slots
    """
    from apps.jobs.models import Job
    from apps.jobs.registry import get_workflow
    from apps.jobs.policies import should_retry, calculate_retry_delay
    from apps.jobs.dispatcher import enqueue
    from apps.observability.context import ExecutionContext
    from apps.observability.services import log_event
    from apps.tenants.quotas import ConcurrencyLimiter
    from apps.tenants.models import Tenant
    
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        return
    
    # Get tenant for concurrency release
    tenant = None
    if job.user:
        try:
            tenant = Tenant.objects.get(owner=job.user)
        except Tenant.DoesNotExist:
            pass
    
    # Create execution context
    ctx = ExecutionContext.from_job(job)
    
    # Transition to running
    job.status = 'running'
    job.started_at = timezone.now()
    job.save(update_fields=['status', 'started_at'])
    
    log_event(ctx, f"Job started: {job.type}", level='info', source='worker')
    
    try:
        # Get workflow function
        workflow = get_workflow(job.type)
        
        # Execute workflow
        result = workflow(ctx, job.payload)
        
        # Mark success
        job.status = 'success'
        job.result = result
        job.finished_at = timezone.now()
        job.save(update_fields=['status', 'result', 'finished_at'])
        
        log_event(ctx, f"Job completed successfully", level='info', source='worker')
        
        # Release concurrency slot on success
        if tenant:
            concurrency_limiter = ConcurrencyLimiter(tenant, job.type)
            concurrency_limiter.release(str(job.id))
        
    except Exception as e:
        logger.exception(f"Job {job_id} failed")
        
        job.error = str(e)
        job.finished_at = timezone.now()
        
        # Check if we should retry
        if should_retry(job):
            job.retry_count += 1
            job.status = 'queued'  # Re-queue for retry
            job.save(update_fields=['status', 'error', 'retry_count', 'finished_at'])
            
            # Schedule retry with backoff
            delay = calculate_retry_delay(job.retry_count)
            scheduled_for = timezone.now() + delay
            
            log_event(
                ctx,
                f"Job failed, retrying (attempt {job.retry_count}/{job.max_retries})",
                level='warning',
                source='worker',
                error=str(e),
                retry_delay_seconds=delay.total_seconds()
            )
            
            # Do NOT release concurrency slot - it stays acquired for retry
            
            enqueue(
                job_type=job.type,
                payload=job.payload,
                trigger='retry',
                user=job.user,
                parent_job=job.parent_job,
                scheduled_for=scheduled_for,
                max_retries=job.max_retries,
                enforce_quotas=False,  # Don't re-check quotas on retry
                enforce_concurrency=False  # Slot already held
            )
        else:
            job.status = 'failed'
            job.save(update_fields=['status', 'error', 'finished_at'])
            
            log_event(
                ctx,
                f"Job failed permanently",
                level='error',
                source='worker',
                error=str(e)
            )
            
            # Release concurrency slot on permanent failure
            if tenant:
                concurrency_limiter = ConcurrencyLimiter(tenant, job.type)
                concurrency_limiter.release(str(job.id))

