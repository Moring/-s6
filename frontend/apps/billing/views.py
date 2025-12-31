"""
Billing views for frontend.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from apps.api_proxy.client import get_backend_client


@login_required
@require_http_methods(["GET"])
def settings(request):
    """Billing settings and reserve balance."""
    client = get_backend_client(request)
    
    # Fetch reserve balance
    balance_data = {}
    is_low_balance = False
    try:
        balance_response = client.get('/api/billing/reserve/balance/')
        balance_data = balance_response
        is_low_balance = balance_data.get('is_low_balance', False)
    except Exception as e:
        messages.warning(request, "Unable to fetch balance data. Please try again.")
        balance_data = {'balance_cents': 0, 'balance_dollars': 0.0}
    
    # Fetch billing profile
    profile_data = {}
    try:
        profile_response = client.get('/api/billing/profile/')
        profile_data = profile_response
    except Exception:
        # Profile might not exist yet, graceful fallback
        profile_data = {
            'plan_tier': 'free',
            'stripe_customer_id': None,
            'auto_topup_enabled': False
        }
    
    return render(request, 'billing/settings.html', {
        'balance': balance_data.get('balance_dollars', 0.0),
        'balance_cents': balance_data.get('balance_cents', 0),
        'profile': profile_data,
        'is_low_balance': is_low_balance
    })


@login_required
@require_http_methods(["POST"])
def topup(request):
    """Initiate top-up via Stripe Checkout."""
    client = get_backend_client(request)
    
    # Get amount from form (default to $50)
    amount_dollars = request.POST.get('amount', '50')
    
    try:
        # Call backend to create Stripe checkout session
        response = client.post('/api/billing/topup/session/', {
            'amount_dollars': float(amount_dollars)
        })
        
        # Redirect to Stripe checkout
        checkout_url = response.get('checkout_url')
        if checkout_url:
            return redirect(checkout_url)
        else:
            messages.error(request, "Failed to create checkout session. Please try again.")
    except Exception as e:
        messages.error(request, f"Error initiating top-up: {str(e)}")
    
    return redirect('billing:settings')


@login_required
@require_http_methods(["GET"])
def ledger(request):
    """View reserve ledger history."""
    client = get_backend_client(request)
    
    # Pagination
    page = request.GET.get('page', 1)
    
    try:
        response = client.get(f'/api/billing/reserve/ledger/?page={page}')
        entries = response.get('results', [])
        count = response.get('count', 0)
        next_page = response.get('next')
        prev_page = response.get('previous')
    except Exception as e:
        messages.warning(request, "Unable to fetch ledger data.")
        entries = []
        count = 0
        next_page = None
        prev_page = None
    
    return render(request, 'billing/ledger.html', {
        'entries': entries,
        'count': count,
        'next_page': next_page,
        'prev_page': prev_page
    })
