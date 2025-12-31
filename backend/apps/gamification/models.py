import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

User = get_user_model()


class UserStreak(models.Model):
    """Tracks user's daily logging streak."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='streak')
    current_streak = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    longest_streak = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    last_counted_date = models.DateField(null=True, blank=True)
    freezes_remaining = models.IntegerField(default=3, validators=[MinValueValidator(0)])
    freezes_used = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gamification_user_streak'
        indexes = [
            models.Index(fields=['user', '-current_streak']),
        ]

    def __str__(self):
        return f"{self.user.username} - Streak: {self.current_streak}"


class UserXP(models.Model):
    """Tracks user's XP (experience points) and level."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='xp')
    total_xp = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    level = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    daily_xp = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    daily_xp_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gamification_user_xp'
        indexes = [
            models.Index(fields=['user', '-total_xp']),
            models.Index(fields=['-total_xp']),
        ]

    def __str__(self):
        return f"{self.user.username} - Level {self.level} ({self.total_xp} XP)"


class XPEvent(models.Model):
    """Immutable ledger of XP grants."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='xp_events')
    amount = models.IntegerField(validators=[MinValueValidator(0)])
    reason = models.CharField(max_length=200)
    worklog_entry = models.ForeignKey('worklog.WorkLog', on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='xp_events')
    metadata = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=200, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'gamification_xp_event'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['worklog_entry']),
        ]

    def __str__(self):
        return f"{self.user.username} +{self.amount} XP: {self.reason}"


class BadgeDefinition(models.Model):
    """Definition of available badges/achievements."""
    CATEGORY_CHOICES = [
        ('milestone', 'Milestone'),
        ('quality', 'Quality'),
        ('consistency', 'Consistency'),
        ('special', 'Special'),
    ]
    
    code = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='milestone')
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class or emoji")
    trigger_type = models.CharField(max_length=100, help_text="Type of trigger: streak_7, first_entry, etc")
    trigger_threshold = models.IntegerField(default=0, help_text="Numeric threshold if applicable")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gamification_badge_definition'
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class UserBadge(models.Model):
    """User's earned badges."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(BadgeDefinition, on_delete=models.CASCADE, related_name='user_badges')
    awarded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    provenance = models.JSONField(default=dict, blank=True, 
                                 help_text="Job ID, trigger details, manual grant reason")
    idempotency_key = models.CharField(max_length=200, unique=True, db_index=True)

    class Meta:
        db_table = 'gamification_user_badge'
        ordering = ['-awarded_at']
        unique_together = [['user', 'badge']]
        indexes = [
            models.Index(fields=['user', '-awarded_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"


class ChallengeTemplate(models.Model):
    """Template for recurring challenges (e.g., weekly quests)."""
    code = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    goal_type = models.CharField(max_length=100, 
                                 help_text="Type: log_days, attach_evidence, write_outcomes, etc")
    goal_target = models.IntegerField(validators=[MinValueValidator(1)], 
                                     help_text="Target count to complete")
    xp_reward = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    recurrence = models.CharField(max_length=50, default='weekly', 
                                  help_text="weekly, monthly, etc")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gamification_challenge_template'
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} ({self.goal_type} >= {self.goal_target})"


class UserChallenge(models.Model):
    """User's active or completed challenge instance."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenges')
    template = models.ForeignKey(ChallengeTemplate, on_delete=models.CASCADE, 
                                related_name='user_challenges')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
    period_start = models.DateField(help_text="Start of challenge period (e.g., week start)")
    period_end = models.DateField(help_text="End of challenge period")
    current_progress = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    target_progress = models.IntegerField(validators=[MinValueValidator(1)])
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True, 
                               help_text="Tracking details: dates logged, etc")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gamification_user_challenge'
        ordering = ['-created_at']
        unique_together = [['user', 'template', 'period_start']]
        indexes = [
            models.Index(fields=['user', 'status', '-created_at']),
            models.Index(fields=['period_end', 'status']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.template.name} ({self.current_progress}/{self.target_progress})"


class RewardConfig(models.Model):
    """Configuration for reward rules (versioned)."""
    version = models.IntegerField(unique=True, db_index=True)
    config = models.JSONField(help_text="XP rules, caps, thresholds, freeze limits, etc")
    is_active = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'gamification_reward_config'
        ordering = ['-version']

    def __str__(self):
        return f"Reward Config v{self.version} {'(active)' if self.is_active else ''}"

    def save(self, *args, **kwargs):
        if self.is_active:
            # Deactivate all others when this one is activated
            RewardConfig.objects.filter(is_active=True).update(is_active=False, activated_at=None)
            self.activated_at = timezone.now()
        super().save(*args, **kwargs)


class GamificationSettings(models.Model):
    """User's gamification UI preferences."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='gamification_settings')
    quiet_mode = models.BooleanField(default=False, 
                                    help_text="Reduce/disable gamification UI elements")
    notifications_enabled = models.BooleanField(default=True)
    show_xp_details = models.BooleanField(default=True)
    show_challenges = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gamification_settings'

    def __str__(self):
        return f"{self.user.username} - Quiet: {self.quiet_mode}"
