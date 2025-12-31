"""
Metrics computation services.
"""
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.db.models import Count, Avg, Sum, Q, F
from django.contrib.auth.models import User
from django.utils import timezone
from apps.system.models import MetricsSnapshot, MetricsConfig, CohortRetention, ActivationEvent
from apps.tenants.models import Tenant
from apps.accounts.models import UserProfile
from apps.jobs.models import Job
from apps.auditing.models import AuthEvent
import logging

logger = logging.getLogger(__name__)


def compute_daily_snapshot(target_date=None, tenant=None, environment='production'):
    """
    Compute daily metrics snapshot for a specific date and tenant.
    Idempotent - can be run multiple times safely.
    
    Args:
        target_date: Date to compute for (defaults to yesterday)
        tenant: Specific tenant or None for global
        environment: Environment name
    
    Returns:
        MetricsSnapshot instance
    """
    if target_date is None:
        target_date = (timezone.now() - timedelta(days=1)).date()
    
    logger.info(f"Computing daily snapshot for {target_date}, tenant={tenant}, env={environment}")
    
    # Get or create snapshot
    snapshot, created = MetricsSnapshot.objects.get_or_create(
        bucket_type='daily',
        bucket_date=target_date,
        tenant=tenant,
        environment=environment,
        defaults={}
    )
    
    # Date range for queries (timezone-aware)
    from django.utils import timezone as tz
    from django.utils import timezone as tz
    day_start = tz.make_aware(datetime.combine(target_date, datetime.min.time()))
    day_end = tz.make_aware(datetime.combine(target_date, datetime.max.time()))
    
    # Base queryset filters
    tenant_filter = Q(profile__tenant=tenant) if tenant else Q()
    
    # --- Customer Metrics ---
    
    # Total customers (active users with profiles)
    total_customers = UserProfile.objects.filter(
        user__is_active=True
    )
    if tenant:
        total_customers = total_customers.filter(tenant=tenant)
    snapshot.total_customers = total_customers.count()
    
    # New customers (signups on this day)
    new_customers = User.objects.filter(
        date_joined__date=target_date,
        is_active=True
    ).filter(tenant_filter).count()
    snapshot.new_customers = new_customers
    
    # Signups total
    signups_total = User.objects.filter(
        date_joined__date=target_date
    ).filter(tenant_filter).count()
    snapshot.signups_total = signups_total
    
    # --- Engagement Metrics ---
    
    # DAU - users who logged in on this day
    login_events = AuthEvent.objects.filter(
        event_type='login_success',
        timestamp__range=(day_start, day_end)
    )
    if tenant:
        login_events = login_events.filter(user__profile__tenant=tenant)
    
    snapshot.dau = login_events.values('user').distinct().count()
    
    # WAU - users who logged in in the past 7 days
    week_start = day_start - timedelta(days=7)
    wau_events = AuthEvent.objects.filter(
        event_type='login_success',
        timestamp__range=(week_start, day_end)
    )
    if tenant:
        wau_events = wau_events.filter(user__profile__tenant=tenant)
    
    snapshot.wau = wau_events.values('user').distinct().count()
    
    # MAU - users who logged in in the past 30 days
    month_start = day_start - timedelta(days=30)
    mau_events = AuthEvent.objects.filter(
        event_type='login_success',
        timestamp__range=(month_start, day_end)
    )
    if tenant:
        mau_events = mau_events.filter(user__profile__tenant=tenant)
    
    snapshot.mau = mau_events.values('user').distinct().count()
    
    # --- Activation Metrics ---
    
    activation_qs = ActivationEvent.objects.filter(
        timestamp__range=(day_start, day_end)
    )
    if tenant:
        activation_qs = activation_qs.filter(tenant=tenant)
    
    # Users who uploaded files
    snapshot.users_uploaded_file = activation_qs.filter(
        event_type='file_upload'
    ).values('user').distinct().count()
    
    # Users who created worklogs
    snapshot.users_created_worklog = activation_qs.filter(
        event_type='worklog_create'
    ).values('user').distinct().count()
    
    # Users who generated reports
    snapshot.users_generated_report = activation_qs.filter(
        event_type='report_generate'
    ).values('user').distinct().count()
    
    # Total activated (users who did at least one key action)
    snapshot.activated_users = activation_qs.values('user').distinct().count()
    
    # --- Jobs & Operations ---
    
    jobs_qs = Job.objects.filter(
        created_at__range=(day_start, day_end)
    )
    
    snapshot.jobs_total = jobs_qs.count()
    snapshot.jobs_succeeded = jobs_qs.filter(status='completed').count()
    snapshot.jobs_failed = jobs_qs.filter(status='failed').count()
    
    # Average job duration (if we have completed jobs with duration)
    completed_jobs = jobs_qs.filter(status='completed', finished_at__isnull=False)
    if completed_jobs.exists():
        # Calculate duration in seconds
        durations = []
        for job in completed_jobs:
            if job.finished_at and job.created_at:
                duration = (job.finished_at - job.created_at).total_seconds()
                durations.append(duration)
        
        if durations:
            snapshot.jobs_avg_duration_sec = int(sum(durations) / len(durations))
    
    # --- Revenue Metrics (Placeholder) ---
    # TODO: Integrate with Stripe when available
    snapshot.mrr = None
    snapshot.arr = None
    snapshot.nrr = None
    snapshot.grr = None
    snapshot.arpa = None
    snapshot.customer_churn_rate = None
    snapshot.revenue_churn_rate = None
    
    # --- Stripe Metrics (Placeholder) ---
    snapshot.stripe_active_subscriptions = None
    snapshot.stripe_past_due = None
    snapshot.stripe_canceled = None
    snapshot.stripe_failed_payments = None
    
    # --- Financial (From Config) ---
    config = MetricsConfig.get_config()
    snapshot.cash_burn_monthly = config.monthly_burn_rate
    snapshot.runway_months = config.runway_months
    
    snapshot.save()
    
    logger.info(f"Snapshot computed: {snapshot.id} - DAU={snapshot.dau}, MAU={snapshot.mau}")
    
    return snapshot


def compute_cohort_retention(cohort_month=None, tenant=None):
    """
    Compute cohort retention for users who signed up in a given month.
    
    Args:
        cohort_month: First day of month (defaults to last month)
        tenant: Specific tenant or None for global
    
    Returns:
        CohortRetention instance
    """
    if cohort_month is None:
        # Default to first day of last month
        today = timezone.now().date()
        cohort_month = date(today.year, today.month, 1) - timedelta(days=1)
        cohort_month = date(cohort_month.year, cohort_month.month, 1)
    
    # Ensure it's first day of month
    cohort_month = date(cohort_month.year, cohort_month.month, 1)
    
    logger.info(f"Computing cohort retention for {cohort_month}, tenant={tenant}")
    
    # Get or create cohort
    cohort, created = CohortRetention.objects.get_or_create(
        cohort_month=cohort_month,
        tenant=tenant,
        defaults={}
    )
    
    # Month boundaries
    month_start = datetime.combine(cohort_month, datetime.min.time())
    next_month = cohort_month + timedelta(days=32)
    month_end = datetime.combine(date(next_month.year, next_month.month, 1) - timedelta(days=1), datetime.max.time())
    
    # Users in cohort
    cohort_users = User.objects.filter(
        date_joined__range=(month_start, month_end),
        is_active=True
    )
    if tenant:
        cohort_users = cohort_users.filter(profile__tenant=tenant)
    
    cohort.cohort_size = cohort_users.count()
    
    if cohort.cohort_size == 0:
        cohort.save()
        return cohort
    
    user_ids = list(cohort_users.values_list('id', flat=True))
    
    # Week 1 retention (days 7-13 after signup)
    week1_start = month_end + timedelta(days=7)
    week1_end = month_end + timedelta(days=13)
    
    week1_logins = AuthEvent.objects.filter(
        event_type='login_success',
        user_id__in=user_ids,
        timestamp__range=(week1_start, week1_end)
    ).values('user').distinct().count()
    
    cohort.week_1_retained = week1_logins
    
    # Week 4 retention (days 28-34)
    week4_start = month_end + timedelta(days=28)
    week4_end = month_end + timedelta(days=34)
    
    week4_logins = AuthEvent.objects.filter(
        event_type='login_success',
        user_id__in=user_ids,
        timestamp__range=(week4_start, week4_end)
    ).values('user').distinct().count()
    
    cohort.week_4_retained = week4_logins
    
    # Week 12 retention (days 84-90)
    week12_start = month_end + timedelta(days=84)
    week12_end = month_end + timedelta(days=90)
    
    week12_logins = AuthEvent.objects.filter(
        event_type='login_success',
        user_id__in=user_ids,
        timestamp__range=(week12_start, week12_end)
    ).values('user').distinct().count()
    
    cohort.week_12_retained = week12_logins
    
    cohort.save()
    
    logger.info(f"Cohort computed: size={cohort.cohort_size}, W1={cohort.week_1_retention_pct}%")
    
    return cohort


def get_metrics_summary(start_date, end_date, tenant=None):
    """
    Get aggregated metrics summary for a date range.
    
    Returns:
        dict with summary metrics
    """
    snapshots = MetricsSnapshot.objects.filter(
        bucket_type='daily',
        bucket_date__range=(start_date, end_date),
        tenant=tenant
    )
    
    if not snapshots.exists():
        return None
    
    # Aggregate metrics
    summary = {
        'period': {
            'start': start_date,
            'end': end_date,
            'days': (end_date - start_date).days + 1
        },
        'customers': {
            'total': snapshots.latest('bucket_date').total_customers,
            'new': snapshots.aggregate(Sum('new_customers'))['new_customers__sum'] or 0,
            'churned': snapshots.aggregate(Sum('churned_customers'))['churned_customers__sum'] or 0,
        },
        'engagement': {
            'dau_avg': int(snapshots.aggregate(Avg('dau'))['dau__avg'] or 0),
            'wau_avg': int(snapshots.aggregate(Avg('wau'))['wau__avg'] or 0),
            'mau_avg': int(snapshots.aggregate(Avg('mau'))['mau__avg'] or 0),
        },
        'activation': {
            'uploaded_file': snapshots.aggregate(Sum('users_uploaded_file'))['users_uploaded_file__sum'] or 0,
            'created_worklog': snapshots.aggregate(Sum('users_created_worklog'))['users_created_worklog__sum'] or 0,
            'generated_report': snapshots.aggregate(Sum('users_generated_report'))['users_generated_report__sum'] or 0,
        },
        'jobs': {
            'total': snapshots.aggregate(Sum('jobs_total'))['jobs_total__sum'] or 0,
            'succeeded': snapshots.aggregate(Sum('jobs_succeeded'))['jobs_succeeded__sum'] or 0,
            'failed': snapshots.aggregate(Sum('jobs_failed'))['jobs_failed__sum'] or 0,
        },
        'financial': {
            'mrr': None,  # TODO: Stripe integration
            'arr': None,
            'burn': snapshots.latest('bucket_date').cash_burn_monthly,
            'runway': snapshots.latest('bucket_date').runway_months,
        }
    }
    
    # Calculate rates
    if summary['jobs']['total'] > 0:
        summary['jobs']['success_rate'] = round(
            (summary['jobs']['succeeded'] / summary['jobs']['total']) * 100, 2
        )
        summary['jobs']['failure_rate'] = round(
            (summary['jobs']['failed'] / summary['jobs']['total']) * 100, 2
        )
    else:
        summary['jobs']['success_rate'] = 0
        summary['jobs']['failure_rate'] = 0
    
    return summary


def check_alerts(snapshot):
    """
    Check if any alert thresholds are exceeded.
    
    Returns:
        list of alert dicts
    """
    config = MetricsConfig.get_config()
    alerts = []
    
    # Get previous snapshot for comparison
    prev_snapshot = MetricsSnapshot.objects.filter(
        bucket_type=snapshot.bucket_type,
        bucket_date__lt=snapshot.bucket_date,
        tenant=snapshot.tenant,
        environment=snapshot.environment
    ).first()
    
    if not prev_snapshot:
        return alerts
    
    # Job failure rate alert
    if snapshot.jobs_total > 0:
        failure_rate = (snapshot.jobs_failed / snapshot.jobs_total) * 100
        if failure_rate > float(config.job_failure_threshold_pct):
            alerts.append({
                'type': 'job_failure_spike',
                'severity': 'warning',
                'message': f"Job failure rate ({failure_rate:.1f}%) exceeds threshold ({config.job_failure_threshold_pct}%)"
            })
    
    # Churn spike alert
    if prev_snapshot.churned_customers > 0 and snapshot.churned_customers > 0:
        churn_change = ((snapshot.churned_customers - prev_snapshot.churned_customers) / prev_snapshot.churned_customers) * 100
        if churn_change > float(config.churn_spike_threshold_pct):
            alerts.append({
                'type': 'churn_spike',
                'severity': 'critical',
                'message': f"Churn increased by {churn_change:.1f}% (threshold: {config.churn_spike_threshold_pct}%)"
            })
    
    return alerts
