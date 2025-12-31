"""
Worklog views for frontend.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from apps.api_proxy.client import get_backend_client
import json


@login_required
@require_http_methods(["GET"])
def index(request):
    """Worklog index page with timeline."""
    return render(request, 'worklog/index.html', {
        'entries': [],
        'stats': {
            'total': 0,
            'this_month': 0,
            'this_week': 0
        }
    })


@login_required
@require_http_methods(["GET"])
def quick_add_modal(request):
    """Return quick add modal HTML (HTMX partial)."""
    # Get smart suggestions from recent entries
    client = get_backend_client(request)
    recent_employers = []
    recent_projects = []
    
    try:
        worklogs = client.list_worklogs()
        if worklogs:
            # Extract unique employers/projects from metadata
            for entry in worklogs[:10]:  # Last 10 entries
                metadata = entry.get('metadata', {})
                if 'employer' in metadata and metadata['employer'] not in recent_employers:
                    recent_employers.append(metadata['employer'])
                if 'project' in metadata and metadata['project'] not in recent_projects:
                    recent_projects.append(metadata['project'])
    except:
        pass
    
    return render(request, 'worklog/quick_add_modal.html', {
        'today': timezone.now().date(),
        'recent_employers': recent_employers[:5],
        'recent_projects': recent_projects[:5],
    })


@login_required
@require_http_methods(["POST"])
def quick_add_submit(request):
    """Submit quick add worklog entry (HTMX endpoint)."""
    date = request.POST.get('date')
    content = request.POST.get('content', '').strip()
    employer = request.POST.get('employer', '').strip()
    project = request.POST.get('project', '').strip()
    tags = request.POST.get('tags', '').strip()
    
    # Validation
    if not content or len(content) < 10:
        return HttpResponse(
            '<div class="alert alert-danger">Content must be at least 10 characters</div>',
            status=400
        )
    
    # Build metadata
    metadata = {}
    if employer:
        metadata['employer'] = employer
    if project:
        metadata['project'] = project
    if tags:
        metadata['tags'] = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    # Call backend API
    client = get_backend_client(request)
    try:
        result = client.create_worklog({
            'date': date,
            'content': content,
            'source': 'manual',
            'metadata': metadata
        })
        
        if result:
            # Return updated worklog list
            return worklog_list_partial(request)
        else:
            return HttpResponse(
                '<div class="alert alert-danger">Failed to create entry. Please try again.</div>',
                status=500
            )
    except Exception as e:
        return HttpResponse(
            f'<div class="alert alert-danger">Error: {str(e)}</div>',
            status=500
        )


@login_required
@require_http_methods(["GET"])
def worklog_list_partial(request):
    """Return worklog list HTML (HTMX partial)."""
    client = get_backend_client(request)
    
    try:
        worklogs = client.list_worklogs()
        
        if not worklogs or len(worklogs) == 0:
            return render(request, 'worklog/list_empty.html')
        
        return render(request, 'worklog/list_partial.html', {
            'entries': worklogs
        })
    except Exception as e:
        return HttpResponse(
            f'<div class="alert alert-danger">Error loading worklogs: {str(e)}</div>'
        )


@login_required
@require_http_methods(["GET"])
def detail(request, entry_id):
    """View/edit worklog entry detail."""
    client = get_backend_client(request)
    
    try:
        # TODO: Backend doesn't have individual get endpoint yet, fetch from list
        worklogs = client.list_worklogs()
        entry = next((w for w in worklogs if w['id'] == entry_id), None)
        
        if not entry:
            messages.error(request, "Entry not found")
            return redirect('worklog:index')
        
        return render(request, 'worklog/detail.html', {
            'entry': entry
        })
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('worklog:index')

