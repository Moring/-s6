"""
Job policies - retry, idempotency, etc.
"""
from datetime import timedelta
from django.utils import timezone


def should_retry(job) -> bool:
    """Determine if a failed job should be retried."""
    return job.retry_count < job.max_retries


def calculate_retry_delay(retry_count: int) -> timedelta:
    """
    Calculate exponential backoff delay for retries.
    
    retry 1: 30 seconds
    retry 2: 2 minutes
    retry 3: 8 minutes
    """
    base_delay = 30  # seconds
    delay_seconds = base_delay * (2 ** retry_count)
    return timedelta(seconds=delay_seconds)


def is_idempotent_duplicate(job) -> bool:
    """
    Check if this job is a duplicate that can be skipped.
    
    MVP stub - implement idempotency logic based on:
    - job type
    - payload fingerprint
    - time window
    """
    # TODO: Implement idempotency checking
    return False
