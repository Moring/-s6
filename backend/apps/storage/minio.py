"""
MinIO storage adapter.
"""
from django.conf import settings
from typing import Optional
from minio import Minio
from minio.error import S3Error
import io


class MinIOClient:
    """MinIO client adapter using minio library."""
    
    def __init__(self):
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.bucket_name = settings.MINIO_BUCKET
        self.secure = settings.MINIO_SECURE
        
        # Initialize minio client
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        # Ensure bucket exists
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            print(f"Error ensuring bucket: {e}")
    
    def put_object(self, bucket_name: str, object_name: str, data, length: int, content_type: str = 'application/octet-stream'):
        """Upload object to MinIO."""
        return self.client.put_object(
            bucket_name,
            object_name,
            data,
            length,
            content_type=content_type
        )
    
    def get_object(self, bucket_name: str, object_name: str):
        """Get object from MinIO."""
        return self.client.get_object(bucket_name, object_name)
    
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
        data_stream = io.BytesIO(file_data)
        self.client.put_object(
            self.bucket_name,
            object_key,
            data_stream,
            len(file_data),
            content_type=content_type
        )
        return object_key
    
    def download_file(self, object_key: str) -> Optional[bytes]:
        """
        Download a file from MinIO.
        
        Args:
            object_key: Object key/path
        
        Returns:
            file_data: File bytes or None if not found
        """
        try:
            response = self.client.get_object(self.bucket_name, object_key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error:
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
        from datetime import timedelta
        return self.client.presigned_get_object(
            self.bucket_name,
            object_key,
            expires=timedelta(seconds=expires_in)
        )
    
    def delete_file(self, object_key: str) -> bool:
        """
        Delete a file from MinIO.
        
        Args:
            object_key: Object key/path
        
        Returns:
            success: True if deleted
        """
        try:
            self.client.remove_object(self.bucket_name, object_key)
            return True
        except S3Error:
            return False
    
    def health_check(self) -> bool:
        """Check if MinIO is accessible."""
        try:
            return self.client.bucket_exists(self.bucket_name)
        except Exception:
            return False


def get_minio_client() -> MinIOClient:
    """Get configured MinIO client."""
    return MinIOClient()

