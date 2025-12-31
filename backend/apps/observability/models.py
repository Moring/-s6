from django.db import models
from apps.jobs.models import Job


class Event(models.Model):
    """Event in a job's execution timeline."""
    
    LEVEL_CHOICES = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    SOURCE_CHOICES = [
        ('system', 'System'),
        ('worker', 'Worker'),
        ('workflow', 'Workflow'),
        ('agent', 'Agent'),
        ('llm', 'LLM'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='events')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='info')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='system')
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['job', 'timestamp']),
            models.Index(fields=['job', 'level']),
        ]

    def __str__(self):
        return f"{self.level.upper()} [{self.source}] {self.message[:50]}"


class Metric(models.Model):
    """System metric (optional for MVP)."""
    
    name = models.CharField(max_length=200, db_index=True)
    value = models.FloatField()
    tags = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['name', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.name}={self.value} @ {self.timestamp}"
