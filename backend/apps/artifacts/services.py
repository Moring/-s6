"""
Artifact services - file upload/download logic.
"""
from django.core.files.uploadedfile import UploadedFile
from apps.tenants.models import Tenant
from apps.storage.minio import get_minio_client
from .models import Artifact
import uuid


def upload_artifact(tenant: Tenant, file: UploadedFile) -> Artifact:
    """
    Upload a file to MinIO and create artifact record.
    """
    # Generate unique path
    file_id = str(uuid.uuid4())
    extension = file.name.split('.')[-1] if '.' in file.name else ''
    object_key = f"{tenant.id}/{file_id}.{extension}" if extension else f"{tenant.id}/{file_id}"
    
    # Upload to MinIO
    minio_client = get_minio_client()
    minio_client.put_object(
        bucket_name=minio_client.bucket_name,
        object_name=object_key,
        data=file,
        length=file.size,
        content_type=file.content_type or 'application/octet-stream'
    )
    
    # Create artifact record
    artifact = Artifact.objects.create(
        tenant=tenant,
        name=file.name,
        path=object_key,
        content_type=file.content_type or 'application/octet-stream',
        size=file.size
    )
    
    return artifact


def list_artifacts(tenant: Tenant):
    """List all artifacts for tenant."""
    return Artifact.objects.filter(tenant=tenant)


def get_artifact(tenant: Tenant, artifact_id: int) -> Artifact:
    """Get artifact by ID, scoped to tenant."""
    return Artifact.objects.get(id=artifact_id, tenant=tenant)
