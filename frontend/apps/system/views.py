"""
System dashboard views for frontend.
"""
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods


@staff_member_required
@require_http_methods(["GET"])
def index(request):
    """System dashboard index."""
    # TODO: Fetch system metrics from backend API
    return render(request, 'system/index.html', {
        'system_status': {}
    })
