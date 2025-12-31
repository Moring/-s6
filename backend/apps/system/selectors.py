"""
System dashboard selectors.
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from apps.jobs.models import Job, Schedule


def get_system_overview() -> dict:
    """Get system overview stats."""
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    
    # Job stats
    job_stats = Job.objects.aggregate(
        total=Count('id'),
        queued=Count('id', filter=Q(status='queued')),
        running=Count('id', filter=Q(status='running')),
        success=Count('id', filter=Q(status='success')),
        failed=Count('id', filter=Q(status='failed')),
        failed_24h=Count('id', filter=Q(status='failed', finished_at__gte=last_24h))
    )
    
    # Schedule stats
    schedule_stats = Schedule.objects.aggregate(
        total=Count('id'),
        enabled=Count('id', filter=Q(enabled=True))
    )
    
    return {
        'jobs': job_stats,
        'schedules': schedule_stats,
        'timestamp': now
    }


def get_recent_jobs(limit: int = 50, status: str = None, job_type: str = None):
    """Get recent jobs with optional filters."""
    qs = Job.objects.all()
    
    if status:
        qs = qs.filter(status=status)
    if job_type:
        qs = qs.filter(type=job_type)
    
    return qs[:limit]


def get_job_by_id(job_id: str):
    """Get job by ID."""
    try:
        return Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return None


def get_schedules():
    """Get all schedules."""
    return Schedule.objects.all()
