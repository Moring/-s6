from django.db import models
from django.contrib.auth.models import User


class Tenant(models.Model):
    """
    Tenant model for multi-tenancy.
    One tenant per user (1:1 mapping).
    """
    name = models.CharField(max_length=200)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='tenant')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'tenants_tenant'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} (owner: {self.owner.username})"
