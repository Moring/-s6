"""
Admin panel views for frontend.
"""
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from apps.api_proxy.client import get_backend_client


@staff_member_required
@require_http_methods(["GET"])
def metrics_dashboard(request):
    """Executive metrics dashboard."""
    client = get_backend_client(request)
    
    # Fetch metrics summary from backend
    try:
        response = client.get('/api/system/metrics/summary/')
        metrics = response if response else {}
    except Exception:
        metrics = {}
    
    # Check for active alerts (placeholder logic)
    alerts = []
    if metrics.get('churn_rate', 0) > 10:
        alerts.append({
            'title': 'High Churn Rate',
            'message': f'Current churn rate ({metrics.get("churn_rate")}%) is above threshold'
        })
    if metrics.get('error_rate', 0) > 5:
        alerts.append({
            'title': 'High Error Rate',
            'message': f'API error rate ({metrics.get("error_rate")}%) is elevated'
        })
    
    return render(request, 'admin_panel/metrics_dashboard.html', {
        'metrics': metrics,
        'alerts': alerts,
        'last_updated': timezone.now()
    })


@staff_member_required
@require_http_methods(["GET"])
def billing_admin(request):
    """Billing admin dashboard."""
    client = get_backend_client(request)
    
    # Get filter params
    date_range = request.GET.get('range', '30')
    sort_by = request.GET.get('sort', 'spend_desc')
    
    # Fetch billing summary from backend
    try:
        response = client.get(f'/api/billing/admin/reserve/summary/?range={date_range}&sort={sort_by}')
        summary = response.get('summary', {}) if response else {}
        accounts = response.get('accounts', []) if response else []
    except Exception as e:
        messages.warning(request, 'Unable to fetch billing data.')
        summary = {}
        accounts = []
    
    return render(request, 'admin_panel/billing_admin.html', {
        'summary': summary,
        'accounts': accounts
    })


@staff_member_required
@require_http_methods(["GET", "POST"])
def passkeys(request):
    """Manage invite passkeys."""
    client = get_backend_client(request)
    
    if request.method == "POST":
        # Create new passkey
        expires_days = request.POST.get('expires_days', '7')
        notes = request.POST.get('notes', '')
        
        try:
            response = client.post('/api/admin/passkeys/', {
                'expires_days': int(expires_days),
                'notes': notes
            })
            
            raw_key = response.get('raw_key')
            if raw_key:
                messages.success(
                    request,
                    f'Passkey created successfully! Key: {raw_key} (save this now, it will not be shown again)'
                )
            else:
                messages.success(request, 'Passkey created successfully!')
        except Exception as e:
            messages.error(request, f'Error creating passkey: {str(e)}')
        
        return redirect('admin_panel:passkeys')
    
    # Fetch passkey list
    try:
        response = client.get('/api/admin/passkeys/list/')
        passkeys = response.get('results', [])
    except Exception as e:
        messages.warning(request, 'Unable to fetch passkeys.')
        passkeys = []
    
    return render(request, 'admin_panel/passkeys.html', {
        'passkeys': passkeys
    })


@staff_member_required
@require_http_methods(["GET"])
def users(request):
    """Manage users."""
    client = get_backend_client(request)
    
    try:
        response = client.get('/api/admin/users/')
        users_list = response.get('results', [])
    except Exception:
        messages.warning(request, 'Unable to fetch users.')
        users_list = []
    
    return render(request, 'admin_panel/users.html', {
        'users': users_list
    })

