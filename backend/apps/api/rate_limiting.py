"""
Rate limiting for abuse protection.
Protects auth endpoints, share links, and expensive operations.
"""
import time
from typing import Optional
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings


class RateLimiter:
    """
    Rate limiter using Django cache backend.
    """
    
    def __init__(self, key_prefix: str, max_requests: int, window_seconds: int):
        """
        Initialize rate limiter.
        
        Args:
            key_prefix: Cache key prefix for this limiter
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def get_key(self, identifier: str) -> str:
        """Get cache key for identifier."""
        return f"ratelimit:{self.key_prefix}:{identifier}"
    
    def is_allowed(self, identifier: str) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
        
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        key = self.get_key(identifier)
        
        # Get current count
        current = cache.get(key, 0)
        
        if current >= self.max_requests:
            # Rate limit exceeded - return window seconds as retry_after
            return False, self.window_seconds
        
        # Increment counter
        if current == 0:
            # First request in window
            cache.set(key, 1, self.window_seconds)
        else:
            cache.incr(key)
        
        return True, None
    
    def reset(self, identifier: str):
        """Reset rate limit for identifier."""
        key = self.get_key(identifier)
        cache.delete(key)


# Predefined rate limiters
AUTH_RATE_LIMITER = RateLimiter(
    key_prefix='auth',
    max_requests=5,
    window_seconds=300  # 5 requests per 5 minutes
)

SIGNUP_RATE_LIMITER = RateLimiter(
    key_prefix='signup',
    max_requests=3,
    window_seconds=3600  # 3 requests per hour
)

PASSKEY_RATE_LIMITER = RateLimiter(
    key_prefix='passkey',
    max_requests=10,
    window_seconds=3600  # 10 requests per hour
)

SHARE_LINK_RATE_LIMITER = RateLimiter(
    key_prefix='share_link',
    max_requests=100,
    window_seconds=3600  # 100 requests per hour
)

EXPORT_RATE_LIMITER = RateLimiter(
    key_prefix='export',
    max_requests=5,
    window_seconds=3600  # 5 exports per hour
)

AI_ACTION_RATE_LIMITER = RateLimiter(
    key_prefix='ai_action',
    max_requests=20,
    window_seconds=3600  # 20 AI actions per hour
)

REPORT_RATE_LIMITER = RateLimiter(
    key_prefix='report',
    max_requests=10,
    window_seconds=3600  # 10 reports per hour
)


def get_client_ip(request) -> str:
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def rate_limit(limiter: RateLimiter, identifier_func=None):
    """
    Decorator to apply rate limiting to views.
    
    Args:
        limiter: RateLimiter instance
        identifier_func: Function to extract identifier from request
                        (defaults to client IP)
    
    Usage:
        @rate_limit(AUTH_RATE_LIMITER)
        def login_view(request):
            ...
        
        @rate_limit(AI_ACTION_RATE_LIMITER, lambda r: f"{r.user.id}")
        def trigger_ai_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get identifier
            if identifier_func:
                identifier = identifier_func(request)
            else:
                identifier = get_client_ip(request)
            
            # Check rate limit
            is_allowed, retry_after = limiter.is_allowed(identifier)
            
            if not is_allowed:
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'retry_after': retry_after
                }, status=429, headers={
                    'Retry-After': str(retry_after)
                })
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


class RateLimitMiddleware:
    """
    Middleware to apply rate limiting globally to specific paths.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip if maintenance mode
        if getattr(settings, 'MAINTENANCE_MODE', False):
            return self.get_response(request)
        
        # Apply rate limiting based on path
        identifier = get_client_ip(request)
        
        # Auth endpoints
        if request.path in ['/api/auth/login/', '/api/auth/token/', '/accounts/login/']:
            is_allowed, retry_after = AUTH_RATE_LIMITER.is_allowed(identifier)
            if not is_allowed:
                return JsonResponse({
                    'error': 'Too many login attempts',
                    'retry_after': retry_after
                }, status=429)
        
        # Signup/passkey endpoints
        elif request.path in ['/api/auth/signup/', '/api/auth/passkey/validate/']:
            is_allowed, retry_after = PASSKEY_RATE_LIMITER.is_allowed(identifier)
            if not is_allowed:
                return JsonResponse({
                    'error': 'Too many signup attempts',
                    'retry_after': retry_after
                }, status=429)
        
        return self.get_response(request)
