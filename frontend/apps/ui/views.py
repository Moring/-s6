"""
UI views for frontend.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from apps.api_proxy.services import get_backend_health, get_dashboard_data, get_job_detail
from apps.api_proxy.client import get_backend_client


@require_http_methods(["GET"])
def index(request):
    """Public homepage - redirects to dashboard if logged in."""
    if request.user.is_authenticated:
        return redirect('ui:dashboard')
    return redirect('account_login')


@login_required
@require_http_methods(["GET"])
def dashboard(request):
    """Main dashboard showing system overview."""
    health = get_backend_health()
    dashboard = get_dashboard_data()
    
    return render(request, 'ui/dashboard.html', {
        'health': health,
        'overview': dashboard.get('overview', {}) if dashboard else {},
        'recent_jobs': dashboard.get('recent_jobs', []) if dashboard else []
    })


@login_required
@require_http_methods(["POST"])
def upload_file(request):
    """Handle file upload."""
    if 'file' not in request.FILES:
        messages.error(request, "No file selected")
        return redirect('index')
    
    file = request.FILES['file']
    client = get_backend_client()
    
    try:
        # Forward file to backend
        response = client.upload_file(file, auth=request.user)
        if response:
            messages.success(request, f"File '{file.name}' uploaded successfully")
        else:
            messages.error(request, "Upload failed")
    except Exception as e:
        messages.error(request, f"Upload error: {e}")
    
    return redirect('index')


@require_http_methods(["GET"])
def health(request):
    """Frontend health check (no auth required)."""
    backend_health = get_backend_health()
    
    return render(request, 'ui/health.html', {
        'frontend_status': 'ok',
        'backend': backend_health
    })


@login_required
@require_http_methods(["GET"])
def jobs_list(request):
    """List all jobs."""
    client = get_backend_client()
    status_filter = request.GET.get('status')
    
    jobs_data = client.list_jobs(status=status_filter, limit=50)
    
    return render(request, 'ui/jobs_list.html', {
        'jobs': jobs_data.get('jobs', []) if jobs_data else [],
        'status_filter': status_filter
    })


@login_required
@require_http_methods(["GET"])
def job_detail(request, job_id):
    """Show job detail and events."""
    data = get_job_detail(job_id)
    
    return render(request, 'ui/job_detail.html', {
        'job': data['job'],
        'events': data['events']
    })
