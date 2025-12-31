from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class WorkLog(models.Model):
    """User work log entry."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    content = models.TextField()
    source = models.CharField(max_length=50, default='manual')  # manual, email, slack, etc
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', '-date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"WorkLog {self.date} ({self.id})"


class Attachment(models.Model):
    """Attachment linked to a work log."""
    worklog = models.ForeignKey(WorkLog, on_delete=models.CASCADE, related_name='attachments')
    kind = models.CharField(max_length=50)  # image, document, code, etc
    object_key = models.CharField(max_length=500)  # MinIO object key
    filename = models.CharField(max_length=255)
    size_bytes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Attachment {self.filename} ({self.id})"
