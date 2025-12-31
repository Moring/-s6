"""
Tenant quotas and concurrency limits.
Prevents resource abuse and ensures fair platform usage.
"""
from typing import Optional, Tuple
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class QuotaLimit:
    """Quota limit definition."""
    name: str
    limit: int
    window_hours: int
    description: str


# Default quota limits per tenant
DEFAULT_QUOTAS = {
    'jobs_per_day': QuotaLimit(
        name='jobs_per_day',
        limit=100,
        window_hours=24,
        description='Maximum jobs per day'
    ),
    'ai_tokens_per_day': QuotaLimit(
        name='ai_tokens_per_day',
        limit=10000,
        window_hours=24,
        description='Maximum AI tokens per day'
    ),
    'storage_bytes': QuotaLimit(
        name='storage_bytes',
        limit=1024 * 1024 * 1024,  # 1GB
        window_hours=0,  # No time window, absolute limit
        description='Maximum storage in bytes'
    ),
    'uploads_per_day': QuotaLimit(
        name='uploads_per_day',
        limit=50,
        window_hours=24,
        description='Maximum file uploads per day'
    ),
    'exports_per_day': QuotaLimit(
        name='exports_per_day',
        limit=5,
        window_hours=24,
        description='Maximum data exports per day'
    ),
    'reports_per_day': QuotaLimit(
        name='reports_per_day',
        limit=20,
        window_hours=24,
        description='Maximum reports generated per day'
    ),
}

# Plan-specific quotas
PLAN_QUOTAS = {
    'free': DEFAULT_QUOTAS,
    'starter': {
        **DEFAULT_QUOTAS,
        'jobs_per_day': QuotaLimit('jobs_per_day', 500, 24, 'Max jobs per day'),
        'ai_tokens_per_day': QuotaLimit('ai_tokens_per_day', 50000, 24, 'Max AI tokens per day'),
        'storage_bytes': QuotaLimit('storage_bytes', 5 * 1024 * 1024 * 1024, 0, 'Max storage (5GB)'),
    },
    'professional': {
        **DEFAULT_QUOTAS,
        'jobs_per_day': QuotaLimit('jobs_per_day', 2000, 24, 'Max jobs per day'),
        'ai_tokens_per_day': QuotaLimit('ai_tokens_per_day', 200000, 24, 'Max AI tokens per day'),
        'storage_bytes': QuotaLimit('storage_bytes', 20 * 1024 * 1024 * 1024, 0, 'Max storage (20GB)'),
    },
}


class QuotaManager:
    """Manage tenant quotas."""
    
    def __init__(self, tenant):
        self.tenant = tenant
        self.plan = getattr(tenant, 'plan', 'free')
    
    def get_quota(self, quota_name: str) -> QuotaLimit:
        """Get quota limit for tenant's plan."""
        quotas = PLAN_QUOTAS.get(self.plan, DEFAULT_QUOTAS)
        return quotas.get(quota_name)
    
    def check_quota(self, quota_name: str, amount: int = 1) -> Tuple[bool, Optional[str]]:
        """
        Check if quota allows operation.
        
        Args:
            quota_name: Name of quota to check
            amount: Amount to consume (default 1)
        
        Returns:
            Tuple of (allowed, error_message)
        """
        quota = self.get_quota(quota_name)
        if not quota:
            return True, None
        
        # Get current usage
        current = self.get_usage(quota_name)
        
        if current + amount > quota.limit:
            return False, f"Quota exceeded: {quota.description} (limit: {quota.limit})"
        
        return True, None
    
    def consume_quota(self, quota_name: str, amount: int = 1):
        """
        Consume quota.
        
        Args:
            quota_name: Name of quota to consume
            amount: Amount to consume (default 1)
        """
        quota = self.get_quota(quota_name)
        if not quota:
            return
        
        cache_key = self._get_cache_key(quota_name)
        
        # Increment counter
        try:
            cache.incr(cache_key, amount)
        except ValueError:
            # Key doesn't exist, create it
            if quota.window_hours > 0:
                ttl = quota.window_hours * 3600
                cache.set(cache_key, amount, ttl)
            else:
                # No expiry for absolute limits
                cache.set(cache_key, amount)
    
    def get_usage(self, quota_name: str) -> int:
        """Get current usage for quota."""
        cache_key = self._get_cache_key(quota_name)
        return cache.get(cache_key, 0)
    
    def reset_quota(self, quota_name: str):
        """Reset quota usage."""
        cache_key = self._get_cache_key(quota_name)
        cache.delete(cache_key)
    
    def _get_cache_key(self, quota_name: str) -> str:
        """Get cache key for quota."""
        return f"quota:{self.tenant.id}:{quota_name}"


class ConcurrencyLimiter:
    """Manage concurrent job execution per tenant and workflow."""
    
    def __init__(self, tenant, workflow_type: Optional[str] = None):
        self.tenant = tenant
        self.workflow_type = workflow_type
    
    def _get_concurrent_count(self, cache_key: str) -> int:
        """Get count of concurrent slots."""
        # Store as simple counter instead of set
        return cache.get(cache_key, 0)
    
    def acquire(self, job_id: str, timeout: int = 300) -> Tuple[bool, Optional[str]]:
        """
        Try to acquire concurrency slot.
        
        Args:
            job_id: Unique job identifier
            timeout: How long to hold the slot (seconds)
        
        Returns:
            Tuple of (acquired, error_message)
        """
        # Get limits
        tenant_limit = self._get_tenant_limit()
        workflow_limit = self._get_workflow_limit()
        
        # Check tenant-wide concurrency
        tenant_key = f"concurrency:tenant:{self.tenant.id}"
        tenant_count = self._get_concurrent_count(tenant_key)
        
        if tenant_count >= tenant_limit:
            return False, f"Tenant concurrency limit reached ({tenant_limit})"
        
        # Check workflow-specific concurrency
        if self.workflow_type:
            workflow_key = f"concurrency:workflow:{self.tenant.id}:{self.workflow_type}"
            workflow_count = self._get_concurrent_count(workflow_key)
            
            if workflow_count >= workflow_limit:
                return False, f"Workflow concurrency limit reached ({workflow_limit})"
        
        # Acquire slots
        slot_key = f"concurrency:slot:{job_id}"
        cache.set(slot_key, {
            'tenant_id': self.tenant.id,
            'workflow_type': self.workflow_type,
            'acquired_at': timezone.now().isoformat()
        }, timeout)
        
        # Increment counters
        if tenant_count == 0:
            cache.set(tenant_key, 1, timeout)
        else:
            try:
                cache.incr(tenant_key)
            except ValueError:
                cache.set(tenant_key, 1, timeout)
        
        if self.workflow_type:
            workflow_key = f"concurrency:workflow:{self.tenant.id}:{self.workflow_type}"
            workflow_count = cache.get(workflow_key, 0)
            if workflow_count == 0:
                cache.set(workflow_key, 1, timeout)
            else:
                try:
                    cache.incr(workflow_key)
                except ValueError:
                    cache.set(workflow_key, 1, timeout)
        
        return True, None
    
    def release(self, job_id: str):
        """Release concurrency slot."""
        slot_key = f"concurrency:slot:{job_id}"
        slot_data = cache.get(slot_key)
        
        if not slot_data:
            return
        
        # Decrement counters
        tenant_key = f"concurrency:tenant:{self.tenant.id}"
        try:
            if cache.get(tenant_key, 0) > 0:
                cache.decr(tenant_key)
        except ValueError:
            pass
        
        if self.workflow_type:
            workflow_key = f"concurrency:workflow:{self.tenant.id}:{self.workflow_type}"
            try:
                if cache.get(workflow_key, 0) > 0:
                    cache.decr(workflow_key)
            except ValueError:
                pass
        
        # Delete slot
        cache.delete(slot_key)
    
    def _get_tenant_limit(self) -> int:
        """Get tenant-wide concurrency limit."""
        plan = getattr(self.tenant, 'plan', 'free')
        limits = {
            'free': 2,
            'starter': 5,
            'professional': 20,
        }
        return limits.get(plan, 2)
    
    def _get_workflow_limit(self) -> int:
        """Get workflow-specific concurrency limit."""
        if not self.workflow_type:
            return float('inf')
        
        plan = getattr(self.tenant, 'plan', 'free')
        
        # Expensive workflows have tighter limits
        expensive_workflows = {'resume.refresh', 'report.generate', 'skills.extract'}
        
        if self.workflow_type in expensive_workflows:
            limits = {
                'free': 1,
                'starter': 2,
                'professional': 5,
            }
        else:
            limits = {
                'free': 2,
                'starter': 4,
                'professional': 10,
            }
        
        return limits.get(plan, 1)


def check_and_consume_quota(tenant, quota_name: str, amount: int = 1) -> Tuple[bool, Optional[str]]:
    """
    Helper to check and consume quota in one call.
    
    Returns:
        Tuple of (allowed, error_message)
    """
    manager = QuotaManager(tenant)
    allowed, error = manager.check_quota(quota_name, amount)
    
    if allowed:
        manager.consume_quota(quota_name, amount)
    
    return allowed, error
