"""
API views for status bar information.
Thin controller - delegates to services.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from apps.billing.tools import get_or_create_reserve_account
from apps.billing.models import UsageEvent
from apps.jobs.models import Job
from django.db.models import Sum, Q


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def status_bar(request):
    """
    Get status bar information for authenticated user.
    
    GET /api/status/bar/
    
    Returns:
        - reserve_balance_cents: Current prepaid balance
        - reserve_balance_dollars: Balance in dollars
        - tokens_in: Total prompt tokens used (placeholder)
        - tokens_out: Total completion tokens used (placeholder)
        - jobs_running: Number of currently running jobs (placeholder)
        - updated_at: Timestamp of this status
    """
    user = request.user
    
    # Get tenant from user profile
    try:
        profile = user.profile
        tenant = profile.tenant
    except AttributeError:
        return Response({
            'error': 'User profile not found'
        }, status=404)
    
    # Get reserve balance
    try:
        reserve = get_or_create_reserve_account(tenant)
        balance_cents = reserve.balance_cents
        balance_dollars = float(reserve.balance_cents) / 100
        is_low = reserve.is_low_balance()
    except Exception as e:
        balance_cents = 0
        balance_dollars = 0.0
        is_low = True
    
    # Token usage - aggregate from UsageEvent model
    try:
        token_stats = UsageEvent.objects.filter(
            tenant=tenant
        ).aggregate(
            total_in=Sum('tokens_in'),
            total_out=Sum('tokens_out')
        )
        tokens_in = token_stats['total_in'] or 0
        tokens_out = token_stats['total_out'] or 0
    except Exception:
        tokens_in = 0
        tokens_out = 0
    
    # Jobs running - query from Job model
    try:
        # Need to filter by tenant - Job model might not have tenant field directly
        # If tenant field doesn't exist, we'll need to filter through user
        jobs_running = Job.objects.filter(
            status='running'
        ).filter(
            Q(user__profile__tenant=tenant) | Q(user__isnull=True)
        ).count()
    except Exception:
        jobs_running = 0
    
    return Response({
        'reserve_balance_cents': balance_cents,
        'reserve_balance_dollars': balance_dollars,
        'is_low_balance': is_low,
        'tokens_in': tokens_in,
        'tokens_out': tokens_out,
        'jobs_running': jobs_running,
        'updated_at': timezone.now().isoformat(),
    })
