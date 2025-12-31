"""
Billing models for Stripe integration, reserve balances, and usage tracking.
All models are tenant-scoped for multi-tenancy isolation.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import hashlib


class BillingProfile(models.Model):
    """
    Tenant-scoped billing profile with Stripe customer reference.
    One per tenant.
    """
    PLAN_TIER_CHOICES = [
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    
    tenant = models.OneToOneField('tenants.Tenant', on_delete=models.CASCADE, related_name='billing_profile')
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, unique=True, 
                                          help_text='Stripe customer ID')
    plan_tier = models.CharField(max_length=20, choices=PLAN_TIER_CHOICES, default='free')
    
    # Subscription metadata
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    subscription_status = models.CharField(max_length=50, blank=True, null=True,
                                          help_text='active, past_due, canceled, etc.')
    subscription_current_period_start = models.DateTimeField(null=True, blank=True)
    subscription_current_period_end = models.DateTimeField(null=True, blank=True)
    
    # Portal and feature flags
    allow_portal_access = models.BooleanField(default=True)
    allow_plan_changes = models.BooleanField(default=True)
    allow_cancellation = models.BooleanField(default=True)
    
    # Auto top-up settings
    auto_topup_enabled = models.BooleanField(default=False)
    auto_topup_threshold_cents = models.IntegerField(default=1000, 
                                                     help_text='Trigger auto top-up when balance below this (cents)')
    auto_topup_amount_cents = models.IntegerField(default=5000,
                                                  help_text='Amount to add when auto top-up triggers (cents)')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'billing_profile'
        verbose_name = 'Billing Profile'
        verbose_name_plural = 'Billing Profiles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Billing for {self.tenant.name} ({self.plan_tier})'


class ReserveAccount(models.Model):
    """
    Tenant-scoped prepaid reserve balance account.
    Balance in cents for precision.
    """
    tenant = models.OneToOneField('tenants.Tenant', on_delete=models.CASCADE, related_name='reserve_account')
    balance_cents = models.BigIntegerField(default=0, help_text='Current balance in cents')
    currency = models.CharField(max_length=3, default='USD')
    
    # Enforcement policy
    POLICY_CHOICES = [
        ('block', 'Block execution when insufficient funds'),
        ('warn', 'Warn but allow execution'),
        ('limited', 'Allow limited workflows only'),
    ]
    low_balance_policy = models.CharField(max_length=20, choices=POLICY_CHOICES, default='warn')
    low_balance_threshold_cents = models.IntegerField(default=500,
                                                       help_text='Threshold for low balance warnings (cents)')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'billing_reserve_account'
        verbose_name = 'Reserve Account'
        verbose_name_plural = 'Reserve Accounts'
        ordering = ['-created_at']
    
    def __str__(self):
        balance_dollars = self.balance_cents / 100
        return f'{self.tenant.name} Reserve: '
    
    @property
    def balance_dollars(self):
        return Decimal(self.balance_cents) / 100
    
    def is_low_balance(self):
        return self.balance_cents < self.low_balance_threshold_cents
    
    def has_sufficient_balance(self, required_cents):
        if self.low_balance_policy == 'block':
            return self.balance_cents >= required_cents
        return True  # warn and limited policies allow execution


class ReserveLedgerEntry(models.Model):
    """
    Immutable ledger entries for all reserve balance changes.
    Tenant-scoped, ordered by timestamp.
    """
    ENTRY_TYPE_CHOICES = [
        ('topup', 'Top-up Payment'),
        ('usage', 'Usage Deduction'),
        ('refund', 'Refund'),
        ('adjustment', 'Manual Adjustment'),
        ('auto_topup', 'Automatic Top-up'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='reserve_ledger')
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE_CHOICES)
    amount_cents = models.BigIntegerField(help_text='Positive for credits, negative for debits')
    balance_after_cents = models.BigIntegerField(help_text='Balance snapshot after this entry')
    
    # References
    related_job_id = models.CharField(max_length=255, blank=True, null=True,
                                     help_text='JobRun ID if usage deduction')
    related_stripe_event_id = models.CharField(max_length=255, blank=True, null=True,
                                              help_text='Stripe event ID if payment-related')
    related_usage_event_id = models.BigIntegerField(blank=True, null=True,
                                                    help_text='UsageEvent ID if usage deduction')
    
    # Metadata
    notes = models.TextField(blank=True, help_text='Description or admin notes')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  help_text='User who triggered this (for adjustments)')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'billing_reserve_ledger'
        verbose_name = 'Reserve Ledger Entry'
        verbose_name_plural = 'Reserve Ledger Entries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
            models.Index(fields=['entry_type', '-created_at']),
        ]
    
    def __str__(self):
        amount_dollars = self.amount_cents / 100
        return f'{self.tenant.name}: {self.entry_type} '


class StripeEvent(models.Model):
    """
    Idempotency tracking for Stripe webhook events.
    Prevents duplicate processing.
    """
    event_id = models.CharField(max_length=255, unique=True, db_index=True,
                               help_text='Stripe event ID')
    event_type = models.CharField(max_length=100, help_text='e.g., checkout.session.completed')
    payload_hash = models.CharField(max_length=64, help_text='SHA256 hash of event payload')
    processed_at = models.DateTimeField(auto_now_add=True)
    processing_result = models.CharField(max_length=20, default='success',
                                        help_text='success, failed, skipped')
    error_message = models.TextField(blank=True)
    
    # Metadata
    tenant_id = models.IntegerField(null=True, blank=True, help_text='Resolved tenant ID')
    
    class Meta:
        db_table = 'billing_stripe_event'
        verbose_name = 'Stripe Event'
        verbose_name_plural = 'Stripe Events'
        ordering = ['-processed_at']
    
    def __str__(self):
        return f'{self.event_type} ({self.event_id[:20]}...)'
    
    @staticmethod
    def compute_payload_hash(payload_dict):
        import json
        payload_str = json.dumps(payload_dict, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()


class RateCard(models.Model):
    """
    Top-level rate card for a pricing tier.
    Multiple versions can exist with effective date ranges.
    """
    name = models.CharField(max_length=100, help_text='e.g., Standard Rates 2024')
    plan_tier = models.CharField(max_length=20, help_text='free, starter, professional, enterprise')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'billing_rate_card'
        verbose_name = 'Rate Card'
        verbose_name_plural = 'Rate Cards'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} ({self.plan_tier})'


class RateCardVersion(models.Model):
    """
    Versioned rate card with effective date range.
    Used to track pricing changes over time.
    """
    rate_card = models.ForeignKey(RateCard, on_delete=models.CASCADE, related_name='versions')
    version = models.IntegerField(help_text='Incrementing version number')
    effective_from = models.DateTimeField(help_text='When this version becomes active')
    effective_to = models.DateTimeField(null=True, blank=True, help_text='When this version expires (null = current)')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'billing_rate_card_version'
        verbose_name = 'Rate Card Version'
        verbose_name_plural = 'Rate Card Versions'
        unique_together = [['rate_card', 'version']]
        ordering = ['-version']
        indexes = [
            models.Index(fields=['effective_from', 'effective_to']),
        ]
    
    def __str__(self):
        return f'{self.rate_card.name} v{self.version}'


class RateLineItem(models.Model):
    """
    Individual pricing line items within a rate card version.
    Supports various usage types (tokens, API calls, storage, etc.).
    """
    USAGE_TYPE_CHOICES = [
        ('prompt_tokens', 'Prompt Tokens'),
        ('completion_tokens', 'Completion Tokens'),
        ('embedding_tokens', 'Embedding Tokens'),
        ('per_request', 'Per API Request'),
        ('per_mb_storage', 'Per MB Storage'),
        ('per_job', 'Per Job Execution'),
        ('per_document', 'Per Document Processed'),
    ]
    
    version = models.ForeignKey(RateCardVersion, on_delete=models.CASCADE, related_name='line_items')
    
    # Pricing dimensions
    usage_type = models.CharField(max_length=50, choices=USAGE_TYPE_CHOICES)
    provider = models.CharField(max_length=100, blank=True, help_text='e.g., openai, anthropic')
    model = models.CharField(max_length=100, blank=True, help_text='e.g., gpt-4, claude-3-opus')
    
    # Pricing
    price_per_unit_cents = models.DecimalField(max_digits=12, decimal_places=6,
                                               help_text='Price in cents per unit (e.g., per 1000 tokens)')
    unit_size = models.IntegerField(default=1, help_text='e.g., 1000 for per-1K-tokens pricing')
    
    # Metadata
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'billing_rate_line_item'
        verbose_name = 'Rate Line Item'
        verbose_name_plural = 'Rate Line Items'
        ordering = ['usage_type', 'provider', 'model']
        indexes = [
            models.Index(fields=['version', 'usage_type', 'provider', 'model']),
        ]
    
    def __str__(self):
        price_display = float(self.price_per_unit_cents)
        return f'{self.usage_type}: {self.provider}/{self.model} @ /{self.unit_size}'


class UsageEvent(models.Model):
    """
    Raw usage events captured from DAG/tool executions.
    Basis for cost computation.
    """
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='usage_events')
    
    # Execution context
    job_run_id = models.CharField(max_length=255, help_text='JobRun or DAG run identifier')
    dag_name = models.CharField(max_length=100, blank=True)
    tool_name = models.CharField(max_length=100)
    
    # LLM-specific fields
    provider = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    tokens_in = models.IntegerField(null=True, blank=True, help_text='Prompt tokens')
    tokens_out = models.IntegerField(null=True, blank=True, help_text='Completion tokens')
    
    # General metrics
    duration_ms = models.IntegerField(null=True, blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    # Non-token usage
    units_consumed = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                        help_text='For non-token usage (MB, documents, etc.)')
    usage_type = models.CharField(max_length=50, blank=True, 
                                  help_text='per_request, per_mb_storage, etc.')
    
    # Cost computation result
    cost_computed = models.BooleanField(default=False)
    cost_cents = models.BigIntegerField(null=True, blank=True, help_text='Computed cost in cents')
    rate_version_used = models.ForeignKey(RateCardVersion, on_delete=models.SET_NULL, null=True, blank=True,
                                         help_text='Rate version used for cost computation')
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'billing_usage_event'
        verbose_name = 'Usage Event'
        verbose_name_plural = 'Usage Events'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', '-timestamp']),
            models.Index(fields=['job_run_id']),
            models.Index(fields=['cost_computed', 'timestamp']),
        ]
    
    def __str__(self):
        return f'{self.tool_name} @ {self.timestamp.strftime("%Y-%m-%d %H:%M")}'


class BillingAuditLog(models.Model):
    """
    Audit log for billing-related admin actions.
    Separate from general auth audit for billing compliance.
    """
    ACTION_CHOICES = [
        ('adjust_reserve', 'Manual Reserve Adjustment'),
        ('change_rate', 'Rate Card Change'),
        ('refund', 'Issue Refund'),
        ('change_policy', 'Change Balance Policy'),
        ('override_block', 'Override Execution Block'),
    ]
    
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='billing_audit_logs')
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Details
    reason = models.TextField(help_text='Required justification for the action')
    details = models.JSONField(default=dict, help_text='Structured details of the action')
    
    # References
    affected_ledger_entry_id = models.BigIntegerField(null=True, blank=True)
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'billing_audit_log'
        verbose_name = 'Billing Audit Log'
        verbose_name_plural = 'Billing Audit Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        return f'{self.action} by {self.performed_by} @ {self.timestamp.strftime("%Y-%m-%d %H:%M")}'
