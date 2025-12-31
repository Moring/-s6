"""
Admin panel views for frontend.
"""
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from apps.api_proxy.client import get_backend_client


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

