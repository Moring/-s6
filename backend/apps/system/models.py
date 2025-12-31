"""
System metrics models for executive dashboard.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from apps.tenants.models import Tenant


class MetricsSnapshot(models.Model):
    """
    Time-bucketed metric aggregates for dashboard display.
    Precomputed periodically to avoid expensive live queries.
    """
    BUCKET_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    # Temporal
    bucket_type = models.CharField(max_length=10, choices=BUCKET_CHOICES, default='daily')
    bucket_date = models.DateField(db_index=True)
    computed_at = models.DateTimeField(auto_now=True)
    
    # Scope
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True,
                               help_text="Null for global/all-tenants metrics")
    environment = models.CharField(max_length=20, default='production', db_index=True)
    
    # Revenue Metrics
    mrr = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                             help_text="Monthly Recurring Revenue")
    arr = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                             help_text="Annual Recurring Revenue (MRR * 12)")
    
    # Growth Metrics
    nrr = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                             help_text="Net Revenue Retention %")
    grr = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                             help_text="Gross Revenue Retention %")
    
    # Customer Metrics
    total_customers = models.IntegerField(default=0)
    new_customers = models.IntegerField(default=0)
    churned_customers = models.IntegerField(default=0)
    reactivated_customers = models.IntegerField(default=0)
    
    # Churn Rates
    customer_churn_rate = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    revenue_churn_rate = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # ARPA (Average Revenue Per Account)
    arpa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Activation & Conversion
    signups_total = models.IntegerField(default=0)
    activated_users = models.IntegerField(default=0, help_text="Users who completed key actions")
    trial_started = models.IntegerField(default=0)
    trial_converted = models.IntegerField(default=0)
    
    # Engagement
    dau = models.IntegerField(default=0, help_text="Daily Active Users")
    wau = models.IntegerField(default=0, help_text="Weekly Active Users")
    mau = models.IntegerField(default=0, help_text="Monthly Active Users")
    
    # Activation breakdown
    users_uploaded_file = models.IntegerField(default=0)
    users_created_worklog = models.IntegerField(default=0)
    users_generated_report = models.IntegerField(default=0)
    
    # Stripe/Payment (when available)
    stripe_active_subscriptions = models.IntegerField(null=True, blank=True)
    stripe_past_due = models.IntegerField(null=True, blank=True)
    stripe_canceled = models.IntegerField(null=True, blank=True)
    stripe_failed_payments = models.IntegerField(null=True, blank=True)
    
    # Operations
    api_requests_total = models.IntegerField(default=0)
    api_errors_total = models.IntegerField(default=0)
    api_avg_latency_ms = models.IntegerField(null=True, blank=True)
    
    # Jobs & AI
    jobs_total = models.IntegerField(default=0)
    jobs_succeeded = models.IntegerField(default=0)
    jobs_failed = models.IntegerField(default=0)
    jobs_avg_duration_sec = models.IntegerField(null=True, blank=True)
    
    # AI/Compute
    ai_tokens_used = models.BigIntegerField(default=0)
    ai_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    
    # Financial (manual inputs)
    cash_burn_monthly = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    runway_months = models.IntegerField(null=True, blank=True)
    outstanding_invoices_count = models.IntegerField(null=True, blank=True)
    outstanding_invoices_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    class Meta:
        db_table = 'system_metrics_snapshot'
        ordering = ['-bucket_date', '-computed_at']
        unique_together = [['bucket_type', 'bucket_date', 'tenant', 'environment']]
        indexes = [
            models.Index(fields=['-bucket_date', 'tenant']),
            models.Index(fields=['bucket_type', 'environment']),
        ]
    
    def __str__(self):
        tenant_str = self.tenant.name if self.tenant else 'Global'
        return f"{self.bucket_type.title()} {self.bucket_date} - {tenant_str}"


class MetricsConfig(models.Model):
    """
    Configuration for metrics thresholds and manual inputs.
    """
    # Alert Thresholds
    churn_spike_threshold_pct = models.DecimalField(max_digits=5, decimal_places=2, default=20.0,
                                                     help_text="Alert if churn increases by this %")
    payment_failure_threshold = models.IntegerField(default=5,
                                                    help_text="Alert if failures exceed this count")
    error_rate_threshold_pct = models.DecimalField(max_digits=5, decimal_places=2, default=5.0,
                                                   help_text="Alert if error rate exceeds this %")
    job_failure_threshold_pct = models.DecimalField(max_digits=5, decimal_places=2, default=10.0,
                                                    help_text="Alert if job failure rate exceeds this %")
    
    # Manual Financial Inputs
    monthly_burn_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                           help_text="Monthly cash burn (manual input)")
    runway_months = models.IntegerField(null=True, blank=True,
                                       help_text="Months of runway (manual input)")
    
    # Toggles
    enable_stripe_metrics = models.BooleanField(default=False)
    enable_ai_cost_tracking = models.BooleanField(default=True)
    enable_cohort_analysis = models.BooleanField(default=True)
    
    # Metadata
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'system_metrics_config'
    
    def __str__(self):
        return f"Metrics Config (updated {self.updated_at:%Y-%m-%d})"
    
    @classmethod
    def get_config(cls):
        """Get or create singleton config."""
        config, _ = cls.objects.get_or_create(id=1)
        return config


class CohortRetention(models.Model):
    """
    Cohort retention analysis for user engagement.
    """
    cohort_month = models.DateField(help_text="First day of signup month")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    
    cohort_size = models.IntegerField(default=0, help_text="Users in this cohort")
    
    # Retention at different intervals
    week_1_retained = models.IntegerField(default=0)
    week_4_retained = models.IntegerField(default=0)
    week_12_retained = models.IntegerField(default=0)
    
    computed_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'system_cohort_retention'
        unique_together = [['cohort_month', 'tenant']]
        ordering = ['-cohort_month']
    
    def __str__(self):
        tenant_str = self.tenant.name if self.tenant else 'Global'
        return f"Cohort {self.cohort_month:%Y-%m} - {tenant_str}"
    
    @property
    def week_1_retention_pct(self):
        if self.cohort_size == 0:
            return 0
        return round((self.week_1_retained / self.cohort_size) * 100, 2)
    
    @property
    def week_4_retention_pct(self):
        if self.cohort_size == 0:
            return 0
        return round((self.week_4_retained / self.cohort_size) * 100, 2)
    
    @property
    def week_12_retention_pct(self):
        if self.cohort_size == 0:
            return 0
        return round((self.week_12_retained / self.cohort_size) * 100, 2)


class ActivationEvent(models.Model):
    """
    Track key activation events for users.
    """
    EVENT_TYPES = [
        ('file_upload', 'File Upload'),
        ('worklog_create', 'Worklog Created'),
        ('report_generate', 'Report Generated'),
        ('skill_compute', 'Skills Computed'),
        ('login', 'Login'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activation_events')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Additional context
    details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'system_activation_event'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['tenant', 'event_type', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.event_type} @ {self.timestamp:%Y-%m-%d %H:%M}"


# Privacy control models for Phase 4
class PrivacyConsent(models.Model):
    """
    User privacy consent settings.
    Controls how user data can be used for AI processing and other purposes.
    """
    
    CONSENT_TYPES = [
        ('ai_context', 'Use data as AI context'),
        ('analytics', 'Usage analytics'),
        ('product_improvements', 'Product improvements'),
        ('marketing', 'Marketing communications'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='privacy_consents')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='privacy_consents')
    consent_type = models.CharField(max_length=50, choices=CONSENT_TYPES)
    granted = models.BooleanField(default=False)
    granted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'system_privacy_consent'
        unique_together = [('user', 'tenant', 'consent_type')]
        indexes = [
            models.Index(fields=['user', 'tenant', 'consent_type']),
            models.Index(fields=['tenant', 'consent_type', 'granted']),
        ]
    
    def __str__(self):
        status = "granted" if self.granted else "revoked"
        return f"{self.user.username} - {self.consent_type}: {status}"
    
    def grant(self):
        """Grant consent."""
        self.granted = True
        self.granted_at = timezone.now()
        self.revoked_at = None
        self.save()
    
    def revoke(self):
        """Revoke consent."""
        self.granted = False
        self.revoked_at = timezone.now()
        self.save()


class DocumentPrivacySettings(models.Model):
    """
    Per-document privacy settings.
    Controls whether specific documents can be used as AI context.
    """
    
    artifact = models.OneToOneField(
        'artifacts.Artifact',
        on_delete=models.CASCADE,
        related_name='privacy_settings'
    )
    allow_ai_context = models.BooleanField(
        default=True,
        help_text='Allow this document to be used as AI context'
    )
    allow_indexing = models.BooleanField(
        default=True,
        help_text='Allow this document to be indexed for search'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='document_privacy_updates'
    )
    
    class Meta:
        db_table = 'system_document_privacy'
        verbose_name = 'Document Privacy Setting'
        verbose_name_plural = 'Document Privacy Settings'
    
    def __str__(self):
        return f"Privacy: {self.artifact.filename} - AI: {self.allow_ai_context}"


class EntryPrivacySettings(models.Model):
    """
    Per-entry privacy settings for worklog entries.
    Controls whether specific entries can be used as AI context.
    """
    
    worklog_entry = models.OneToOneField(
        'worklog.WorkLog',
        on_delete=models.CASCADE,
        related_name='privacy_settings'
    )
    allow_ai_context = models.BooleanField(
        default=True,
        help_text='Allow this entry to be used as AI context'
    )
    exclude_from_exports = models.BooleanField(
        default=False,
        help_text='Exclude from data exports'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='entry_privacy_updates'
    )
    
    class Meta:
        db_table = 'system_entry_privacy'
        verbose_name = 'Entry Privacy Setting'
        verbose_name_plural = 'Entry Privacy Settings'
    
    def __str__(self):
        return f"Privacy: Entry {self.worklog_entry.id} - AI: {self.allow_ai_context}"
