"""
Metrics computation workflow.
"""
from apps.jobs.registry import register
from apps.observability.services import log_event
from apps.orchestration.persist import persist_result
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg
import json


@register('system.compute_metrics')
def compute_metrics(ctx, payload: dict) -> dict:
    """
    Compute system metrics snapshots.
    
    Payload:
        tenant_id: Optional tenant ID (if provided, compute for that tenant only)
        bucket: 'daily' | 'weekly' | 'monthly' (default: 'daily')
        lookback_days: Number of days to look back (default: 30)
    
    Returns:
        snapshots_created: Count of snapshots created
    """
    from apps.system.models import MetricsSnapshot
    from apps.tenants.models import Tenant
    from apps.worklog.models import WorkLog
    from apps.jobs.models import Job
    from apps.invitations.models import InvitePasskey
    from apps.billing.models import ReserveAccount, ReserveLedgerEntry
    from apps.artifacts.models import Artifact
    from apps.observability.models import AuthEvent
    from django.contrib.auth.models import User
    
    tenant_id = payload.get('tenant_id')
    bucket = payload.get('bucket', 'daily')
    lookback_days = payload.get('lookback_days', 30)
    
    log_event(ctx, f"Computing {bucket} metrics snapshot", 
              tenant_id=tenant_id, lookback_days=lookback_days, source='workflow')
    
    now = timezone.now()
    lookback = now - timedelta(days=lookback_days)
    
    # Get tenants to compute for
    if tenant_id:
        try:
            tenants = [Tenant.objects.get(id=tenant_id)]
        except Tenant.DoesNotExist:
            return persist_result(ctx, {'error': 'Tenant not found'}, 'Metrics computation failed')
    else:
        tenants = Tenant.objects.all()
    
    snapshots_created = 0
    
    for tenant in tenants:
        try:
            # Compute metrics
            metrics_data = {
                'tenant_id': tenant.id,
                'bucket': bucket,
                'computed_at': now.isoformat(),
            }
            
            # User metrics
            users = User.objects.filter(profile__tenant=tenant)
            metrics_data['total_users'] = users.count()
            metrics_data['active_users_30d'] = users.filter(
                last_login__gte=lookback
            ).count()
            
            # Worklog metrics
            worklogs = WorkLog.objects.filter(user__in=users, created_at__gte=lookback)
            metrics_data['total_worklogs'] = worklogs.count()
            metrics_data['daily_worklog_avg'] = (
                worklogs.count() / max(lookback_days, 1)
            )
            
            # Job metrics
            jobs = Job.objects.filter(
                user__in=users,
                created_at__gte=lookback
            )
            metrics_data['total_jobs'] = jobs.count()
            metrics_data['successful_jobs'] = jobs.filter(status='completed').count()
            metrics_data['failed_jobs'] = jobs.filter(status='failed').count()
            
            # Compute success rate
            total = jobs.count()
            if total > 0:
                metrics_data['job_success_rate'] = (
                    jobs.filter(status='completed').count() / total * 100
                )
            else:
                metrics_data['job_success_rate'] = 0
            
            # Billing metrics
            reserves = ReserveAccount.objects.filter(tenant=tenant)
            if reserves.exists():
                metrics_data['total_reserve_balance_cents'] = sum(
                    r.balance_cents for r in reserves
                )
                metrics_data['reserve_accounts_count'] = reserves.count()
            
            # Ledger metrics (costs)
            ledger_entries = ReserveLedgerEntry.objects.filter(
                reserve__tenant=tenant,
                created_at__gte=lookback
            )
            debits = ledger_entries.filter(amount_cents__lt=0)
            if debits.exists():
                metrics_data['total_costs_cents'] = abs(
                    sum(e.amount_cents for e in debits)
                )
                metrics_data['avg_daily_cost_cents'] = (
                    metrics_data.get('total_costs_cents', 0) / max(lookback_days, 1)
                )
            else:
                metrics_data['total_costs_cents'] = 0
                metrics_data['avg_daily_cost_cents'] = 0
            
            # Signup/passkey metrics
            passkeys = InvitePasskey.objects.filter(
                created_at__gte=lookback
            )
            used_passkeys = passkeys.filter(used_at__isnull=False)
            metrics_data['passkeys_created'] = passkeys.count()
            metrics_data['passkeys_used'] = used_passkeys.count()
            
            if passkeys.count() > 0:
                metrics_data['signup_conversion_rate'] = (
                    used_passkeys.count() / passkeys.count() * 100
                )
            else:
                metrics_data['signup_conversion_rate'] = 0
            
            # Auth metrics
            auth_events = AuthEvent.objects.filter(
                created_at__gte=lookback
            )
            login_success = auth_events.filter(
                event_type='login',
                success=True
            ).count()
            login_attempts = auth_events.filter(event_type='login').count()
            
            metrics_data['login_attempts'] = login_attempts
            metrics_data['login_successes'] = login_success
            
            if login_attempts > 0:
                metrics_data['login_success_rate'] = (
                    login_success / login_attempts * 100
                )
            else:
                metrics_data['login_success_rate'] = 0
            
            # Storage metrics
            artifacts = Artifact.objects.filter(
                tenant=tenant,
                created_at__gte=lookback
            )
            metrics_data['total_artifacts'] = artifacts.count()
            metrics_data['total_storage_bytes'] = sum(
                a.size for a in artifacts
            ) if artifacts.exists() else 0
            
            # Create snapshot
            snapshot = MetricsSnapshot.objects.create(
                tenant=tenant,
                bucket=bucket,
                metrics_data=metrics_data,
                created_at=now
            )
            
            snapshots_created += 1
            log_event(ctx, f"Created metrics snapshot for tenant {tenant.id}",
                     snapshot_id=snapshot.id, source='workflow')
            
        except Exception as e:
            log_event(ctx, f"Error computing metrics for tenant {tenant.id}: {str(e)}",
                     error=str(e), level='error', source='workflow')
    
    result = {
        'snapshots_created': snapshots_created,
        'bucket': bucket,
        'lookback_days': lookback_days
    }
    
    return persist_result(ctx, result, 'Metrics snapshots computed successfully')
