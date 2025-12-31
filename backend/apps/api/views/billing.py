"""
Billing API views - thin controllers for reserve management and Stripe integration.
All business logic delegated to services and tools.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta

from apps.billing.models import (
    ReserveAccount, ReserveLedgerEntry, BillingProfile,
    UsageEvent, RateCard, RateCardVersion, BillingAuditLog
)
from apps.billing.tools import (
    stripe_create_checkout_session,
    stripe_create_portal_session,
    get_or_create_reserve_account,
)
from apps.billing.services import (
    credit_reserve, manual_adjust_reserve, estimate_job_cost
)
from apps.billing.webhooks import verify_webhook_signature, process_webhook_event
from apps.auditing.models import AuthEvent
from apps.tenants.models import Tenant
import logging
import json

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reserve_balance(request):
    """
    Get current reserve balance for authenticated user's tenant.
    GET /api/billing/reserve/balance/
    """
    tenant = request.user.profile.tenant
    account = get_or_create_reserve_account(tenant)
    
    # Log access
    AuthEvent.objects.create(
        event_type='billing_access',
        user=request.user,
        tenant=tenant,
        ip_address=request.META.get('REMOTE_ADDR'),
        details={'action': 'view_balance'}
    )
    
    return Response({
        'balance_cents': account.balance_cents,
        'balance_dollars': float(account.balance_dollars),
        'currency': account.currency,
        'low_balance_policy': account.low_balance_policy,
        'low_balance_threshold_cents': account.low_balance_threshold_cents,
        'is_low_balance': account.is_low_balance(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reserve_ledger(request):
    """
    Get reserve ledger entries for authenticated user's tenant.
    GET /api/billing/reserve/ledger/?limit=50&offset=0
    """
    tenant = request.user.profile.tenant
    
    limit = int(request.GET.get('limit', 50))
    offset = int(request.GET.get('offset', 0))
    
    entries = ReserveLedgerEntry.objects.filter(
        tenant=tenant
    ).order_by('-created_at')[offset:offset+limit]
    
    total_count = ReserveLedgerEntry.objects.filter(tenant=tenant).count()
    
    entries_data = [
        {
            'id': entry.id,
            'entry_type': entry.entry_type,
            'amount_cents': entry.amount_cents,
            'amount_dollars': entry.amount_cents / 100,
            'balance_after_cents': entry.balance_after_cents,
            'balance_after_dollars': entry.balance_after_cents / 100,
            'notes': entry.notes,
            'related_job_id': entry.related_job_id,
            'created_at': entry.created_at.isoformat(),
        }
        for entry in entries
    ]
    
    return Response({
        'entries': entries_data,
        'total_count': total_count,
        'limit': limit,
        'offset': offset,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_topup_session(request):
    """
    Create Stripe checkout session for reserve top-up.
    POST /api/billing/topup/session/
    Body: {"amount_cents": 5000}
    """
    tenant = request.user.profile.tenant
    amount_cents = request.data.get('amount_cents')
    
    if not amount_cents or amount_cents < 100:
        return Response(
            {'error': 'amount_cents must be at least 100 (minimum .00)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if amount_cents > 1000000:
        return Response(
            {'error': 'amount_cents cannot exceed 1000000 (0,000)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Build callback URLs
    success_url = request.build_absolute_uri('/billing/topup/success/')
    cancel_url = request.build_absolute_uri('/billing/topup/cancel/')
    
    try:
        result = stripe_create_checkout_session(
            tenant=tenant,
            amount_cents=amount_cents,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        
        # Log action
        AuthEvent.objects.create(
            event_type='billing_action',
            user=request.user,
            tenant=tenant,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={
                'action': 'create_topup_session',
                'amount_cents': amount_cents,
                'session_id': result['session_id'],
            }
        )
        
        return Response(result)
        
    except Exception as e:
        logger.error(f'Failed to create checkout session: {e}')
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_portal_session(request):
    """
    Create Stripe customer portal session.
    POST /api/billing/portal/session/
    """
    tenant = request.user.profile.tenant
    return_url = request.build_absolute_uri('/billing/')
    
    try:
        result = stripe_create_portal_session(
            tenant=tenant,
            return_url=return_url,
        )
        
        # Log action
        AuthEvent.objects.create(
            event_type='billing_action',
            user=request.user,
            tenant=tenant,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={'action': 'open_portal'}
        )
        
        return Response(result)
        
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        logger.error(f'Failed to create portal session: {e}')
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def billing_profile(request):
    """
    Get billing profile for authenticated user's tenant.
    GET /api/billing/profile/
    """
    tenant = request.user.profile.tenant
    
    try:
        profile = BillingProfile.objects.get(tenant=tenant)
    except BillingProfile.DoesNotExist:
        return Response({
            'plan_tier': 'free',
            'subscription_status': None,
            'stripe_customer_id': None,
        })
    
    return Response({
        'plan_tier': profile.plan_tier,
        'subscription_status': profile.subscription_status,
        'stripe_subscription_id': profile.stripe_subscription_id,
        'subscription_current_period_start': profile.subscription_current_period_start.isoformat() if profile.subscription_current_period_start else None,
        'subscription_current_period_end': profile.subscription_current_period_end.isoformat() if profile.subscription_current_period_end else None,
        'allow_portal_access': profile.allow_portal_access,
        'allow_plan_changes': profile.allow_plan_changes,
        'auto_topup_enabled': profile.auto_topup_enabled,
        'auto_topup_threshold_cents': profile.auto_topup_threshold_cents,
        'auto_topup_amount_cents': profile.auto_topup_amount_cents,
    })


@api_view(['POST'])
@csrf_exempt
def stripe_webhook(request):
    """
    Stripe webhook endpoint for processing payment events.
    POST /api/billing/webhook/
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
    
    if not webhook_secret:
        logger.warning('Stripe webhook secret not configured')
        # Allow for development/testing
        try:
            event_data = json.loads(payload)
        except json.JSONDecodeError:
            return HttpResponse(status=400)
    else:
        # Verify signature
        try:
            event = verify_webhook_signature(payload, sig_header, webhook_secret)
            event_data = event.to_dict() if hasattr(event, 'to_dict') else event
        except Exception as e:
            logger.error(f'Webhook signature verification failed: {e}')
            return HttpResponse(status=400)
    
    # Process event idempotently
    try:
        result = process_webhook_event(event_data)
        return HttpResponse(json.dumps(result), content_type='application/json')
    except Exception as e:
        logger.error(f'Webhook processing failed: {e}', exc_info=True)
        return HttpResponse(status=500)


# Admin endpoints

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_reserve_summary(request):
    """
    Admin: Get system-wide reserve balance summary.
    GET /api/billing/admin/reserve/summary/
    """
    accounts = ReserveAccount.objects.all()
    
    total_balance = accounts.aggregate(total=Sum('balance_cents'))['total'] or 0
    low_balance_count = accounts.filter(
        balance_cents__lt=models.F('low_balance_threshold_cents')
    ).count()
    negative_balance_count = accounts.filter(balance_cents__lt=0).count()
    
    # Log access
    AuthEvent.objects.create(
        event_type='admin_action',
        user=request.user,
        details={'action': 'view_reserve_summary'}
    )
    
    return Response({
        'total_accounts': accounts.count(),
        'total_balance_cents': total_balance,
        'total_balance_dollars': total_balance / 100,
        'low_balance_count': low_balance_count,
        'negative_balance_count': negative_balance_count,
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_usage_costs(request):
    """
    Admin: Get usage cost breakdown.
    GET /api/billing/admin/usage/costs/?start=YYYY-MM-DD&end=YYYY-MM-DD&tenant=ID
    """
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    tenant_id = request.GET.get('tenant')
    
    # Build queryset
    qs = UsageEvent.objects.filter(cost_computed=True)
    
    if start_date:
        start_dt = timezone.datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        qs = qs.filter(timestamp__gte=start_dt)
    
    if end_date:
        end_dt = timezone.datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        qs = qs.filter(timestamp__lte=end_dt)
    
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    
    # Aggregate by tenant
    tenant_costs = qs.values('tenant_id').annotate(
        total_cost=Sum('cost_cents'),
        event_count=Count('id'),
        avg_cost=Avg('cost_cents'),
    ).order_by('-total_cost')
    
    # Aggregate by tool
    tool_costs = qs.values('tool_name').annotate(
        total_cost=Sum('cost_cents'),
        event_count=Count('id'),
    ).order_by('-total_cost')[:10]
    
    # Aggregate by model
    model_costs = qs.filter(model__isnull=False).values('provider', 'model').annotate(
        total_cost=Sum('cost_cents'),
        event_count=Count('id'),
    ).order_by('-total_cost')[:10]
    
    # Log access
    AuthEvent.objects.create(
        event_type='admin_action',
        user=request.user,
        details={
            'action': 'view_usage_costs',
            'filters': {
                'start': start_date,
                'end': end_date,
                'tenant': tenant_id,
            }
        }
    )
    
    return Response({
        'tenant_costs': list(tenant_costs),
        'tool_costs': list(tool_costs),
        'model_costs': list(model_costs),
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_adjust_reserve(request):
    """
    Admin: Manually adjust reserve balance.
    POST /api/billing/admin/reserve/adjust/
    Body: {"tenant_id": 1, "amount_cents": 5000, "reason": "..."}
    """
    tenant_id = request.data.get('tenant_id')
    amount_cents = request.data.get('amount_cents')
    reason = request.data.get('reason', '')
    
    if not tenant_id or amount_cents is None:
        return Response(
            {'error': 'tenant_id and amount_cents required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        tenant = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return Response(
            {'error': 'Tenant not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        entry = manual_adjust_reserve(
            tenant=tenant,
            amount_cents=amount_cents,
            reason=reason,
            performed_by=request.user,
        )
        
        return Response({
            'status': 'success',
            'ledger_entry_id': entry.id,
            'new_balance_cents': entry.balance_after_cents,
        })
        
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f'Failed to adjust reserve: {e}')
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_export_ledger_csv(request):
    """
    Admin: Export ledger entries as CSV.
    GET /api/billing/admin/ledger/export.csv?tenant=ID&start=YYYY-MM-DD&end=YYYY-MM-DD
    """
    import csv
    from django.http import StreamingHttpResponse
    
    tenant_id = request.GET.get('tenant')
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    
    # Build queryset
    qs = ReserveLedgerEntry.objects.all()
    
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    
    if start_date:
        start_dt = timezone.datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        qs = qs.filter(created_at__gte=start_dt)
    
    if end_date:
        end_dt = timezone.datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        qs = qs.filter(created_at__lte=end_dt)
    
    qs = qs.order_by('created_at')
    
    # Log export
    AuthEvent.objects.create(
        event_type='admin_action',
        user=request.user,
        details={
            'action': 'export_ledger_csv',
            'filters': {
                'tenant': tenant_id,
                'start': start_date,
                'end': end_date,
            },
            'row_count': qs.count(),
        }
    )
    
    # Stream CSV
    def csv_generator():
        buffer = []
        writer = csv.writer(type('obj', (object,), {'write': buffer.append})())
        
        # Header
        writer.writerow([
            'Tenant ID', 'Tenant Name', 'Entry Type', 'Amount (cents)', 
            'Amount ($)', 'Balance After (cents)', 'Balance After ($)',
            'Related Job ID', 'Stripe Event ID', 'Notes', 'Created At'
        ])
        yield ''.join(buffer)
        buffer.clear()
        
        # Data rows
        for entry in qs.iterator(chunk_size=1000):
            writer.writerow([
                entry.tenant.id,
                entry.tenant.name,
                entry.entry_type,
                entry.amount_cents,
                entry.amount_cents / 100,
                entry.balance_after_cents,
                entry.balance_after_cents / 100,
                entry.related_job_id or '',
                entry.related_stripe_event_id or '',
                entry.notes,
                entry.created_at.isoformat(),
            ])
            yield ''.join(buffer)
            buffer.clear()
    
    response = StreamingHttpResponse(csv_generator(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ledger_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    return response
