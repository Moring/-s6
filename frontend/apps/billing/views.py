"""
Billing views for frontend.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods


@login_required
@require_http_methods(["GET"])
def settings(request):
    """Billing settings and reserve balance."""
    # TODO: Fetch reserve balance and billing profile from backend
    return render(request, 'billing/settings.html', {
        'balance': '—',
        'profile': None
    })


@login_required
@require_http_methods(["POST"])
def topup(request):
    """Initiate top-up via Stripe Checkout."""
    # TODO: Call backend API to create Stripe checkout session
    return redirect('billing:settings')


@login_required
@require_http_methods(["GET"])
def ledger(request):
    """View reserve ledger history."""
    # TODO: Fetch ledger entries from backend
    return render(request, 'billing/ledger.html', {
        'entries': []
    })
