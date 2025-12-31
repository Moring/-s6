from django.db import models
from apps.tenants.models import Tenant


class Artifact(models.Model):
    """
    File artifact stored in MinIO.
    Tenant-scoped for multi-tenancy.
    """
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='artifacts')
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=500)  # MinIO object key
    content_type = models.CharField(max_length=100)
    size = models.IntegerField()  # bytes
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'artifacts_artifact'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name})"
