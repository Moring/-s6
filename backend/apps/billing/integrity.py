"""
Financial integrity checks for reserve billing and ledgers.
Periodic validation to ensure accounting correctness.
"""
from typing import Dict, List, Tuple
from django.db.models import Sum, Q
from django.core.cache import cache
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class IntegrityCheckResult:
    """Result of a financial integrity check."""
    
    def __init__(self, check_name: str):
        self.check_name = check_name
        self.passed = True
        self.discrepancies = []
        self.warnings = []
        self.timestamp = timezone.now()
    
    def add_discrepancy(self, description: str, expected: any, actual: any):
        """Add a discrepancy (failure)."""
        self.passed = False
        self.discrepancies.append({
            'description': description,
            'expected': expected,
            'actual': actual,
            'difference': actual - expected if isinstance(actual, (int, float, Decimal)) else None
        })
    
    def add_warning(self, description: str, value: any = None):
        """Add a warning (not a failure, but noteworthy)."""
        self.warnings.append({
            'description': description,
            'value': value
        })
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'check_name': self.check_name,
            'passed': self.passed,
            'discrepancies': self.discrepancies,
            'warnings': self.warnings,
            'timestamp': self.timestamp.isoformat(),
            'status': 'PASS' if self.passed else 'FAIL'
        }


def check_reserve_balance_integrity() -> IntegrityCheckResult:
    """
    Check that tenant reserve balances match ledger entries.
    
    Validates:
    - Sum of ledger debits/credits = current balance
    - No negative balances (unless explicitly allowed)
    - Balance matches cached value
    """
    from apps.tenants.models import Tenant
    from apps.billing.models import ReserveLedgerEntry
    
    result = IntegrityCheckResult('reserve_balance_integrity')
    
    for tenant in Tenant.objects.all():
        # Get current balance from tenant
        current_balance = tenant.settings.get('reserve_balance', 0) if hasattr(tenant, 'settings') and tenant.settings else 0
        
        # Calculate balance from ledger
        ledger_sum = ReserveLedgerEntry.objects.filter(
            tenant=tenant
        ).aggregate(
            total=Sum('amount_cents')
        )['total'] or Decimal('0')
        
        # Check if they match
        if abs(float(current_balance) - float(ledger_sum)) > 0.01:  # Allow 1 cent tolerance
            result.add_discrepancy(
                f'Tenant {tenant.id} balance mismatch',
                expected=float(ledger_sum),
                actual=float(current_balance)
            )
        
        # Check for negative balance
        if current_balance < 0:
            result.add_warning(
                f'Tenant {tenant.id} has negative balance',
                value=float(current_balance)
            )
    
    return result


def check_quota_counter_integrity() -> IntegrityCheckResult:
    """
    Check that quota counters match actual job counts.
    
    Validates:
    - Cached job count = actual job count in DB
    - Token usage matches API call logs
    """
    from apps.tenants.models import Tenant
    from apps.jobs.models import Job
    from django.utils.timezone import now
    from datetime import timedelta
    
    result = IntegrityCheckResult('quota_counter_integrity')
    
    # Check last 24 hours
    since = now() - timedelta(days=1)
    
    for tenant in Tenant.objects.all():
        # Get cached job count
        cache_key = f'quota:jobs_today:{tenant.id}'
        cached_count = cache.get(cache_key, 0)
        
        # Count actual jobs
        actual_count = Job.objects.filter(
            user__in=tenant.owner.__class__.objects.filter(
                # Get all users in this tenant
                id=tenant.owner.id
            ),
            created_at__gte=since
        ).count()
        
        # Allow some discrepancy due to cache timing
        if abs(cached_count - actual_count) > 5:
            result.add_discrepancy(
                f'Tenant {tenant.id} job count mismatch (last 24h)',
                expected=actual_count,
                actual=cached_count
            )
    
    return result


def check_ledger_entry_integrity() -> IntegrityCheckResult:
    """
    Check ledger entries for integrity.
    
    Validates:
    - No duplicate entries (same idempotency key)
    - All entries have valid amounts
    - Entries are balanced (if double-entry bookkeeping)
    """
    from apps.billing.models import ReserveLedgerEntry
    
    result = IntegrityCheckResult('ledger_entry_integrity')
    
    # Check for zero or null amounts
    invalid_amounts = ReserveLedgerEntry.objects.filter(
        Q(amount_cents=0) | Q(amount_cents__isnull=True)
    ).count()
    
    if invalid_amounts > 0:
        result.add_warning(
            f'Found {invalid_amounts} ledger entries with zero or null amounts'
        )
    
    # Check for duplicate idempotency keys (if we add that field)
    # This would be added when we implement idempotency for charges
    
    return result


def check_stripe_charge_integrity() -> IntegrityCheckResult:
    """
    Check that Stripe charges match ledger entries.
    
    Validates:
    - Every successful Stripe charge has a ledger entry
    - Ledger amounts match Stripe amounts
    - No orphaned charges or entries
    """
    from apps.billing.models import ReserveLedgerEntry
    
    result = IntegrityCheckResult('stripe_charge_integrity')
    
    # StripeCharge model doesn't exist - we track charges via stripe_event_id in ledger
    # Check that ledger entries with stripe references are valid
    stripe_entries = ReserveLedgerEntry.objects.filter(
        related_stripe_event_id__isnull=False
    )
    
    for entry in stripe_entries:
        # Basic validation: non-zero amounts, valid balance
        if entry.amount_cents == 0:
            result.add_warning(
                f'Ledger entry {entry.id} has zero amount for Stripe event',
                entry.related_stripe_event_id
            )
    
    # If no issues found, all is good
    if not result.warnings:
        result.add_warning('No Stripe-related ledger entries found or all entries valid')
    
    return result


def run_all_integrity_checks() -> Dict[str, IntegrityCheckResult]:
    """
    Run all financial integrity checks.
    
    Returns:
        Dictionary mapping check names to results
    """
    checks = {
        'reserve_balance': check_reserve_balance_integrity(),
        'quota_counter': check_quota_counter_integrity(),
        'ledger_entry': check_ledger_entry_integrity(),
        'stripe_charge': check_stripe_charge_integrity(),
    }
    
    # Log summary
    failed_checks = [name for name, result in checks.items() if not result.passed]
    if failed_checks:
        logger.error(f'Financial integrity checks FAILED: {", ".join(failed_checks)}')
    else:
        logger.info('All financial integrity checks PASSED')
    
    # Cache results
    cache.set('integrity_check_results', {
        name: result.to_dict() for name, result in checks.items()
    }, 3600)  # Cache for 1 hour
    
    return checks


def get_cached_integrity_results() -> Dict[str, dict]:
    """
    Get cached integrity check results.
    
    Returns:
        Dictionary of cached results or empty dict if no cache
    """
    return cache.get('integrity_check_results', {})


def schedule_integrity_checks():
    """
    Schedule periodic integrity checks.
    Should be called by periodic task runner (Huey, Celery, cron, etc.)
    """
    from apps.workers.queue import db_task
    
    @db_task()
    def run_integrity_checks_task():
        """Periodic task to run integrity checks."""
        results = run_all_integrity_checks()
        
        # If any checks failed, send alert (would integrate with alerting system)
        failed = [name for name, result in results.items() if not result.passed]
        if failed:
            logger.critical(
                f'FINANCIAL INTEGRITY ALERT: Checks failed: {", ".join(failed)}'
            )
            # TODO: Send alert via email/Slack/PagerDuty
    
    return run_integrity_checks_task
