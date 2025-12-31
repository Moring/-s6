"""
Periodic tasks for maintenance and scheduling.
"""
import logging
from huey import crontab
from .queue import db_periodic_task

logger = logging.getLogger(__name__)


@db_periodic_task(crontab(minute='*'))
def scheduler_tick():
    """Run scheduler tick every minute."""
    from apps.jobs.scheduler import tick
    
    logger.info("Running scheduler tick")
    try:
        tick()
    except Exception as e:
        logger.exception("Scheduler tick failed")


@db_periodic_task(crontab(hour='*/6'))
def cleanup_old_jobs():
    """Cleanup old completed jobs (stub for MVP)."""
    from django.utils import timezone
    from datetime import timedelta
    from apps.jobs.models import Job
    
    logger.info("Running job cleanup")
    
    # Delete completed jobs older than 30 days
    cutoff = timezone.now() - timedelta(days=30)
    deleted_count, _ = Job.objects.filter(
        status__in=['success', 'failed'],
        finished_at__lt=cutoff
    ).delete()
    
    logger.info(f"Deleted {deleted_count} old jobs")
