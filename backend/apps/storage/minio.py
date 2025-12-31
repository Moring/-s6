"""
MinIO storage adapter (stub for MVP).
"""
from django.conf import settings
from typing import Optional


class MinIOClient:
    """
    MinIO client adapter.
    
    For MVP, this is a stub. In production, implement:
    - boto3/minio-py integration
    - Presigned URL generation
    - Multipart upload
    - Bucket lifecycle management
    """
    
    def __init__(self):
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.bucket = settings.MINIO_BUCKET
        self.secure = settings.MINIO_SECURE
    
    def upload_file(self, object_key: str, file_data: bytes, content_type: str = 'application/octet-stream') -> str:
        """
        Upload a file to MinIO.
        
        Args:
            object_key: Object key/path
            file_data: File bytes
            content_type: MIME type
        
        Returns:
            object_key: The key of uploaded object
        """
        # TODO: Implement actual MinIO upload
        # For MVP, just return the key
        return object_key
    
    def download_file(self, object_key: str) -> Optional[bytes]:
        """
        Download a file from MinIO.
        
        Args:
            object_key: Object key/path
        
        Returns:
            file_data: File bytes or None if not found
        """
        # TODO: Implement actual MinIO download
        return None
    
    def get_presigned_url(self, object_key: str, expires_in: int = 3600) -> str:
        """
        Get presigned URL for object access.
        
        Args:
            object_key: Object key/path
            expires_in: URL expiration in seconds
        
        Returns:
            url: Presigned URL
        """
        # TODO: Implement presigned URL generation
        return f"https://{self.endpoint}/{self.bucket}/{object_key}"
    
    def delete_file(self, object_key: str) -> bool:
        """
        Delete a file from MinIO.
        
        Args:
            object_key: Object key/path
        
        Returns:
            success: True if deleted
        """
        # TODO: Implement actual MinIO delete
        return True


def get_minio_client() -> MinIOClient:
    """Get configured MinIO client."""
    return MinIOClient()
