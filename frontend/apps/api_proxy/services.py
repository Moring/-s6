"""
Service layer for API proxy operations.
"""
from .client import get_backend_client


def get_backend_health():
    """Get backend health status."""
    client = get_backend_client()
    return client.health_check()


def get_dashboard_data():
    """Get dashboard data from backend."""
    client = get_backend_client()
    
    health = client.health_check()
    overview = client.get_system_overview()
    jobs = client.list_jobs(limit=5)
    
    return {
        'health': health,
        'overview': overview,
        'recent_jobs': jobs.get('jobs', []) if jobs else []
    }


def get_job_detail(job_id: str):
    """Get job detail and events."""
    client = get_backend_client()
    
    job = client.get_job(job_id)
    events = client.get_job_events(job_id)
    
    return {
        'job': job,
        'events': events.get('events', []) if events else []
    }
