"""
Service-to-service authentication.
Secure internal API calls between frontend and backend.
"""
import hmac
import hashlib
import time
from typing import Optional, Tuple
from django.conf import settings
from django.http import JsonResponse
from functools import wraps


def get_service_secret() -> str:
    """Get the service-to-service shared secret."""
    secret = getattr(settings, 'SERVICE_TO_SERVICE_SECRET', None)
    if not secret:
        # Fallback to SECRET_KEY for development
        secret = settings.SECRET_KEY
    return secret


def generate_service_token(timestamp: Optional[int] = None) -> str:
    """
    Generate a signed service token.
    
    Args:
        timestamp: Unix timestamp (defaults to current time)
    
    Returns:
        Token string in format: timestamp:signature
    """
    if timestamp is None:
        timestamp = int(time.time())
    
    secret = get_service_secret()
    message = f"service-call:{timestamp}"
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"{timestamp}:{signature}"


def verify_service_token(token: str, max_age: int = 300) -> Tuple[bool, Optional[str]]:
    """
    Verify a service token.
    
    Args:
        token: Token string in format timestamp:signature
        max_age: Maximum age of token in seconds (default 5 minutes)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        parts = token.split(':')
        if len(parts) != 2:
            return False, "Invalid token format"
        
        timestamp_str, provided_signature = parts
        timestamp = int(timestamp_str)
        
        # Check token age
        current_time = int(time.time())
        age = current_time - timestamp
        if age > max_age:
            return False, "Token expired"
        if age < -60:  # Allow 60 seconds clock skew
            return False, "Token from future"
        
        # Verify signature
        secret = get_service_secret()
        message = f"service-call:{timestamp}"
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(provided_signature, expected_signature):
            return False, "Invalid signature"
        
        return True, None
        
    except (ValueError, AttributeError) as e:
        return False, f"Token verification error: {str(e)}"


def require_service_auth(view_func):
    """
    Decorator to require service-to-service authentication.
    
    Usage:
        @require_service_auth
        def my_api_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Skip in development if explicitly disabled
        if getattr(settings, 'SKIP_SERVICE_AUTH', False) and settings.DEBUG:
            return view_func(request, *args, **kwargs)
        
        # Get token from header
        token = request.headers.get('X-Service-Token', '')
        
        # Verify token
        is_valid, error = verify_service_token(token)
        if not is_valid:
            return JsonResponse({
                'error': 'Service authentication required',
                'detail': error
            }, status=401)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


class ServiceAuthMiddleware:
    """
    Middleware to validate service-to-service calls.
    Applied selectively to internal API endpoints.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if this is an internal API call that requires service auth
        path = request.path
        
        # Define paths that require service auth
        # (exclude public endpoints like /api/auth/, share links, health checks)
        requires_auth = (
            path.startswith('/api/') and
            not path.startswith('/api/auth/') and
            not path.startswith('/api/healthz') and
            not path.startswith('/api/share/')
        )
        
        if requires_auth and not getattr(settings, 'SKIP_SERVICE_AUTH', False):
            token = request.headers.get('X-Service-Token', '')
            is_valid, error = verify_service_token(token)
            
            if not is_valid:
                return JsonResponse({
                    'error': 'Service authentication required',
                    'detail': error
                }, status=401)
        
        return self.get_response(request)
