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
    
    def __init__(self):
        self.base_url = settings.BACKEND_BASE_URL
        self.timeout = 10
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request to backend API."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method,
                url,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Backend API error: {e}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """Check backend health with caching."""
        cache_key = 'backend_health'
        cached = cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        result = self._make_request('GET', '/api/healthz/')
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


# Singleton instance
_client = None


def get_backend_client() -> BackendAPIClient:
    """Get or create backend API client instance."""
    global _client
    if _client is None:
        _client = BackendAPIClient()
    return _client
