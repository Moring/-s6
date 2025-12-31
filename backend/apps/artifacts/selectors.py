"""
Artifact selectors - query logic.
"""
from apps.tenants.models import Tenant
from .models import Artifact


def list_artifacts_for_tenant(tenant: Tenant):
    """List all artifacts for a tenant."""
    return Artifact.objects.filter(tenant=tenant).order_by('-created_at')
