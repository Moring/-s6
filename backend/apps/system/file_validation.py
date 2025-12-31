"""
File upload hardening and validation.
Implements security checks for file uploads to prevent abuse.
"""
from typing import Optional, Dict, Any, Tuple
import mimetypes
import hashlib
from pathlib import Path
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
import logging

# Optional: python-magic for MIME type detection
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

logger = logging.getLogger(__name__)


# Allowed file types and extensions
ALLOWED_DOCUMENT_TYPES = {
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'text/plain': ['.txt'],
    'text/markdown': ['.md'],
    'text/csv': ['.csv'],
}

ALLOWED_IMAGE_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'image/webp': ['.webp'],
}

ALLOWED_ARCHIVE_TYPES = {
    'application/zip': ['.zip'],
    'application/x-gzip': ['.gz'],
    'application/x-tar': ['.tar'],
}

# Combine all allowed types
ALL_ALLOWED_TYPES = {
    **ALLOWED_DOCUMENT_TYPES,
    **ALLOWED_IMAGE_TYPES,
    **ALLOWED_ARCHIVE_TYPES,
}

# File size limits (in bytes)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB default
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB for images
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50 MB for documents


class FileValidationError(Exception):
    """Raised when file validation fails."""
    pass


class FileValidator:
    """
    Validates uploaded files for security and policy compliance.
    """
    
    def __init__(self, allow_documents: bool = True, allow_images: bool = True,
                 allow_archives: bool = False):
        """
        Initialize validator with allowed file categories.
        
        Args:
            allow_documents: Allow document uploads
            allow_images: Allow image uploads
            allow_archives: Allow archive uploads
        """
        self.allowed_types = {}
        
        if allow_documents:
            self.allowed_types.update(ALLOWED_DOCUMENT_TYPES)
        if allow_images:
            self.allowed_types.update(ALLOWED_IMAGE_TYPES)
        if allow_archives:
            self.allowed_types.update(ALLOWED_ARCHIVE_TYPES)
    
    def validate(self, uploaded_file: UploadedFile) -> Tuple[bool, Optional[str]]:
        """
        Validate an uploaded file.
        
        Args:
            uploaded_file: Django UploadedFile object
            
        Returns:
            (is_valid, error_message)
        """
        try:
            # 1. Check file size
            self._validate_size(uploaded_file)
            
            # 2. Check file extension
            self._validate_extension(uploaded_file.name)
            
            # 3. Check MIME type from content
            self._validate_mime_type(uploaded_file)
            
            # 4. Check for malicious content (basic)
            self._validate_content(uploaded_file)
            
            return True, None
            
        except FileValidationError as e:
            logger.warning(f"File validation failed: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Unexpected error during file validation: {e}")
            return False, "File validation failed"
    
    def _validate_size(self, uploaded_file: UploadedFile):
        """Validate file size."""
        size = uploaded_file.size
        
        # Get mime type to determine size limit
        mime_type = self._detect_mime_type(uploaded_file)
        
        if mime_type in ALLOWED_IMAGE_TYPES:
            max_size = MAX_IMAGE_SIZE
        elif mime_type in ALLOWED_DOCUMENT_TYPES:
            max_size = MAX_DOCUMENT_SIZE
        else:
            max_size = MAX_FILE_SIZE
        
        if size > max_size:
            raise FileValidationError(
                f"File size {size} bytes exceeds maximum allowed {max_size} bytes"
            )
    
    def _validate_extension(self, filename: str):
        """Validate file extension."""
        ext = Path(filename).suffix.lower()
        
        # Check if extension is in any allowed type
        allowed_extensions = [
            ext for exts in self.allowed_types.values() for ext in exts
        ]
        
        if ext not in allowed_extensions:
            raise FileValidationError(
                f"File extension '{ext}' not allowed. "
                f"Allowed: {', '.join(allowed_extensions)}"
            )
    
    def _detect_mime_type(self, uploaded_file: UploadedFile) -> Optional[str]:
        """Detect MIME type from file content."""
        if not HAS_MAGIC:
            # Fallback to extension-based detection
            return mimetypes.guess_type(uploaded_file.name)[0]
        
        try:
            # Read first chunk for magic detection
            uploaded_file.seek(0)
            chunk = uploaded_file.read(2048)
            uploaded_file.seek(0)
            
            # Use python-magic for accurate detection
            mime_type = magic.from_buffer(chunk, mime=True)
            return mime_type
        except Exception as e:
            logger.error(f"Failed to detect MIME type: {e}")
            # Fallback to extension-based detection
            return mimetypes.guess_type(uploaded_file.name)[0]
    
    def _validate_mime_type(self, uploaded_file: UploadedFile):
        """Validate MIME type from content."""
        mime_type = self._detect_mime_type(uploaded_file)
        
        if not mime_type:
            raise FileValidationError("Could not determine file type")
        
        if mime_type not in self.allowed_types:
            raise FileValidationError(
                f"File type '{mime_type}' not allowed. "
                f"Allowed: {', '.join(self.allowed_types.keys())}"
            )
    
    def _validate_content(self, uploaded_file: UploadedFile):
        """
        Validate file content for malicious patterns.
        This is a basic check - production should use proper malware scanning.
        """
        # Read file content
        uploaded_file.seek(0)
        content = uploaded_file.read()
        uploaded_file.seek(0)
        
        # Check for suspicious patterns (very basic)
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'eval(',
            b'base64,',
        ]
        
        content_lower = content.lower()
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                logger.warning(
                    f"Suspicious pattern found in {uploaded_file.name}: {pattern}"
                )
                # Don't block - just log warning
                # Production should use proper malware scanner
    
    def calculate_checksum(self, uploaded_file: UploadedFile) -> str:
        """
        Calculate SHA256 checksum of file.
        
        Args:
            uploaded_file: Uploaded file
            
        Returns:
            Hex string of SHA256 checksum
        """
        uploaded_file.seek(0)
        sha256 = hashlib.sha256()
        
        for chunk in uploaded_file.chunks(4096):
            sha256.update(chunk)
        
        uploaded_file.seek(0)
        return sha256.hexdigest()


class MalwareScannerStub:
    """
    Placeholder for malware scanning integration.
    In production, integrate with ClamAV, VirusTotal, or similar service.
    """
    
    @staticmethod
    def scan_file(uploaded_file: UploadedFile) -> Dict[str, Any]:
        """
        Scan file for malware.
        
        Args:
            uploaded_file: File to scan
            
        Returns:
            Scan results
        """
        # This is a stub - integrate with actual malware scanner
        logger.info(f"Malware scan requested for {uploaded_file.name} (stub)")
        
        return {
            'scanned': False,
            'clean': True,  # Assumed clean since no scanner
            'scanner': 'stub',
            'message': 'Malware scanning not configured',
        }


def validate_upload(uploaded_file: UploadedFile, 
                   allow_documents: bool = True,
                   allow_images: bool = True,
                   allow_archives: bool = False,
                   scan_malware: bool = False) -> Dict[str, Any]:
    """
    Validate an uploaded file with all checks.
    
    Args:
        uploaded_file: Django UploadedFile
        allow_documents: Allow document types
        allow_images: Allow image types
        allow_archives: Allow archive types
        scan_malware: Run malware scan (requires configuration)
        
    Returns:
        Validation results dictionary
    """
    validator = FileValidator(
        allow_documents=allow_documents,
        allow_images=allow_images,
        allow_archives=allow_archives
    )
    
    # Basic validation
    is_valid, error = validator.validate(uploaded_file)
    
    if not is_valid:
        return {
            'valid': False,
            'error': error,
            'filename': uploaded_file.name,
        }
    
    # Calculate checksum
    checksum = validator.calculate_checksum(uploaded_file)
    
    # Optional malware scan
    scan_results = None
    if scan_malware:
        scan_results = MalwareScannerStub.scan_file(uploaded_file)
        if not scan_results.get('clean', True):
            return {
                'valid': False,
                'error': 'File failed malware scan',
                'filename': uploaded_file.name,
                'scan_results': scan_results,
            }
    
    # Detect MIME type
    mime_type = validator._detect_mime_type(uploaded_file)
    
    return {
        'valid': True,
        'filename': uploaded_file.name,
        'size': uploaded_file.size,
        'mime_type': mime_type,
        'checksum': checksum,
        'scan_results': scan_results,
    }


# MinIO bucket policy documentation
MINIO_BUCKET_POLICIES = """
# MinIO Bucket Policy Configuration

## Recommended Bucket Structure

1. **user-uploads**: User-uploaded documents and files
   - Private access only
   - Versioning enabled
   - Lifecycle: Keep indefinitely or per retention policy

2. **job-artifacts**: Job output and generated artifacts
   - Private access only
   - Lifecycle: Clean up after 365 days (configurable via retention policy)

3. **public-shares**: Files shared via public links
   - Read-only public access for specific objects via presigned URLs
   - Short-lived presigned URLs (1-24 hours)
   - Lifecycle: Clean up after share link expires

## Example MinIO Policy (user-uploads bucket)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": ["arn:aws:iam::ACCOUNT-ID:user/backend-service"]
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::user-uploads/*",
        "arn:aws:s3:::user-uploads"
      ]
    }
  ]
}
```

## Presigned URL Best Practices

1. **Short expiration times**: 1 hour for downloads, 15 minutes for uploads
2. **Tenant scoping**: Include tenant ID in object key path
3. **Access logging**: Log all presigned URL generation and usage
4. **Revocation**: Cannot revoke presigned URLs early - use short expiration
5. **Content-Type validation**: Set Content-Type when generating upload URLs

## Security Headers for MinIO

Configure MinIO to return security headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy: default-src 'none'`

"""


def get_minio_policy_docs() -> str:
    """Get MinIO bucket policy documentation."""
    return MINIO_BUCKET_POLICIES
