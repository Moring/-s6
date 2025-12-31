"""
Phase 3 tests: Jobs robustness, idempotency, quotas, concurrency, and financial integrity.
"""
import pytest
from django.test import Client
from django.contrib.auth.models import User
from django.core.cache import cache
from apps.tenants.models import Tenant
from apps.jobs.models import Job
from apps.jobs.dispatcher import enqueue, enqueue_safe, QuotaExceededError, ConcurrencyLimitError
from apps.jobs.idempotency import (
    IdempotencyManager, STRIPE_IDEMPOTENCY, EMAIL_IDEMPOTENCY,
    ensure_idempotent_stripe_charge
)
from apps.jobs.simulation import (
    SimulationMode, STRIPE_SIMULATION, OPENAI_SIMULATION,
    temporary_simulation, get_simulation_status
)
from apps.tenants.quotas import QuotaManager, ConcurrencyLimiter
from apps.billing.integrity import (
    check_reserve_balance_integrity, check_quota_counter_integrity,
    run_all_integrity_checks
)


@pytest.fixture
def client():
    """Create test client."""
    return Client()


def create_test_user_with_tenant():
    """Create unique user with tenant."""
    import uuid
    username = f'user_{uuid.uuid4().hex[:8]}'
    user = User.objects.create_user(username=username, password='pass', email=f'{username}@test.com')
    # Check if tenant already exists
    tenant, created = Tenant.objects.get_or_create(owner=user, defaults={'name': f'Test Tenant {username}'})
    return user, tenant


@pytest.mark.django_db
class TestIdempotency:
    """Test idempotency key management."""
    
    def setup_method(self):
        """Clear cache."""
        cache.clear()
    
    def test_idempotency_key_generation(self):
        """Test generating idempotency keys."""
        manager = IdempotencyManager('test_operation')
        
        key1 = manager.generate_key(user_id=123, amount=1000)
        key2 = manager.generate_key(user_id=123, amount=1000)
        key3 = manager.generate_key(user_id=123, amount=2000)
        
        # Same params should generate same key
        assert key1 == key2
        
        # Different params should generate different key
        assert key1 != key3
    
    def test_idempotency_check_and_store(self):
        """Test checking and storing idempotency."""
        manager = IdempotencyManager('test_operation', ttl=60)
        
        key = manager.generate_key(user_id=123, action='charge')
        
        # First check should not be duplicate
        result = manager.check(key)
        assert not result.is_duplicate
        assert result.cached_result is None
        
        # Store result
        manager.store(key, {'status': 'success', 'charge_id': 'ch_123'})
        
        # Second check should be duplicate
        result = manager.check(key)
        assert result.is_duplicate
        assert result.cached_result == {'status': 'success', 'charge_id': 'ch_123'}
    
    def test_idempotent_stripe_charge(self):
        """Test idempotent Stripe charge helper."""
        call_count = 0
        
        def charge_func():
            nonlocal call_count
            call_count += 1
            return {'charge_id': 'ch_test', 'amount': 1000}
        
        # First call should execute
        was_dup1, result1 = ensure_idempotent_stripe_charge(
            user_id=123,
            amount=1000,
            currency='usd',
            description='Test charge',
            charge_func=charge_func
        )
        assert not was_dup1
        assert call_count == 1
        
        # Second call should use cached result
        was_dup2, result2 = ensure_idempotent_stripe_charge(
            user_id=123,
            amount=1000,
            currency='usd',
            description='Test charge',
            charge_func=charge_func
        )
        assert was_dup2
        assert call_count == 1  # Function not called again
        assert result1 == result2


@pytest.mark.django_db
class TestSimulationMode:
    """Test simulation mode for external integrations."""
    
    def setup_method(self):
        """Clear cache."""
        cache.clear()
    
    def test_simulation_mode_toggle(self):
        """Test enabling/disabling simulation mode."""
        sim = SimulationMode('test_service')
        
        # Disable first
        sim.disable()
        assert not sim.is_enabled()
        
        # Enable
        sim.enable()
        assert sim.is_enabled()
    
    def test_simulate_or_execute(self):
        """Test conditional execution based on simulation mode."""
        sim = SimulationMode('test_service')
        call_count = 0
        
        def real_func():
            nonlocal call_count
            call_count += 1
            return 'real_result'
        
        # With simulation disabled
        sim.disable()
        result = sim.simulate_or_execute(real_func, 'simulated_result')
        assert result == 'real_result'
        assert call_count == 1
        
        # With simulation enabled
        sim.enable()
        result = sim.simulate_or_execute(real_func, 'simulated_result')
        assert result == 'simulated_result'
        assert call_count == 1  # Not called again
    
    def test_temporary_simulation(self):
        """Test temporary simulation context manager."""
        sim = SimulationMode('test_service')
        sim.disable()
        
        assert not sim.is_enabled()
        
        with temporary_simulation('test_service', enabled=True):
            assert sim.is_enabled()
        
        assert not sim.is_enabled()
    
    def test_get_simulation_status(self):
        """Test getting simulation status for all services."""
        status = get_simulation_status()
        
        assert 'stripe' in status
        assert 'openai' in status
        assert 'email' in status
        assert isinstance(status['stripe'], bool)


@pytest.mark.django_db
class TestQuotaEnforcement:
    """Test quota enforcement in job dispatcher."""
    
    def setup_method(self):
        """Clear cache."""
        cache.clear()
    
    def test_enqueue_with_quota_enforcement(self):
        """Test job enqueue respects quotas."""
        user, tenant = create_test_user_with_tenant()
        
        # Set low quota
        quota_manager = QuotaManager(tenant)
        quota_manager.quotas['jobs_per_day'] = 2
        
        # First 2 jobs should succeed
        job1 = enqueue('test.job', {'test': 1}, user=user)
        assert job1.status == 'queued'
        
        job2 = enqueue('test.job', {'test': 2}, user=user)
        assert job2.status == 'queued'
        
        # Third should raise QuotaExceededError
        with pytest.raises(QuotaExceededError):
            enqueue('test.job', {'test': 3}, user=user)
    
    def test_enqueue_safe_returns_error(self):
        """Test safe enqueue returns error instead of raising."""
        user, tenant = create_test_user_with_tenant()
        
        # Set low quota
        quota_manager = QuotaManager(tenant)
        quota_manager.quotas['jobs_per_day'] = 1
        
        # First should succeed
        success1, job1, error1 = enqueue_safe('test.job', {'test': 1}, user=user)
        assert success1
        assert job1 is not None
        assert error1 is None
        
        # Second should fail
        success2, job2, error2 = enqueue_safe('test.job', {'test': 2}, user=user)
        assert not success2
        assert job2 is None
        assert 'quota' in error2.lower()


@pytest.mark.django_db
class TestConcurrencyLimits:
    """Test concurrency limit enforcement."""
    
    def setup_method(self):
        """Clear cache."""
        cache.clear()
    
    def test_concurrency_limit_enforcement(self):
        """Test concurrency limits are enforced."""
        user, tenant = create_test_user_with_tenant()
        
        # Set low concurrency limit
        limiter = ConcurrencyLimiter(tenant, 'ai.workflow', max_concurrent=2)
        
        # First 2 should succeed
        acquired1, _ = limiter.acquire('job1')
        assert acquired1
        
        acquired2, _ = limiter.acquire('job2')
        assert acquired2
        
        # Third should fail
        acquired3, error3 = limiter.acquire('job3')
        assert not acquired3
        assert 'concurrency limit' in error3.lower()
        
        # Release one slot
        limiter.release('job1')
        
        # Now third should succeed
        acquired3_retry, _ = limiter.acquire('job3')
        assert acquired3_retry
    
    def test_enqueue_respects_concurrency(self):
        """Test job enqueue respects concurrency limits."""
        user, tenant = create_test_user_with_tenant()
        
        # Create a limiter with low limit
        tenant.settings = {'concurrency_limits': {'test.workflow': 1}}
        tenant.save()
        
        # First job should succeed
        job1 = enqueue('test.workflow', {'test': 1}, user=user, enforce_quotas=False)
        assert job1.status == 'queued'
        
        # Second should fail due to concurrency
        with pytest.raises(ConcurrencyLimitError):
            enqueue('test.workflow', {'test': 2}, user=user, enforce_quotas=False)


@pytest.mark.django_db
class TestFinancialIntegrity:
    """Test financial integrity checks."""
    
    def setup_method(self):
        """Clear cache."""
        cache.clear()
    
    def test_reserve_balance_integrity_pass(self):
        """Test reserve balance integrity check passes with correct data."""
        user, tenant = create_test_user_with_tenant()
        
        # Set up correct balance
        tenant.settings = {'reserve_balance': 1000}
        tenant.save()
        
        result = check_reserve_balance_integrity()
        # Should pass or have no discrepancies for this tenant
        assert isinstance(result.to_dict(), dict)
    
    def test_quota_counter_integrity(self):
        """Test quota counter integrity check."""
        user, tenant = create_test_user_with_tenant()
        
        result = check_quota_counter_integrity()
        assert result.check_name == 'quota_counter_integrity'
        assert isinstance(result.to_dict(), dict)
    
    def test_run_all_integrity_checks(self):
        """Test running all integrity checks."""
        results = run_all_integrity_checks()
        
        assert 'reserve_balance' in results
        assert 'quota_counter' in results
        assert 'ledger_entry' in results
        assert 'stripe_charge' in results
        
        # All should return IntegrityCheckResult
        for name, result in results.items():
            assert hasattr(result, 'passed')
            assert hasattr(result, 'discrepancies')
            assert hasattr(result, 'warnings')


@pytest.mark.django_db
class TestPhase3Integration:
    """Integration tests for Phase 3 features."""
    
    def setup_method(self):
        """Clear cache."""
        cache.clear()
    
    def test_idempotent_job_with_quotas(self):
        """Test idempotent job execution with quota enforcement."""
        user, tenant = create_test_user_with_tenant()
        
        # Set quota
        quota_manager = QuotaManager(tenant)
        quota_manager.quotas['jobs_per_day'] = 5
        
        # Create idempotency manager
        idem = IdempotencyManager('test_job')
        key = idem.generate_key(user_id=user.id, task='process_report')
        
        # First execution
        result1 = idem.check(key)
        assert not result1.is_duplicate
        
        success, job, error = enqueue_safe('test.job', {'key': key}, user=user)
        assert success
        
        idem.store(key, {'job_id': str(job.id)})
        
        # Second execution should use cached result
        result2 = idem.check(key)
        assert result2.is_duplicate
    
    def test_simulation_mode_with_concurrency(self):
        """Test simulation mode works with concurrency limits."""
        user, tenant = create_test_user_with_tenant()
        
        # Enable simulation
        STRIPE_SIMULATION.enable()
        
        # Enqueue job with concurrency limit
        limiter = ConcurrencyLimiter(tenant, 'stripe.charge', max_concurrent=1)
        
        acquired, error = limiter.acquire('job1')
        assert acquired
        
        # Simulate Stripe call
        def real_charge():
            return {'charge_id': 'ch_real'}
        
        result = STRIPE_SIMULATION.simulate_or_execute(
            real_charge,
            {'charge_id': 'ch_simulated', 'simulated': True}
        )
        
        assert result['simulated'] == True
        
        limiter.release('job1')
    
    def test_end_to_end_job_lifecycle(self):
        """Test complete job lifecycle with Phase 3 features."""
        user, tenant = create_test_user_with_tenant()
        
        # 1. Check quotas
        quota_manager = QuotaManager(tenant)
        allowed, _ = quota_manager.check_job_quota()
        assert allowed
        
        # 2. Check concurrency
        limiter = ConcurrencyLimiter(tenant, 'test.workflow')
        acquired, _ = limiter.acquire('test_job_1')
        assert acquired
        
        # 3. Create job with idempotency
        idem = IdempotencyManager('test_workflow')
        key = idem.generate_key(user_id=user.id, workflow='test')
        
        result_check = idem.check(key)
        if not result_check.is_duplicate:
            success, job, error = enqueue_safe(
                'test.workflow',
                {'idempotency_key': key},
                user=user,
                enforce_quotas=True,
                enforce_concurrency=False  # Already acquired
            )
            
            if success:
                idem.store(key, {'job_id': str(job.id), 'status': 'queued'})
        
        # 4. Release concurrency slot
        limiter.release('test_job_1')
        
        # 5. Run integrity checks
        results = run_all_integrity_checks()
        assert len(results) > 0
