"""
Tenant services - business logic for tenant operations.
"""
from django.contrib.auth.models import User
from .models import Tenant


def create_tenant_for_user(user: User) -> Tenant:
    """
    Create a tenant for a user.
    Idempotent - returns existing tenant if already created.
    """
    tenant, created = Tenant.objects.get_or_create(
        owner=user,
        defaults={'name': f"{user.username}'s workspace"}
    )
    return tenant


def get_tenant_for_user(user: User) -> Tenant:
    """Get tenant for user. Raises Tenant.DoesNotExist if not found."""
    return user.tenant
