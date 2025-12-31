"""
UI views for frontend.
"""
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from apps.api_proxy.services import get_backend_health, get_dashboard_data, get_job_detail


@require_http_methods(["GET"])
def index(request):
    """Homepage showing system dashboard."""
    try:
        data = get_dashboard_data()
    except Exception as e:
        data = {
            'health': {'status': 'error', 'error': str(e)},
            'overview': None,
            'recent_jobs': []
        }
    
    return render(request, 'ui/index.html', data)


@require_http_methods(["GET"])
def health(request):
    """Frontend health check."""
    backend_health = get_backend_health()
    
    return render(request, 'ui/health.html', {
        'frontend_status': 'ok',
        'backend': backend_health
    })


@require_http_methods(["GET"])
def jobs_list(request):
    """List all jobs."""
    from apps.api_proxy.client import get_backend_client
    
    client = get_backend_client()
    status_filter = request.GET.get('status')
    
    jobs_data = client.list_jobs(status=status_filter, limit=50)
    
    return render(request, 'ui/jobs_list.html', {
        'jobs': jobs_data.get('jobs', []) if jobs_data else [],
        'status_filter': status_filter
    })


@require_http_methods(["GET"])
def job_detail(request, job_id):
    """Show job detail and events."""
    data = get_job_detail(job_id)
    
    return render(request, 'ui/job_detail.html', {
        'job': data['job'],
        'events': data['events']
    })
