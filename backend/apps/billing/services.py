"""
Billing services for reserve management, cost computation, and ledger operations.
Business logic layer - called by APIs and DAG workflows.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.billing.models import (
    ReserveAccount, ReserveLedgerEntry, UsageEvent, 
    RateCardVersion, RateLineItem, BillingProfile, BillingAuditLog
)
from apps.observability.services import emit_event
import logging

logger = logging.getLogger(__name__)


@transaction.atomic
def credit_reserve(tenant, amount_cents, entry_type='topup', stripe_event_id=None, notes=''):
    """
    Credit reserve account and create ledger entry.
    Thread-safe with database-level locking.
    
    Args:
        tenant: Tenant instance
        amount_cents: Amount to credit (positive integer)
        entry_type: Type of entry (topup, auto_topup, refund, adjustment)
        stripe_event_id: Related Stripe event ID if applicable
        notes: Description or notes
    
    Returns:
        ReserveLedgerEntry instance
    """
    if amount_cents <= 0:
        raise ValueError('Credit amount must be positive')
    
    # Lock reserve account row for update
    account = ReserveAccount.objects.select_for_update().get(tenant=tenant)
    
    # Update balance
    old_balance = account.balance_cents
    account.balance_cents += amount_cents
    account.save()
    
    # Create ledger entry
    entry = ReserveLedgerEntry.objects.create(
        tenant=tenant,
        entry_type=entry_type,
        amount_cents=amount_cents,
        balance_after_cents=account.balance_cents,
        related_stripe_event_id=stripe_event_id,
        notes=notes,
    )
    
    emit_event(
        event_type='billing.reserve_credited',
        tenant_id=tenant.id,
        details={
            'amount_cents': amount_cents,
            'old_balance': old_balance,
            'new_balance': account.balance_cents,
            'entry_type': entry_type,
            'ledger_entry_id': entry.id,
        }
    )
    
    logger.info(f'Credited {amount_cents} cents to tenant {tenant.id} reserve. '
                f'Balance: {old_balance} -> {account.balance_cents}')
    
    return entry


@transaction.atomic
def deduct_reserve(tenant, amount_cents, job_run_id=None, usage_event_id=None, notes=''):
    """
    Deduct from reserve account and create ledger entry.
    Enforces balance policy.
    
    Args:
        tenant: Tenant instance
        amount_cents: Amount to deduct (positive integer)
        job_run_id: Related job run ID
        usage_event_id: Related usage event ID
        notes: Description or notes
    
    Returns:
        ReserveLedgerEntry instance
    
    Raises:
        ValueError if insufficient balance and policy is BLOCK
    """
    if amount_cents <= 0:
        raise ValueError('Deduction amount must be positive')
    
    # Lock reserve account row for update
    account = ReserveAccount.objects.select_for_update().get(tenant=tenant)
    
    # Check policy
    if account.low_balance_policy == 'block' and account.balance_cents < amount_cents:
        raise ValueError(f'Insufficient balance. Required: {amount_cents}, Available: {account.balance_cents}')
    
    # Update balance (can go negative for warn/limited policies)
    old_balance = account.balance_cents
    account.balance_cents -= amount_cents
    account.save()
    
    # Create ledger entry (negative amount)
    entry = ReserveLedgerEntry.objects.create(
        tenant=tenant,
        entry_type='usage',
        amount_cents=-amount_cents,
        balance_after_cents=account.balance_cents,
        related_job_id=job_run_id,
        related_usage_event_id=usage_event_id,
        notes=notes,
    )
    
    emit_event(
        event_type='billing.reserve_deducted',
        tenant_id=tenant.id,
        details={
            'amount_cents': amount_cents,
            'old_balance': old_balance,
            'new_balance': account.balance_cents,
            'job_run_id': job_run_id,
            'ledger_entry_id': entry.id,
        }
    )
    
    logger.info(f'Deducted {amount_cents} cents from tenant {tenant.id} reserve. '
                f'Balance: {old_balance} -> {account.balance_cents}')
    
    # Check if low balance threshold reached
    if account.is_low_balance():
        emit_event(
            event_type='billing.low_balance_warning',
            tenant_id=tenant.id,
            details={
                'current_balance': account.balance_cents,
                'threshold': account.low_balance_threshold_cents,
                'policy': account.low_balance_policy,
            }
        )
        logger.warning(f'Low balance warning for tenant {tenant.id}: {account.balance_cents} cents')
    
    return entry


def compute_llm_cost(usage_event, rate_version):
    """
    Compute cost for an LLM usage event using the given rate version.
    
    Args:
        usage_event: UsageEvent instance with token counts
        rate_version: RateCardVersion to use for pricing
    
    Returns:
        int: cost in cents
    """
    total_cost_cents = 0
    
    # Compute prompt tokens cost
    if usage_event.tokens_in:
        prompt_rate = RateLineItem.objects.filter(
            version=rate_version,
            usage_type='prompt_tokens',
            provider=usage_event.provider,
            model=usage_event.model,
        ).first()
        
        if prompt_rate:
            units = usage_event.tokens_in / prompt_rate.unit_size
            cost = float(prompt_rate.price_per_unit_cents) * units
            total_cost_cents += int(cost)
    
    # Compute completion tokens cost
    if usage_event.tokens_out:
        completion_rate = RateLineItem.objects.filter(
            version=rate_version,
            usage_type='completion_tokens',
            provider=usage_event.provider,
            model=usage_event.model,
        ).first()
        
        if completion_rate:
            units = usage_event.tokens_out / completion_rate.unit_size
            cost = float(completion_rate.price_per_unit_cents) * units
            total_cost_cents += int(cost)
    
    return total_cost_cents


def compute_non_llm_cost(usage_event, rate_version):
    """
    Compute cost for non-LLM usage (storage, embeddings, API calls, etc.).
    
    Args:
        usage_event: UsageEvent instance with units_consumed and usage_type
        rate_version: RateCardVersion to use for pricing
    
    Returns:
        int: cost in cents
    """
    if not usage_event.units_consumed or not usage_event.usage_type:
        return 0
    
    rate = RateLineItem.objects.filter(
        version=rate_version,
        usage_type=usage_event.usage_type,
    ).first()
    
    if not rate:
        return 0
    
    units = float(usage_event.units_consumed) / rate.unit_size
    cost = float(rate.price_per_unit_cents) * units
    
    return int(cost)


def get_active_rate_version(tenant):
    """
    Get the active rate card version for a tenant based on plan tier.
    
    Args:
        tenant: Tenant instance
    
    Returns:
        RateCardVersion instance or None
    """
    try:
        billing_profile = BillingProfile.objects.get(tenant=tenant)
        plan_tier = billing_profile.plan_tier
    except BillingProfile.DoesNotExist:
        plan_tier = 'free'
    
    # Find active rate version for this tier
    now = timezone.now()
    rate_version = RateCardVersion.objects.filter(
        rate_card__plan_tier=plan_tier,
        rate_card__is_active=True,
        effective_from__lte=now,
    ).filter(
        models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=now)
    ).order_by('-version').first()
    
    return rate_version


def compute_and_persist_cost(usage_event):
    """
    Compute cost for a usage event and persist to the event record.
    
    Args:
        usage_event: UsageEvent instance
    
    Returns:
        int: computed cost in cents
    """
    if usage_event.cost_computed:
        return usage_event.cost_cents
    
    # Get active rate version
    rate_version = get_active_rate_version(usage_event.tenant)
    
    if not rate_version:
        logger.warning(f'No active rate version found for tenant {usage_event.tenant.id}')
        usage_event.cost_cents = 0
        usage_event.cost_computed = True
        usage_event.save()
        return 0
    
    # Compute cost based on usage type
    if usage_event.provider and usage_event.model:
        cost_cents = compute_llm_cost(usage_event, rate_version)
    elif usage_event.usage_type:
        cost_cents = compute_non_llm_cost(usage_event, rate_version)
    else:
        cost_cents = 0
    
    # Persist cost
    usage_event.cost_cents = cost_cents
    usage_event.cost_computed = True
    usage_event.rate_version_used = rate_version
    usage_event.save()
    
    emit_event(
        event_type='billing.cost_computed',
        tenant_id=usage_event.tenant.id,
        details={
            'usage_event_id': usage_event.id,
            'cost_cents': cost_cents,
            'rate_version_id': rate_version.id,
            'job_run_id': usage_event.job_run_id,
        }
    )
    
    return cost_cents


def estimate_job_cost(tenant, workflow_name, estimated_tool_calls=None):
    """
    Best-effort cost estimation for a job before execution.
    Uses historical averages or provided estimates.
    
    Args:
        tenant: Tenant instance
        workflow_name: Name of workflow/DAG
        estimated_tool_calls: Optional dict of {tool_name: count}
    
    Returns:
        dict with estimated_cost_cents and details
    """
    # TODO: Implement historical average lookup
    # For MVP, return placeholder
    return {
        'estimated_cost_cents': 0,
        'confidence': 'low',
        'note': 'Historical cost estimation not yet implemented',
    }


@transaction.atomic
def manual_adjust_reserve(tenant, amount_cents, reason, performed_by):
    """
    Admin function to manually adjust reserve balance.
    Creates audit log and ledger entry.
    
    Args:
        tenant: Tenant instance
        amount_cents: Amount to adjust (positive = credit, negative = debit)
        reason: Required justification
        performed_by: User performing the adjustment
    
    Returns:
        ReserveLedgerEntry instance
    """
    if not reason or len(reason.strip()) < 10:
        raise ValueError('Reason must be at least 10 characters')
    
    # Perform adjustment
    if amount_cents > 0:
        entry = credit_reserve(
            tenant=tenant,
            amount_cents=amount_cents,
            entry_type='adjustment',
            notes=f'Manual credit by {performed_by.username}: {reason}'
        )
    else:
        entry = deduct_reserve(
            tenant=tenant,
            amount_cents=abs(amount_cents),
            notes=f'Manual debit by {performed_by.username}: {reason}'
        )
    
    # Create audit log
    audit_log = BillingAuditLog.objects.create(
        action='adjust_reserve',
        tenant=tenant,
        performed_by=performed_by,
        reason=reason,
        details={
            'amount_cents': amount_cents,
            'ledger_entry_id': entry.id,
        },
        affected_ledger_entry_id=entry.id,
    )
    
    emit_event(
        event_type='billing.manual_adjustment',
        tenant_id=tenant.id,
        details={
            'amount_cents': amount_cents,
            'performed_by': performed_by.username,
            'audit_log_id': audit_log.id,
        }
    )
    
    logger.warning(f'Manual reserve adjustment for tenant {tenant.id}: {amount_cents} cents by {performed_by.username}')
    
    return entry
