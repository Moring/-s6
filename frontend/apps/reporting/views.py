"""
Reporting views for frontend.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods


@login_required
@require_http_methods(["GET"])
def index(request):
    """Reports index page."""
    # TODO: Fetch reports from backend API
    return render(request, 'reporting/index.html', {
        'reports': []
    })


@login_required
@require_http_methods(["GET", "POST"])
def generate(request):
    """Generate a new report."""
    if request.method == "POST":
        # TODO: Call backend API to generate report
        return redirect('reporting:index')
    
    return render(request, 'reporting/generate.html')
