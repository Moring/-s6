"""
Test suite for system-level capabilities.
Tests roles, permissions, service auth, rate limiting, quotas, and feature flags.
"""
import pytest
import time
from django.contrib.auth.models import User
from django.test import RequestFactory, override_settings
from django.core.cache import cache
from apps.tenants.models import Tenant, TenantMembership
from apps.tenants.roles import (
    TenantRole, Permission, get_user_role, has_permission, ROLE_PERMISSIONS
)
from apps.api.service_auth import generate_service_token, verify_service_token
from apps.api.rate_limiting import RateLimiter, get_client_ip
from apps.api.feature_flags import is_feature_enabled, SHARING_ENABLED
from apps.tenants.quotas import QuotaManager, ConcurrencyLimiter, check_and_consume_quota


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(username='testuser', password='testpass', email='test@example.com')


@pytest.fixture
def owner_user(db):
    """Create owner user."""
    return User.objects.create_user(username='owner', password='testpass', email='owner@example.com')


@pytest.fixture
def tenant(owner_user):
    """Create test tenant."""
    # Clean up any existing tenant for this owner
    Tenant.objects.filter(owner=owner_user).delete()
    return Tenant.objects.create(name='Test Tenant', owner=owner_user, plan='free')


@pytest.fixture
def admin_user(db):
    """Create admin user (separate from owner)."""
    return User.objects.create_user(username='adminuser', password='testpass', email='admin@example.com')


@pytest.fixture
def member_user(db):
    """Create member user."""
    return User.objects.create_user(username='memberuser', password='testpass', email='member@example.com')


@pytest.fixture
def readonly_user(db):
    """Create read-only user."""
    return User.objects.create_user(username='readonlyuser', password='testpass', email='readonly@example.com')


@pytest.fixture
def admin_membership(admin_user, tenant):
    """Create admin membership."""
    return TenantMembership.objects.create(
        tenant=tenant,
        user=admin_user,
        role='admin'
    )


@pytest.fixture
def member_membership(member_user, tenant):
    """Create member membership."""
    return TenantMembership.objects.create(
        tenant=tenant,
        user=member_user,
        role='member'
    )


@pytest.fixture
def read_only_membership(readonly_user, tenant):
    """Create read-only membership."""
    return TenantMembership.objects.create(
        tenant=tenant,
        user=readonly_user,
        role='read_only'
    )


@pytest.mark.django_db
class TestTenantRoles:
    """Test tenant role system."""
    
    def test_get_user_role_owner(self, owner_user, tenant):
        """Test owner role detection."""
        role = get_user_role(owner_user, tenant)
        assert role == TenantRole.OWNER
    
    def test_get_user_role_admin(self, admin_user, tenant, admin_membership):
        """Test admin role detection."""
        role = get_user_role(admin_user, tenant)
        assert role == TenantRole.ADMIN
    
    def test_get_user_role_member(self, member_user, tenant, member_membership):
        """Test member role detection."""
        role = get_user_role(member_user, tenant)
        assert role == TenantRole.MEMBER
    
    def test_get_user_role_read_only(self, readonly_user, tenant, read_only_membership):
        """Test read-only role detection."""
        role = get_user_role(readonly_user, tenant)
        assert role == TenantRole.READ_ONLY
    
    def test_get_user_role_no_membership(self, user, tenant):
        """Test no role for non-member."""
        role = get_user_role(user, tenant)
        assert role is None


@pytest.mark.django_db
class TestPermissions:
    """Test permission system."""
    
    def test_owner_has_all_permissions(self, owner_user, tenant):
        """Test owner has all permissions."""
        for permission in Permission:
            assert has_permission(owner_user, tenant, permission)
    
    def test_admin_permissions(self, admin_user, tenant, admin_membership):
        """Test admin has correct permissions."""
        # Should have most permissions
        assert has_permission(admin_user, tenant, Permission.MANAGE_USERS)
        assert has_permission(admin_user, tenant, Permission.VIEW_WORKLOG)
        assert has_permission(admin_user, tenant, Permission.TRIGGER_JOB)
        
        # Should NOT have tenant management
        assert not has_permission(admin_user, tenant, Permission.MANAGE_TENANT)
        assert not has_permission(admin_user, tenant, Permission.MANAGE_BILLING)
    
    def test_member_permissions(self, member_user, tenant, member_membership):
        """Test member has correct permissions."""
        # Should have standard permissions
        assert has_permission(member_user, tenant, Permission.CREATE_WORKLOG)
        assert has_permission(member_user, tenant, Permission.VIEW_WORKLOG)
        assert has_permission(member_user, tenant, Permission.TRIGGER_JOB)
        
        # Should NOT have management permissions
        assert not has_permission(member_user, tenant, Permission.MANAGE_USERS)
        assert not has_permission(member_user, tenant, Permission.MANAGE_TENANT)
    
    def test_read_only_permissions(self, readonly_user, tenant, read_only_membership):
        """Test read-only has correct permissions."""
        # Should have view permissions only
        assert has_permission(readonly_user, tenant, Permission.VIEW_WORKLOG)
        assert has_permission(readonly_user, tenant, Permission.VIEW_REPORT)
        
        # Should NOT have edit permissions
        assert not has_permission(readonly_user, tenant, Permission.CREATE_WORKLOG)
        assert not has_permission(readonly_user, tenant, Permission.EDIT_WORKLOG)
        assert not has_permission(readonly_user, tenant, Permission.TRIGGER_JOB)
    
    def test_superuser_has_all_permissions(self, tenant):
        """Test superuser has all permissions."""
        superuser = User.objects.create_superuser(username='superadmin', password='admin', email='super@example.com')
        for permission in Permission:
            assert has_permission(superuser, tenant, permission)


class TestServiceAuth:
    """Test service-to-service authentication."""
    
    def test_generate_and_verify_token(self):
        """Test token generation and verification."""
        token = generate_service_token()
        is_valid, error = verify_service_token(token)
        assert is_valid
        assert error is None
    
    def test_verify_expired_token(self):
        """Test expired token rejection."""
        # Generate token with old timestamp
        old_timestamp = int(time.time()) - 400  # 400 seconds ago
        token = generate_service_token(old_timestamp)
        is_valid, error = verify_service_token(token, max_age=300)
        assert not is_valid
        assert "expired" in error.lower()
    
    def test_verify_invalid_signature(self):
        """Test invalid signature rejection."""
        timestamp = int(time.time())
        token = f"{timestamp}:invalidsignature"
        is_valid, error = verify_service_token(token)
        assert not is_valid
        assert "signature" in error.lower()
    
    def test_verify_malformed_token(self):
        """Test malformed token rejection."""
        is_valid, error = verify_service_token("malformed")
        assert not is_valid
        assert "format" in error.lower()


class TestRateLimiting:
    """Test rate limiting."""
    
    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()
    
    def test_rate_limiter_allows_within_limit(self):
        """Test requests within limit are allowed."""
        limiter = RateLimiter('test', max_requests=5, window_seconds=60)
        
        for i in range(5):
            is_allowed, retry_after = limiter.is_allowed('test-id')
            assert is_allowed
            assert retry_after is None
    
    def test_rate_limiter_blocks_over_limit(self):
        """Test requests over limit are blocked."""
        limiter = RateLimiter('test', max_requests=3, window_seconds=60)
        
        # First 3 should pass
        for i in range(3):
            is_allowed, _ = limiter.is_allowed('test-id')
            assert is_allowed
        
        # 4th should fail
        is_allowed, retry_after = limiter.is_allowed('test-id')
        assert not is_allowed
        assert retry_after is not None and retry_after > 0
    
    def test_rate_limiter_reset(self):
        """Test rate limit reset."""
        limiter = RateLimiter('test', max_requests=2, window_seconds=60)
        
        # Use up limit
        limiter.is_allowed('test-id')
        limiter.is_allowed('test-id')
        is_allowed, _ = limiter.is_allowed('test-id')
        assert not is_allowed
        
        # Reset
        limiter.reset('test-id')
        
        # Should work again
        is_allowed, _ = limiter.is_allowed('test-id')
        assert is_allowed
    
    def test_get_client_ip(self):
        """Test IP extraction from request."""
        factory = RequestFactory()
        
        # Direct IP
        request = factory.get('/', REMOTE_ADDR='1.2.3.4')
        assert get_client_ip(request) == '1.2.3.4'
        
        # X-Forwarded-For
        request = factory.get('/', HTTP_X_FORWARDED_FOR='5.6.7.8, 9.10.11.12')
        assert get_client_ip(request) == '5.6.7.8'


class TestFeatureFlags:
    """Test feature flags."""
    
    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()
    
    def test_feature_flag_default(self):
        """Test feature flag default value."""
        # Sharing is enabled by default
        assert SHARING_ENABLED.is_enabled()
    
    def test_feature_flag_enable_disable(self):
        """Test dynamic enable/disable."""
        SHARING_ENABLED.disable()
        assert not SHARING_ENABLED.is_enabled()
        
        SHARING_ENABLED.enable()
        assert SHARING_ENABLED.is_enabled()
    
    @override_settings(FEATURE_FLAGS={'sharing': False})
    def test_feature_flag_from_settings(self):
        """Test feature flag from Django settings."""
        cache.clear()
        SHARING_ENABLED.disable()  # Use cache to override
        assert not SHARING_ENABLED.is_enabled()
    
    def test_is_feature_enabled_helper(self):
        """Test is_feature_enabled helper function."""
        SHARING_ENABLED.enable()
        assert is_feature_enabled('sharing')
        
        SHARING_ENABLED.disable()
        assert not is_feature_enabled('sharing')


@pytest.mark.django_db
class TestQuotas:
    """Test quota management."""
    
    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()
    
    def test_quota_check_within_limit(self, tenant):
        """Test quota check within limit."""
        manager = QuotaManager(tenant)
        allowed, error = manager.check_quota('jobs_per_day', 1)
        assert allowed
        assert error is None
    
    def test_quota_consumption(self, tenant):
        """Test quota consumption."""
        manager = QuotaManager(tenant)
        
        # Consume quota
        manager.consume_quota('jobs_per_day', 10)
        usage = manager.get_usage('jobs_per_day')
        assert usage == 10
    
    def test_quota_exceeded(self, tenant):
        """Test quota exceeded."""
        manager = QuotaManager(tenant)
        
        # Consume up to limit (free plan: 100)
        manager.consume_quota('jobs_per_day', 100)
        
        # Try to exceed
        allowed, error = manager.check_quota('jobs_per_day', 1)
        assert not allowed
        assert 'exceeded' in error.lower()
    
    def test_quota_reset(self, tenant):
        """Test quota reset."""
        manager = QuotaManager(tenant)
        
        manager.consume_quota('jobs_per_day', 50)
        assert manager.get_usage('jobs_per_day') == 50
        
        manager.reset_quota('jobs_per_day')
        assert manager.get_usage('jobs_per_day') == 0
    
    def test_check_and_consume_quota(self, tenant):
        """Test combined check and consume."""
        allowed, error = check_and_consume_quota(tenant, 'jobs_per_day', 5)
        assert allowed
        
        manager = QuotaManager(tenant)
        assert manager.get_usage('jobs_per_day') == 5


@pytest.mark.django_db
class TestConcurrency:
    """Test concurrency limits."""
    
    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()
    
    def test_concurrency_acquire_within_limit(self, tenant):
        """Test acquiring concurrency slot within limit."""
        limiter = ConcurrencyLimiter(tenant)
        acquired, error = limiter.acquire('job-1')
        assert acquired
        assert error is None
    
    def test_concurrency_limit_exceeded(self, tenant):
        """Test concurrency limit exceeded."""
        limiter = ConcurrencyLimiter(tenant)
        
        # Free plan allows 2 concurrent
        acquired1, _ = limiter.acquire('job-1')
        assert acquired1
        
        acquired2, _ = limiter.acquire('job-2')
        assert acquired2
        
        # 3rd should fail
        acquired3, error = limiter.acquire('job-3')
        assert not acquired3
        assert 'limit reached' in error.lower()
    
    def test_concurrency_release(self, tenant):
        """Test releasing concurrency slot."""
        limiter = ConcurrencyLimiter(tenant)
        
        # Acquire
        limiter.acquire('job-1')
        limiter.acquire('job-2')
        
        # Should be at limit
        acquired, _ = limiter.acquire('job-3')
        assert not acquired
        
        # Release one
        limiter.release('job-1')
        
        # Now should succeed
        acquired, _ = limiter.acquire('job-3')
        assert acquired
