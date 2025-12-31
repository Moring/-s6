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
        # Call backend status bar API
        status_data = client.get('/api/status/bar/')
        
        if status_data:
            balance_dollars = status_data.get('reserve_balance_dollars', 0)
            tokens_in = status_data.get('tokens_in', 0)
            tokens_out = status_data.get('tokens_out', 0)
            is_low = status_data.get('is_low_balance', False)
            updated_at = status_data.get('updated_at', '')
            
            # Format balance
            if is_low and balance_dollars <= 0:
                balance_display = f'<span class="text-danger">${balance_dollars:.2f}</span>'
            elif is_low:
                balance_display = f'<span class="text-warning">${balance_dollars:.2f}</span>'
            else:
                balance_display = f'${balance_dollars:.2f}'
            
            # Format tokens
            total_tokens = tokens_in + tokens_out
            if total_tokens > 1000000:
                tokens_display = f'{total_tokens/1000000:.1f}M'
            elif total_tokens > 1000:
                tokens_display = f'{total_tokens/1000:.0f}K'
            else:
                tokens_display = str(total_tokens)
            
            # Format time (show only minutes:seconds ago)
            from datetime import datetime, timezone
            try:
                updated_dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                delta = (now - updated_dt).total_seconds()
                if delta < 60:
                    time_display = 'now'
                elif delta < 3600:
                    time_display = f'{int(delta/60)}m ago'
                else:
                    time_display = f'{int(delta/3600)}h ago'
            except:
                time_display = 'now'
        else:
            balance_display = "—"
            tokens_display = "—"
            time_display = "—"
            
    except Exception as e:
        balance_display = "—"
        tokens_display = "—"
        time_display = "offline"
    
    html = f'''
    <div class="d-flex align-items-center gap-3 px-3">
        <div class="text-center">
            <span class="text-muted fs-12 d-block">Reserve</span>
            <span class="fw-semibold">{balance_display}</span>
        </div>
        <div class="vr"></div>
        <div class="text-center">
            <span class="text-muted fs-12 d-block">Tokens</span>
            <span class="fw-semibold text-dark">{tokens_display}</span>
        </div>
        <div class="text-muted fs-11">
            <i class="ti ti-clock me-1"></i><span>{time_display}</span>
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
