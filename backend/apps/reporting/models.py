from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Report(models.Model):
    """Generated report (resume, status, standup, etc)."""
    
    KIND_CHOICES = [
        ('resume', 'Resume'),
        ('status', 'Status Report'),
        ('standup', 'Standup'),
        ('summary', 'Summary'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    kind = models.CharField(max_length=50, choices=KIND_CHOICES)
    content = models.JSONField(default=dict)  # Structured content
    rendered_text = models.TextField(blank=True)  # Plain text or markdown
    rendered_html = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'kind', '-created_at']),
            models.Index(fields=['kind', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} ({self.id})"
