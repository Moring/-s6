from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Skill(models.Model):
    """User skill extracted from work logs."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    normalized = models.CharField(max_length=200)  # Normalized form
    confidence = models.FloatField(default=0.0)  # 0.0 to 1.0
    level = models.CharField(max_length=50, null=True, blank=True)  # beginner, intermediate, expert
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-confidence', 'normalized']
        indexes = [
            models.Index(fields=['user', '-confidence']),
            models.Index(fields=['normalized']),
        ]
        unique_together = [['user', 'normalized']]

    def __str__(self):
        return f"{self.normalized} ({self.confidence:.2f})"


class SkillEvidence(models.Model):
    """Evidence linking a skill to its source."""
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='evidence')
    source_type = models.CharField(max_length=50)  # worklog, project, etc
    source_id = models.IntegerField()
    excerpt = models.TextField(blank=True)
    weight = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['skill', '-created_at']),
            models.Index(fields=['source_type', 'source_id']),
        ]

    def __str__(self):
        return f"Evidence for {self.skill.normalized} from {self.source_type}:{self.source_id}"
