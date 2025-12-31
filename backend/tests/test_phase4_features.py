"""
Phase 4 Feature Tests: Data Safety + Privacy + Portability + Governance
Tests data export, retention, privacy controls, file validation, audit logs, and tenant management.
"""
import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import json

from apps.tenants.models import Tenant
from apps.system.data_export import DataExporter, ExportRequest
from apps.system.retention import RetentionManager, retention_manager
from apps.system.privacy import PrivacyManager, PrivacyConsent, check_ai_context_allowed
from apps.system.deletion import AccountDeletionRequest, DataAnonymizer
from apps.system.file_validation import FileValidator, validate_upload, FileValidationError
from apps.system.admin_views import AuditLogViewer, TenantManager
from apps.auditing.models import AuthEvent


def create_test_user_with_tenant():
    """Create unique user with tenant."""
    import uuid
    username = f'user_{uuid.uuid4().hex[:8]}'
    user = User.objects.create_user(username=username, password='pass', email=f'{username}@test.com')
    tenant, created = Tenant.objects.get_or_create(owner=user, defaults={'name': f'Test Tenant {username}'})
    return user, tenant


@pytest.mark.django_db
class TestDataExport:
    """Test data export functionality."""
    
    def test_data_exporter_initialization(self):
        """Test DataExporter can be initialized."""
        user, tenant = create_test_user_with_tenant()
        
        exporter = DataExporter(user, tenant)
        assert exporter.user == user
        assert exporter.tenant == tenant
    
    def test_export_metadata(self):
        """Test export metadata generation."""
        user, tenant = create_test_user_with_tenant()
        
        exporter = DataExporter(user, tenant)
        metadata = exporter._get_export_metadata()
        
        assert metadata['user_id'] == user.id
        assert metadata['username'] == user.username
        assert metadata['tenant_id'] == tenant.id
        assert metadata['tenant_name'] == tenant.name
        assert 'export_date' in metadata
    
    def test_export_user_profile(self):
        """Test user profile export."""
        user, tenant = create_test_user_with_tenant()
        
        exporter = DataExporter(user, tenant)
        profile = exporter._export_user_profile()
        
        assert profile['username'] == user.username
        assert profile['email'] == user.email
        assert 'date_joined' in profile
        assert profile['is_active'] is True
    
    def test_export_all_data(self):
        """Test exporting all user data."""
        user, tenant = create_test_user_with_tenant()
        
        exporter = DataExporter(user, tenant)
        export_data = exporter.export_all()
        
        assert 'export_metadata' in export_data
        assert 'user_profile' in export_data
        assert 'worklog' in export_data
        assert 'skills' in export_data
        assert 'documents' in export_data
        assert 'reports' in export_data
        assert 'billing' in export_data


@pytest.mark.django_db
class TestRetentionPolicies:
    """Test data retention policies."""
    
    def test_retention_manager_initialization(self):
        """Test RetentionManager initializes with default policies."""
        manager = RetentionManager()
        
        assert 'system_logs' in manager.policies
        assert 'ai_transcripts' in manager.policies
        assert 'auth_events' in manager.policies
        
        # Check default policy values
        auth_policy = manager.get_policy('auth_events')
        assert auth_policy is not None
        assert auth_policy.days == 365
        assert auth_policy.enabled is True
    
    def test_update_retention_policy(self):
        """Test updating retention policy."""
        manager = RetentionManager()
        
        manager.update_policy('auth_events', days=180, enabled=True)
        
        policy = manager.get_policy('auth_events')
        assert policy.days == 180
    
    def test_cleanup_auth_events_dry_run(self):
        """Test auth events cleanup in dry run mode."""
        user, tenant = create_test_user_with_tenant()
        
        # Create old and new auth events
        old_date = timezone.now() - timedelta(days=400)
        AuthEvent.objects.create(
            event_type='login_success',
            user=user,
            timestamp=old_date,
            success=True
        )
        
        AuthEvent.objects.create(
            event_type='login_success',
            user=user,
            success=True
        )
        
        manager = RetentionManager()
        result = manager.cleanup_auth_events(dry_run=True)
        
        assert result['status'] == 'success'
        assert result['deleted'] >= 1  # At least one old event
        assert result['dry_run'] is True
        
        # Verify nothing was actually deleted
        assert AuthEvent.objects.filter(user=user).count() == 2
    
    def test_cleanup_summary(self):
        """Test getting cleanup summary."""
        manager = RetentionManager()
        
        summary = manager.get_cleanup_summary()
        
        assert 'timestamp' in summary
        assert 'total_records_to_delete' in summary
        assert 'policies' in summary
        assert len(summary['policies']) >= 3


@pytest.mark.django_db
class TestPrivacyControls:
    """Test privacy consent and controls."""
    
    def test_privacy_manager_initialization(self):
        """Test PrivacyManager initialization."""
        user, tenant = create_test_user_with_tenant()
        
        manager = PrivacyManager(user, tenant)
        assert manager.user == user
        assert manager.tenant == tenant
    
    def test_default_ai_consent(self):
        """Test default AI context consent is granted."""
        user, tenant = create_test_user_with_tenant()
        
        manager = PrivacyManager(user, tenant)
        assert manager.get_consent('ai_context') is True
    
    def test_grant_and_revoke_consent(self):
        """Test granting and revoking consent."""
        user, tenant = create_test_user_with_tenant()
        
        manager = PrivacyManager(user, tenant)
        
        # Grant marketing consent
        manager.grant_consent('marketing')
        assert manager.get_consent('marketing') is True
        
        # Revoke marketing consent
        manager.revoke_consent('marketing')
        assert manager.get_consent('marketing') is False
    
    def test_get_all_consents(self):
        """Test getting all consent settings."""
        user, tenant = create_test_user_with_tenant()
        
        manager = PrivacyManager(user, tenant)
        manager.grant_consent('analytics')
        
        consents = manager.get_all_consents()
        
        assert 'ai_context' in consents
        assert 'analytics' in consents
        assert 'marketing' in consents
        assert consents['analytics'] is True
    
    def test_check_ai_context_allowed(self):
        """Test AI context permission check."""
        user, tenant = create_test_user_with_tenant()
        
        # Should be allowed by default
        assert check_ai_context_allowed(user, tenant) is True
        
        # Revoke consent
        manager = PrivacyManager(user, tenant)
        manager.revoke_consent('ai_context')
        
        # Should now be denied
        assert check_ai_context_allowed(user, tenant) is False


@pytest.mark.django_db
class TestAccountDeletion:
    """Test account deletion and anonymization."""
    
    def test_create_deletion_request(self):
        """Test creating account deletion request."""
        user, tenant = create_test_user_with_tenant()
        
        result = AccountDeletionRequest.create_deletion_request(
            user, reason="Testing"
        )
        
        assert result['status'] == 'pending_review'
        assert result['user_id'] == user.id
        assert result['username'] == user.username
        assert 'message' in result
    
    def test_data_anonymizer_ip_address(self):
        """Test IP address anonymization."""
        original_ip = "192.168.1.100"
        anonymized = DataAnonymizer.anonymize_ip_address(original_ip)
        
        assert anonymized == "192.168.1.0"
    
    def test_data_anonymizer_email(self):
        """Test email anonymization."""
        original_email = "user@example.com"
        anonymized = DataAnonymizer.anonymize_email(original_email, user_id=123)
        
        assert anonymized == "deleted_123@deleted.local"
        assert original_email not in anonymized


@pytest.mark.django_db
class TestFileValidation:
    """Test file upload validation."""
    
    def test_file_validator_initialization(self):
        """Test FileValidator initialization."""
        validator = FileValidator(allow_documents=True, allow_images=True)
        
        assert len(validator.allowed_types) > 0
        assert 'application/pdf' in validator.allowed_types
        assert 'image/jpeg' in validator.allowed_types
    
    def test_validate_extension_allowed(self):
        """Test validating allowed file extension."""
        validator = FileValidator(allow_documents=True)
        
        # Should not raise exception
        validator._validate_extension('test.pdf')
        validator._validate_extension('document.docx')
    
    def test_validate_extension_disallowed(self):
        """Test rejecting disallowed file extension."""
        validator = FileValidator(allow_documents=True, allow_images=False)
        
        with pytest.raises(FileValidationError):
            validator._validate_extension('image.jpg')
    
    def test_validate_size(self):
        """Test file size validation."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        validator = FileValidator()
        
        # Small file should pass
        small_file = SimpleUploadedFile("test.txt", b"small content", content_type="text/plain")
        validator._validate_size(small_file)
        
        # Large file should fail
        large_content = b"x" * (101 * 1024 * 1024)  # 101 MB
        large_file = SimpleUploadedFile("large.txt", large_content, content_type="text/plain")
        
        with pytest.raises(FileValidationError):
            validator._validate_size(large_file)


@pytest.mark.django_db
class TestAuditLogViewer:
    """Test admin audit log viewer."""
    
    def test_audit_log_viewer_requires_staff(self):
        """Test that audit log viewer requires staff permission."""
        user, tenant = create_test_user_with_tenant()
        
        with pytest.raises(PermissionError):
            AuditLogViewer(user)
    
    def test_audit_log_viewer_initialization(self):
        """Test AuditLogViewer initialization with staff user."""
        user, tenant = create_test_user_with_tenant()
        user.is_staff = True
        user.save()
        
        viewer = AuditLogViewer(user)
        assert viewer.requesting_user == user
    
    def test_get_auth_events(self):
        """Test retrieving auth events."""
        user, tenant = create_test_user_with_tenant()
        user.is_staff = True
        user.save()
        
        # Create some auth events
        AuthEvent.log(
            event_type='login_success',
            user=user,
            success=True
        )
        
        viewer = AuditLogViewer(user)
        result = viewer.get_auth_events(page=1, per_page=10)
        
        assert 'events' in result
        assert 'pagination' in result
        assert len(result['events']) >= 1
    
    def test_get_event_summary(self):
        """Test event summary statistics."""
        user, tenant = create_test_user_with_tenant()
        user.is_staff = True
        user.save()
        
        # Create some events
        AuthEvent.log(event_type='login_success', user=user, success=True)
        AuthEvent.log(event_type='login_failure', user=user, success=False)
        
        viewer = AuditLogViewer(user)
        summary = viewer.get_event_summary(days=30)
        
        assert 'total_events' in summary
        assert 'failed_events' in summary
        assert 'failed_logins' in summary
        assert summary['total_events'] >= 2


@pytest.mark.django_db
class TestTenantManagement:
    """Test tenant management interface."""
    
    def test_tenant_manager_requires_staff(self):
        """Test that tenant manager requires staff permission."""
        user, tenant = create_test_user_with_tenant()
        
        with pytest.raises(PermissionError):
            TenantManager(user)
    
    def test_tenant_manager_initialization(self):
        """Test TenantManager initialization."""
        user, tenant = create_test_user_with_tenant()
        user.is_staff = True
        user.save()
        
        manager = TenantManager(user)
        assert manager.requesting_user == user
    
    def test_list_tenants(self):
        """Test listing tenants."""
        user, tenant = create_test_user_with_tenant()
        user.is_staff = True
        user.save()
        
        manager = TenantManager(user)
        result = manager.list_tenants(page=1, per_page=10)
        
        assert 'tenants' in result
        assert 'pagination' in result
        assert len(result['tenants']) >= 1
    
    def test_get_tenant_detail(self):
        """Test getting tenant details."""
        user, tenant = create_test_user_with_tenant()
        user.is_staff = True
        user.save()
        
        manager = TenantManager(user)
        detail = manager.get_tenant_detail(tenant.id)
        
        assert detail['id'] == tenant.id
        assert detail['name'] == tenant.name
        assert 'owner' in detail
        assert 'members' in detail
        assert 'quotas' in detail
        assert 'usage' in detail


@pytest.mark.django_db
class TestPhase4Integration:
    """Integration tests for Phase 4 features."""
    
    def test_full_data_lifecycle(self):
        """Test complete data lifecycle: create, privacy control, export, delete."""
        user, tenant = create_test_user_with_tenant()
        
        # 1. Create data (user profile exists)
        assert user.is_active is True
        
        # 2. Set privacy controls
        privacy_manager = PrivacyManager(user, tenant)
        privacy_manager.grant_consent('ai_context')
        assert privacy_manager.get_consent('ai_context') is True
        
        # 3. Export data
        exporter = DataExporter(user, tenant)
        export_data = exporter.export_all()
        assert 'user_profile' in export_data
        assert export_data['user_profile']['username'] == user.username
        
        # 4. Request deletion
        deletion_result = AccountDeletionRequest.create_deletion_request(
            user, reason="Testing full lifecycle"
        )
        assert deletion_result['status'] == 'pending_review'
    
    def test_retention_with_audit_logs(self):
        """Test retention policies work with audit logs."""
        user, tenant = create_test_user_with_tenant()
        
        # Create old event
        old_event = AuthEvent.log(
            event_type='login_success',
            user=user,
            success=True
        )
        old_event.timestamp = timezone.now() - timedelta(days=400)
        old_event.save()
        
        # Run retention cleanup
        manager = RetentionManager()
        result = manager.cleanup_auth_events(dry_run=True)
        
        assert result['deleted'] >= 1
    
    def test_admin_governance_workflow(self):
        """Test admin governance workflow."""
        # Create admin user
        admin_user = User.objects.create_user(
            username='admin_test',
            password='admin',
            is_staff=True
        )
        
        # Create regular user
        user, tenant = create_test_user_with_tenant()
        
        # Admin views audit logs
        viewer = AuditLogViewer(admin_user)
        events = viewer.get_auth_events(page=1)
        assert 'events' in events
        
        # Admin manages tenant
        manager = TenantManager(admin_user)
        tenants = manager.list_tenants()
        assert len(tenants['tenants']) >= 1
        
        # Admin gets tenant details
        detail = manager.get_tenant_detail(tenant.id)
        assert detail['id'] == tenant.id
