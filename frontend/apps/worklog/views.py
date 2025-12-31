"""
Worklog views for frontend.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages


@login_required
@require_http_methods(["GET"])
def index(request):
    """Worklog index page with timeline."""
    # TODO: Fetch worklogs from backend API
    return render(request, 'worklog/index.html', {
        'entries': [],
        'stats': {
            'total': 0,
            'this_month': 0,
            'this_week': 0
        }
    })


@login_required
@require_http_methods(["GET", "POST"])
def quick_add(request):
    """Quick add worklog entry."""
    if request.method == "POST":
        # TODO: Call backend API to create entry
        messages.success(request, "Worklog entry created successfully")
        return redirect('worklog:index')
    
    return render(request, 'worklog/quick_add.html')


@login_required
@require_http_methods(["GET"])
def detail(request, entry_id):
    """View/edit worklog entry detail."""
    # TODO: Fetch entry from backend API
    return render(request, 'worklog/detail.html', {
        'entry': None
    })
