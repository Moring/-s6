"""
Admin panel views for frontend.
"""
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods


@staff_member_required
@require_http_methods(["GET"])
def metrics_dashboard(request):
    """Executive metrics dashboard."""
    # TODO: Fetch metrics from backend API
    return render(request, 'admin_panel/metrics_dashboard.html', {
        'metrics': {}
    })


@staff_member_required
@require_http_methods(["GET"])
def billing_admin(request):
    """Billing admin dashboard."""
    # TODO: Fetch billing summary from backend API
    return render(request, 'admin_panel/billing_admin.html', {
        'accounts': []
    })


@staff_member_required
@require_http_methods(["GET", "POST"])
def passkeys(request):
    """Manage invite passkeys."""
    if request.method == "POST":
        # TODO: Create new passkey via backend API
        pass
    
    # TODO: Fetch passkeys from backend API
    return render(request, 'admin_panel/passkeys.html', {
        'passkeys': []
    })
