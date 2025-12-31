"""
Job dispatcher - enqueues jobs for execution.
Enforces quotas and concurrency limits.
"""
from typing import Optional
from datetime import datetime
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Job

User = get_user_model()


class QuotaExceededError(Exception):
    """Raised when user/tenant quota is exceeded."""
    pass


class ConcurrencyLimitError(Exception):
    """Raised when concurrency limit is reached."""
    pass


def enqueue(
    job_type: str,
    payload: dict,
    trigger: str = 'api',
    user: Optional[User] = None,
    parent_job: Optional[Job] = None,
    scheduled_for: Optional[datetime] = None,
    max_retries: int = 3,
    enforce_quotas: bool = True,
    enforce_concurrency: bool = True
) -> Job:
    """
    Enqueue a job for execution with quota and concurrency enforcement.
    
    Args:
        job_type: Type of job (maps to workflow)
        payload: Job parameters
        trigger: How the job was triggered
        user: User who triggered the job
        parent_job: Parent job if this is a child
        scheduled_for: Schedule for future execution
        max_retries: Maximum retry attempts
        enforce_quotas: Whether to enforce quota limits (default: True)
        enforce_concurrency: Whether to enforce concurrency limits (default: True)
    
    Returns:
        Created Job instance
    
    Raises:
        QuotaExceededError: If user/tenant quota exceeded
        ConcurrencyLimitError: If concurrency limit reached
    """
    # Import here to avoid circular dependency
    from apps.tenants.quotas import QuotaManager, ConcurrencyLimiter
    from apps.tenants.models import Tenant
    
    # Get tenant for quota/concurrency checks
    tenant = None
    if user:
        try:
            tenant = Tenant.objects.get(owner=user)
        except Tenant.DoesNotExist:
            pass
    
    # Enforce quotas
    if enforce_quotas and tenant:
        quota_manager = QuotaManager(tenant)
        
        # Check job quota
        allowed, error = quota_manager.check_job_quota()
        if not allowed:
            raise QuotaExceededError(error)
        
        # Consume job quota
        quota_manager.consume_job()
    
    # Enforce concurrency limits
    if enforce_concurrency and tenant:
        concurrency_limiter = ConcurrencyLimiter(tenant, job_type)
        
        # Try to acquire concurrency slot
        job_id_temp = f'pending-{job_type}-{user.id if user else "system"}'
        acquired, error = concurrency_limiter.acquire(job_id_temp)
        if not acquired:
            raise ConcurrencyLimitError(error)
    
    # Create job
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
    
    # Release temporary concurrency slot and acquire with real job ID
    if enforce_concurrency and tenant:
        concurrency_limiter.release(job_id_temp)
        concurrency_limiter.acquire(str(job.id))
    
    # Import here to avoid circular dependency
    from apps.workers.execute_job import execute_job
    
    # Enqueue to Huey
    if scheduled_for:
        execute_job.schedule(args=(str(job.id),), eta=scheduled_for)
    else:
        execute_job(str(job.id))
    
    return job


def enqueue_safe(
    job_type: str,
    payload: dict,
    **kwargs
) -> tuple[bool, Optional[Job], Optional[str]]:
    """
    Safe version of enqueue that returns success status instead of raising.
    
    Returns:
        (success, job or None, error_message or None)
    
    Example:
        success, job, error = enqueue_safe('report.generate', {'kind': 'status'}, user=user)
        if not success:
            return Response({'error': error}, status=429)
    """
    try:
        job = enqueue(job_type, payload, **kwargs)
        return True, job, None
    except QuotaExceededError as e:
        return False, None, str(e)
    except ConcurrencyLimitError as e:
        return False, None, str(e)
    except Exception as e:
        return False, None, f'Failed to enqueue job: {str(e)}'

