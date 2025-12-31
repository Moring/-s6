"""
Feature flags for controlled rollouts.
Allows enabling/disabling features without code changes.
"""
from django.conf import settings
from django.core.cache import cache
from typing import Optional, Any
import os


class FeatureFlag:
    """Feature flag definition."""
    
    def __init__(self, name: str, default: bool = False, description: str = ""):
        self.name = name
        self.default = default
        self.description = description
    
    def is_enabled(self, user=None, tenant=None) -> bool:
        """
        Check if feature is enabled.
        
        Args:
            user: Optional user for user-specific flags
            tenant: Optional tenant for tenant-specific flags
        
        Returns:
            bool: True if feature is enabled
        """
        # Check env var override
        env_key = f"FEATURE_{self.name.upper()}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value.lower() in ['true', '1', 'yes', 'on']
        
        # Check cache for dynamic flags
        cache_key = f"feature_flag:{self.name}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Check settings
        flags = getattr(settings, 'FEATURE_FLAGS', {})
        return flags.get(self.name, self.default)
    
    def enable(self, ttl: Optional[int] = None):
        """Enable feature flag dynamically."""
        cache_key = f"feature_flag:{self.name}"
        cache.set(cache_key, True, ttl)
    
    def disable(self, ttl: Optional[int] = None):
        """Disable feature flag dynamically."""
        cache_key = f"feature_flag:{self.name}"
        cache.set(cache_key, False, ttl)


# Define feature flags
SHARING_ENABLED = FeatureFlag(
    name='sharing',
    default=True,
    description='Enable share link creation and access'
)

EXPORTS_ENABLED = FeatureFlag(
    name='exports',
    default=True,
    description='Enable data export functionality'
)

AI_WORKFLOWS_ENABLED = FeatureFlag(
    name='ai_workflows',
    default=True,
    description='Enable AI-powered workflows'
)

EMAIL_NOTIFICATIONS_ENABLED = FeatureFlag(
    name='email_notifications',
    default=False,
    description='Enable email notifications'
)

STRIPE_ENABLED = FeatureFlag(
    name='stripe',
    default=False,
    description='Enable Stripe billing integration'
)

VLLM_PROVIDER_ENABLED = FeatureFlag(
    name='vllm_provider',
    default=False,
    description='Enable vLLM provider for AI'
)

MALWARE_SCANNING_ENABLED = FeatureFlag(
    name='malware_scanning',
    default=False,
    description='Enable malware scanning for uploads'
)

ACCOUNT_DELETION_ENABLED = FeatureFlag(
    name='account_deletion',
    default=True,
    description='Enable account deletion requests'
)

SUPPORT_IMPERSONATION_ENABLED = FeatureFlag(
    name='support_impersonation',
    default=False,
    description='Enable support user impersonation (requires consent)'
)


def is_feature_enabled(feature_name: str, user=None, tenant=None) -> bool:
    """
    Check if a feature is enabled.
    
    Args:
        feature_name: Name of feature flag
        user: Optional user
        tenant: Optional tenant
    
    Returns:
        bool: True if enabled
    """
    # Map common names to flag objects
    flags = {
        'sharing': SHARING_ENABLED,
        'exports': EXPORTS_ENABLED,
        'ai_workflows': AI_WORKFLOWS_ENABLED,
        'email_notifications': EMAIL_NOTIFICATIONS_ENABLED,
        'stripe': STRIPE_ENABLED,
        'vllm_provider': VLLM_PROVIDER_ENABLED,
        'malware_scanning': MALWARE_SCANNING_ENABLED,
        'account_deletion': ACCOUNT_DELETION_ENABLED,
        'support_impersonation': SUPPORT_IMPERSONATION_ENABLED,
    }
    
    flag = flags.get(feature_name)
    if not flag:
        return False
    
    return flag.is_enabled(user, tenant)


def require_feature(feature_name: str):
    """
    Decorator to require feature flag on views.
    
    Usage:
        @require_feature('exports')
        def export_view(request):
            ...
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            from django.http import JsonResponse
            from django.core.exceptions import PermissionDenied
            
            if not is_feature_enabled(feature_name):
                if request.content_type == 'application/json':
                    return JsonResponse({
                        'error': 'Feature not available',
                        'feature': feature_name
                    }, status=403)
                raise PermissionDenied('This feature is currently disabled')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Initialize feature flags from settings
def init_feature_flags():
    """Initialize feature flags from Django settings."""
    # Check for disable sharing flag
    if getattr(settings, 'DISABLE_SHARING', False):
        SHARING_ENABLED.disable()
    
    # Check for email configuration
    email_configured = all([
        getattr(settings, 'EMAIL_HOST', None),
        getattr(settings, 'EMAIL_HOST_USER', None),
    ])
    if email_configured:
        EMAIL_NOTIFICATIONS_ENABLED.enable()
    
    # Check for Stripe configuration
    stripe_configured = getattr(settings, 'STRIPE_SECRET_KEY', None)
    if stripe_configured:
        STRIPE_ENABLED.enable()
    
    # Check for vLLM configuration
    if getattr(settings, 'LLM_PROVIDER', 'local') == 'vllm':
        VLLM_PROVIDER_ENABLED.enable()
