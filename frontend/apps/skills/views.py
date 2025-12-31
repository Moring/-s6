"""
Skills views for frontend.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods


@login_required
@require_http_methods(["GET"])
def index(request):
    """Skills index page."""
    # TODO: Fetch skills from backend API
    return render(request, 'skills/index.html', {
        'skills': []
    })
