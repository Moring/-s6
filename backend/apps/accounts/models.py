from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    Extended user profile for managing user-specific metadata.
    Each user has exactly one profile, linked to one tenant.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='user_profiles')
    
    # Billing
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe customer ID for billing")
    
    # Settings and metadata
    settings = models.JSONField(default=dict, blank=True, help_text="User-specific settings as JSON")
    notes = models.TextField(blank=True, help_text="Admin notes about this user")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_userprofile'
        ordering = ['-created_at']
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"Profile for {self.user.username} (Tenant: {self.tenant.name})"
