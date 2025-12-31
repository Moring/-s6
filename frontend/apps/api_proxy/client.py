"""
Backend API client for frontend.
"""
import requests
import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class BackendAPIClient:
    """Client for communicating with the backend API."""
    
    def __init__(self, auth_token: Optional[str] = None):
        self.base_url = settings.BACKEND_BASE_URL
        self.timeout = 10
        self.auth_token = auth_token
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers including auth token if available."""
        headers = {'Content-Type': 'application/json'}
        if self.auth_token:
            headers['Authorization'] = f'Token {self.auth_token}'
        return headers
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request to backend API."""
        url = f"{self.base_url}{endpoint}"
        
        # Merge headers
        headers = self._get_headers()
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
            del kwargs['headers']
        
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Backend API error: {e}")
            return None
    
    def get(self, endpoint: str, **kwargs) -> Optional[Any]:
        """GET request to backend."""
        return self._make_request('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> Optional[Any]:
        """POST request to backend."""
        return self._make_request('POST', endpoint, **kwargs)
    
    def patch(self, endpoint: str, **kwargs) -> Optional[Any]:
        """PATCH request to backend."""
        return self._make_request('PATCH', endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Optional[Any]:
        """DELETE request to backend."""
        return self._make_request('DELETE', endpoint, **kwargs)
    
    def get_token(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Get auth token from backend.
        
        Args:
            username: User's username
            password: User's password
        
        Returns:
            Dict with 'token' and 'user' keys, or None on failure
        """
        return self.post('/api/auth/token/', json={
            'username': username,
            'password': password
        })
    
    def upload_file(self, file, auth_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Upload a file to backend.
        
        Args:
            file: Django UploadedFile object
            auth_token: Optional token override
        
        Returns:
            Response dict or None
        """
        url = f"{self.base_url}/api/artifacts/upload/"
        
        token = auth_token or self.auth_token
        headers = {}
        if token:
            headers['Authorization'] = f'Token {token}'
        
        try:
            files = {'file': (file.name, file.read(), file.content_type)}
            response = requests.post(
                url,
                files=files,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"File upload error: {e}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """Check backend health with caching."""
        cache_key = 'backend_health'
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        result = self._make_request('GET', '/api/readyz/')
        if result is None:
            result = {'status': 'error', 'error': 'Backend unreachable'}
        
        cache.set(cache_key, result, 10)  # Cache for 10 seconds
        return result
    
    def get_system_overview(self) -> Optional[Dict[str, Any]]:
        """Get system overview (requires staff access)."""
        cache_key = 'system_overview'
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        result = self._make_request('GET', '/system/overview/')
        if result:
            cache.set(cache_key, result, 10)
        
        return result
    
    def list_jobs(self, status: Optional[str] = None, limit: int = 10) -> Optional[Dict[str, Any]]:
        """List jobs with caching."""
        cache_key = f'jobs_list_{status}_{limit}'
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        params = {'limit': limit}
        if status:
            params['status'] = status
        
        result = self._make_request('GET', '/system/jobs/', params=params)
        if result:
            cache.set(cache_key, result, 5)  # Cache for 5 seconds
        
        return result
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job detail."""
        return self._make_request('GET', f'/api/jobs/{job_id}/')
    
    def get_job_events(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job events timeline."""
        return self._make_request('GET', f'/api/jobs/{job_id}/events/')
    
    def list_worklogs(self) -> Optional[Dict[str, Any]]:
        """List work logs."""
        cache_key = 'worklogs_list'
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        result = self._make_request('GET', '/api/worklogs/')
        if result:
            cache.set(cache_key, result, 10)
        
        return result
    
    def create_worklog(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new work log."""
        # Invalidate cache
        cache.delete('worklogs_list')
        return self._make_request('POST', '/api/worklogs/', json=data)
    
    def analyze_worklog(self, worklog_id: int) -> Optional[Dict[str, Any]]:
        """Trigger worklog analysis."""
        return self._make_request('POST', f'/api/worklogs/{worklog_id}/analyze/')
    
    def update_worklog(self, worklog_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a work log."""
        cache.delete('worklogs_list')
        return self._make_request('PATCH', f'/api/worklogs/{worklog_id}/', json=data)
    
    def delete_worklog(self, worklog_id: int) -> bool:
        """Delete a work log."""
        cache.delete('worklogs_list')
        result = self._make_request('DELETE', f'/api/worklogs/{worklog_id}/')
        return result is not None


def get_backend_client(request=None) -> BackendAPIClient:
    """
    Get or create backend API client instance.
    
    If request is provided and user is authenticated, will include auth token.
    """
    token = None
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        # Get token from session
        token = request.session.get('backend_token')
    
    return BackendAPIClient(auth_token=token)
