"""
Job scheduler - manages scheduled job execution.
"""
from datetime import datetime, timedelta
from django.utils import timezone
from croniter import croniter
from .models import Schedule
from .dispatcher import enqueue


def tick():
    """
    Check schedules and enqueue jobs that are due.
    Called periodically by worker.
    """
    now = timezone.now()
    
    for schedule in Schedule.objects.filter(enabled=True):
        if should_run(schedule, now):
            # Enqueue the job
            enqueue(
                job_type=schedule.job_type,
                payload=schedule.payload,
                trigger='schedule'
            )
            
            # Update last run
            schedule.last_run_at = now
            schedule.save(update_fields=['last_run_at'])


def should_run(schedule: Schedule, now: datetime) -> bool:
    """Check if a schedule should run now."""
    # Handle special cron expressions
    if schedule.cron == '@every_minute':
        if not schedule.last_run_at:
            return True
        return (now - schedule.last_run_at) >= timedelta(minutes=1)
    
    if schedule.cron == '@hourly':
        if not schedule.last_run_at:
            return True
        return (now - schedule.last_run_at) >= timedelta(hours=1)
    
    if schedule.cron == '@daily':
        if not schedule.last_run_at:
            return True
        return (now - schedule.last_run_at) >= timedelta(days=1)
    
    # Handle standard cron expressions
    try:
        cron = croniter(schedule.cron, schedule.last_run_at or now)
        next_run = cron.get_next(datetime)
        return now >= next_run
    except Exception:
        # Invalid cron expression
        return False


def create_schedule(
    name: str,
    job_type: str,
    cron: str,
    payload: dict = None,
    enabled: bool = True
) -> Schedule:
    """Create a new schedule."""
    return Schedule.objects.create(
        name=name,
        job_type=job_type,
        cron=cron,
        payload=payload or {},
        enabled=enabled
    )
