import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Job(models.Model):
    """Asynchronous job execution record."""
    
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    TRIGGER_CHOICES = [
        ('api', 'API'),
        ('schedule', 'Schedule'),
        ('system', 'System'),
        ('retry', 'Retry'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=100, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued', db_index=True)
    trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default='api')
    
    payload = models.JSONField(default=dict)
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    scheduled_for = models.DateTimeField(null=True, blank=True, db_index=True)
    parent_job = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_jobs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['type', 'status']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"Job {self.type} ({self.id}) - {self.status}"


class Schedule(models.Model):
    """Scheduled job configuration."""
    
    name = models.CharField(max_length=200, unique=True)
    job_type = models.CharField(max_length=100)
    cron = models.CharField(max_length=100)  # Cron expression or @hourly, @daily, etc
    payload = models.JSONField(default=dict)
    enabled = models.BooleanField(default=True, db_index=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"Schedule {self.name} ({self.job_type})"
