"""
API proxy views for HTMX partials.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from .services import get_backend_client
from decimal import Decimal


@login_required
@require_http_methods(["GET"])
def status_bar(request):
    """Return status bar HTML partial."""
    try:
        client = get_backend_client()
        # TODO: Call backend API for reserve balance and token counts
        balance = "—"
        tokens = "—"
        updated = "—"
    except Exception:
        balance = "—"
        tokens = "—"
        updated = "Error"
    
    html = f'''
    <div class="d-flex align-items-center gap-3 px-3">
        <div class="text-center">
            <span class="text-muted fs-12 d-block">Reserve</span>
            <span class="fw-semibold text-dark">{balance}</span>
        </div>
        <div class="vr"></div>
        <div class="text-center">
            <span class="text-muted fs-12 d-block">Tokens</span>
            <span class="fw-semibold text-dark">{tokens}</span>
        </div>
        <div class="text-muted fs-11">
            <i class="ti ti-clock me-1"></i><span>{updated}</span>
        </div>
    </div>
    '''
    return HttpResponse(html)


@login_required
@require_http_methods(["GET"])
def reserve_balance(request):
    """Return reserve balance HTML partial."""
    try:
        client = get_backend_client()
        # TODO: Call backend API for reserve balance
        balance = "—"
    except Exception:
        balance = "Error"
    
    return HttpResponse(f'<span class="text-dark">{balance}</span>')
