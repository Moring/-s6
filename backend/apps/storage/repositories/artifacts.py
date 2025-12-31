"""
Artifact repository for storing job artifacts.
"""
from apps.storage.minio import get_minio_client


class ArtifactRepository:
    """Repository for job artifacts and attachments."""
    
    def __init__(self):
        self.client = get_minio_client()
    
    def store_artifact(self, job_id: str, artifact_name: str, data: bytes, content_type: str = 'application/json') -> str:
        """
        Store a job artifact.
        
        Args:
            job_id: Job UUID
            artifact_name: Name of artifact
            data: Artifact data
            content_type: MIME type
        
        Returns:
            object_key: Storage key
        """
        object_key = f"jobs/{job_id}/{artifact_name}"
        return self.client.upload_file(object_key, data, content_type)
    
    def retrieve_artifact(self, job_id: str, artifact_name: str) -> bytes:
        """Retrieve a job artifact."""
        object_key = f"jobs/{job_id}/{artifact_name}"
        return self.client.download_file(object_key)
    
    def store_attachment(self, worklog_id: int, filename: str, data: bytes, content_type: str) -> str:
        """
        Store a worklog attachment.
        
        Args:
            worklog_id: WorkLog ID
            filename: Original filename
            data: File data
            content_type: MIME type
        
        Returns:
            object_key: Storage key
        """
        # Generate unique key
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        object_key = f"worklogs/{worklog_id}/{unique_id}_{filename}"
        return self.client.upload_file(object_key, data, content_type)
    
    def get_attachment_url(self, object_key: str) -> str:
        """Get presigned URL for attachment."""
        return self.client.get_presigned_url(object_key)


def get_artifact_repository() -> ArtifactRepository:
    """Get artifact repository instance."""
    return ArtifactRepository()
