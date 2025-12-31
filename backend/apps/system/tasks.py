"""
Scheduled tasks for metrics computation.
"""
from huey import crontab
from huey.contrib.djhuey import db_task, db_periodic_task
from datetime import timedelta, date
from django.utils import timezone
from apps.system.services import compute_daily_snapshot, compute_cohort_retention
from apps.system.models import MetricsSnapshot
from apps.tenants.models import Tenant
from apps.observability.services import log_event
import logging

logger = logging.getLogger(__name__)


@db_periodic_task(crontab(hour='1', minute='0'))
def compute_daily_metrics():
    """
    Compute daily metrics snapshots for all tenants.
    Runs every day at 1 AM.
    """
    logger.info("Starting daily metrics computation")
    
    try:
        yesterday = (timezone.now() - timedelta(days=1)).date()
        
        # Compute global snapshot
        global_snapshot = compute_daily_snapshot(
            target_date=yesterday,
            tenant=None,
            environment='production'
        )
        
        logger.info(f"Global snapshot computed: {global_snapshot.id}")
        
        # Compute per-tenant snapshots
        tenants = Tenant.objects.filter(is_active=True)
        for tenant in tenants:
            try:
                snapshot = compute_daily_snapshot(
                    target_date=yesterday,
                    tenant=tenant,
                    environment='production'
                )
                logger.info(f"Tenant snapshot computed: {tenant.name} -> {snapshot.id}")
            except Exception as e:
                logger.error(f"Failed to compute snapshot for tenant {tenant.name}: {e}")
        
        logger.info(f"Daily metrics computed successfully for {tenants.count()} tenants")
        
    except Exception as e:
        logger.error(f"Daily metrics computation failed: {e}", exc_info=True)
        raise


@db_periodic_task(crontab(day='1', hour='2', minute='0'))
def compute_monthly_cohorts():
    """
    Compute cohort retention analysis.
    Runs on the 1st of each month at 2 AM.
    """
    logger.info("Starting cohort retention computation")
    
    try:
        # Compute for last month
        today = timezone.now().date()
        last_month = date(today.year, today.month, 1) - timedelta(days=1)
        cohort_month = date(last_month.year, last_month.month, 1)
        
        # Global cohort
        global_cohort = compute_cohort_retention(
            cohort_month=cohort_month,
            tenant=None
        )
        
        logger.info(f"Global cohort computed: {global_cohort.id}")
        
        # Per-tenant cohorts
        tenants = Tenant.objects.filter(is_active=True)
        for tenant in tenants:
            try:
                cohort = compute_cohort_retention(
                    cohort_month=cohort_month,
                    tenant=tenant
                )
                logger.info(f"Tenant cohort computed: {tenant.name} -> {cohort.id}")
            except Exception as e:
                logger.error(f"Failed to compute cohort for tenant {tenant.name}: {e}")
        
        logger.info(f"Cohort retention computed successfully for {tenants.count()} tenants")
        
    except Exception as e:
        logger.error(f"Cohort computation failed: {e}", exc_info=True)
        raise


@db_task()
def backfill_metrics(start_date, end_date, tenant_id=None):
    """
    Backfill metrics for a date range.
    Can be triggered manually.
    
    Args:
        start_date: Start date (YYYY-MM-DD string or date)
        end_date: End date (YYYY-MM-DD string or date)
        tenant_id: Optional tenant ID
    """
    logger.info(f"Starting metrics backfill: {start_date} to {end_date}")
    
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    
    tenant = None
    if tenant_id:
        tenant = Tenant.objects.get(id=tenant_id)
    
    current_date = start_date
    while current_date <= end_date:
        try:
            snapshot = compute_daily_snapshot(
                target_date=current_date,
                tenant=tenant,
                environment='production'
            )
            logger.info(f"Backfilled: {current_date} -> {snapshot.id}")
        except Exception as e:
            logger.error(f"Failed to backfill {current_date}: {e}")
        
        current_date += timedelta(days=1)
    
    logger.info("Backfill complete")
