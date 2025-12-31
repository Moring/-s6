from django.db import models
from django.contrib.auth.models import User


class Tenant(models.Model):
    """
    Tenant model for multi-tenancy.
    One tenant per user (1:1 mapping for MVP, supports multi-user via membership).
    """
    name = models.CharField(max_length=200)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='tenant')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Settings
    plan = models.CharField(max_length=50, default='free', help_text="Subscription plan")
    settings = models.JSONField(default=dict, blank=True, help_text="Tenant-specific settings")

    class Meta:
        db_table = 'tenants_tenant'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} (owner: {self.owner.username})"


class TenantMembership(models.Model):
    """
    Multi-user tenant membership with roles.
    Allows multiple users to belong to a tenant with specific roles.
    """
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('read_only', 'Read Only'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tenant_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    is_active = models.BooleanField(default=True)
    
    # Metadata
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='invited_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tenants_membership'
        unique_together = [['tenant', 'user']]
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.tenant.name} ({self.role})"
