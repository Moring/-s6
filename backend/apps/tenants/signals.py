"""
Tenant signals - auto-create tenant on user creation.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Tenant


@receiver(post_save, sender=User)
def create_tenant_for_new_user(sender, instance, created, **kwargs):
    """Automatically create a tenant when a new user is created."""
    if created and not instance.is_superuser:
        # Check if tenant already exists
        if not hasattr(instance, 'tenant'):
            Tenant.objects.create(
                owner=instance,
                name=f"{instance.username}'s workspace"
            )
