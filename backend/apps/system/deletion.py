"""
Account deletion and data anonymization workflows.
Implements GDPR-compliant data removal and anonymization.
"""
from typing import Dict, Any, Optional
from datetime import datetime
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class DeletionStatus:
    """Account deletion status."""
    REQUESTED = 'requested'
    PENDING_REVIEW = 'pending_review'
    APPROVED = 'approved'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    
    CHOICES = [
        (REQUESTED, 'Deletion Requested'),
        (PENDING_REVIEW, 'Pending Admin Review'),
        (APPROVED, 'Approved for Deletion'),
        (IN_PROGRESS, 'Deletion In Progress'),
        (COMPLETED, 'Deletion Completed'),
        (CANCELLED, 'Deletion Cancelled'),
    ]


class AccountDeletionRequest:
    """
    Manages account deletion requests.
    Implements safe deletion workflow with admin approval.
    """
    
    @staticmethod
    def create_deletion_request(user: User, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new account deletion request.
        
        Args:
            user: User requesting deletion
            reason: Optional reason for deletion
            
        Returns:
            Deletion request details
        """
        from apps.auditing.models import AuthEvent
        
        # Check if there's already a pending request
        # (In a real implementation, this would check a DeletionRequest model)
        
        # Log deletion request
        AuthEvent.log(
            event_type='admin_action',
            user=user,
            details={
                'action': 'account_deletion_requested',
                'reason': reason,
                'timestamp': timezone.now().isoformat(),
            },
            success=True
        )
        
        logger.warning(f"Account deletion requested by user {user.username}: {reason}")
        
        return {
            'status': DeletionStatus.PENDING_REVIEW,
            'user_id': user.id,
            'username': user.username,
            'requested_at': timezone.now().isoformat(),
            'reason': reason,
            'message': (
                'Your deletion request has been received and is pending admin review. '
                'You will be notified via email once reviewed.'
            ),
            'estimated_completion_days': 30,
        }
    
    @staticmethod
    def approve_deletion(user_id: int, admin_user: User) -> Dict[str, Any]:
        """
        Approve a deletion request (admin action).
        
        Args:
            user_id: User ID to delete
            admin_user: Admin approving deletion
            
        Returns:
            Approval status
        """
        from apps.auditing.models import AuthEvent
        
        user = User.objects.get(id=user_id)
        
        # Log admin approval
        AuthEvent.log(
            event_type='admin_action',
            user=admin_user,
            details={
                'action': 'account_deletion_approved',
                'target_user_id': user_id,
                'target_username': user.username,
                'timestamp': timezone.now().isoformat(),
            },
            success=True
        )
        
        logger.warning(
            f"Account deletion approved by admin {admin_user.username} "
            f"for user {user.username}"
        )
        
        return {
            'status': DeletionStatus.APPROVED,
            'user_id': user_id,
            'approved_by': admin_user.username,
            'approved_at': timezone.now().isoformat(),
            'message': 'Deletion approved. Will be executed within 7 days.',
        }
    
    @staticmethod
    def execute_deletion(user_id: int, anonymize: bool = False) -> Dict[str, Any]:
        """
        Execute account deletion or anonymization.
        
        Args:
            user_id: User ID to delete/anonymize
            anonymize: If True, anonymize instead of delete
            
        Returns:
            Deletion/anonymization results
        """
        user = User.objects.get(id=user_id)
        
        if anonymize:
            return AccountDeletionRequest._anonymize_user(user)
        else:
            return AccountDeletionRequest._delete_user(user)
    
    @staticmethod
    @transaction.atomic
    def _anonymize_user(user: User) -> Dict[str, Any]:
        """
        Anonymize user data while preserving aggregates.
        
        Args:
            user: User to anonymize
            
        Returns:
            Anonymization results
        """
        original_username = user.username
        anonymized_username = f"deleted_user_{user.id}_{timezone.now().timestamp()}"
        
        results = {
            'method': 'anonymization',
            'user_id': user.id,
            'original_username': original_username,
            'anonymized_username': anonymized_username,
            'started_at': timezone.now().isoformat(),
            'operations': [],
        }
        
        # Anonymize user profile
        user.username = anonymized_username
        user.email = f"{anonymized_username}@deleted.local"
        user.first_name = ''
        user.last_name = ''
        user.is_active = False
        user.save()
        results['operations'].append('profile_anonymized')
        
        # Remove personal data from worklog entries
        from apps.worklog.models import WorkLog
        entries = WorkLog.objects.filter(tenant__owner=user)
        for entry in entries:
            # Keep work data but remove personally identifiable details
            if hasattr(entry, 'personal_notes'):
                entry.personal_notes = '[REDACTED]'
                entry.save()
        results['operations'].append(f'anonymized_{entries.count()}_worklog_entries')
        
        # Anonymize auth events (keep for security audit)
        from apps.auditing.models import AuthEvent
        auth_events = AuthEvent.objects.filter(user=user)
        auth_events.update(
            details={'anonymized': True, 'original_user_id': user.id}
        )
        results['operations'].append(f'anonymized_{auth_events.count()}_auth_events')
        
        # Keep tenant data but transfer ownership if possible
        from apps.tenants.models import Tenant
        tenants = Tenant.objects.filter(owner=user)
        for tenant in tenants:
            # Try to transfer to another admin
            other_admin = tenant.members.filter(
                tenantmembership__role='admin'
            ).exclude(id=user.id).first()
            
            if other_admin:
                tenant.owner = other_admin
                tenant.save()
                results['operations'].append(f'tenant_{tenant.id}_ownership_transferred')
            else:
                # Mark tenant for deletion
                tenant.is_active = False
                tenant.save()
                results['operations'].append(f'tenant_{tenant.id}_deactivated')
        
        results['completed_at'] = timezone.now().isoformat()
        results['status'] = 'success'
        
        logger.warning(f"User {original_username} anonymized successfully")
        
        return results
    
    @staticmethod
    @transaction.atomic
    def _delete_user(user: User) -> Dict[str, Any]:
        """
        Permanently delete user and associated data.
        WARNING: This is destructive and cannot be undone.
        
        Args:
            user: User to delete
            
        Returns:
            Deletion results
        """
        original_username = user.username
        user_id = user.id
        
        results = {
            'method': 'permanent_deletion',
            'user_id': user_id,
            'username': original_username,
            'started_at': timezone.now().isoformat(),
            'deleted': [],
        }
        
        # Delete user-owned data
        from apps.worklog.models import WorkLog
        from apps.artifacts.models import Artifact
        from apps.tenants.models import Tenant
        
        # Delete worklog entries
        entries_count = WorkLog.objects.filter(tenant__owner=user).count()
        WorkLog.objects.filter(tenant__owner=user).delete()
        results['deleted'].append(f'{entries_count}_worklog_entries')
        
        # Delete artifacts (triggers storage cleanup)
        artifacts_count = Artifact.objects.filter(tenant__owner=user).count()
        Artifact.objects.filter(tenant__owner=user).delete()
        results['deleted'].append(f'{artifacts_count}_artifacts')
        
        # Delete tenants (cascades to related data)
        tenants_count = Tenant.objects.filter(owner=user).count()
        Tenant.objects.filter(owner=user).delete()
        results['deleted'].append(f'{tenants_count}_tenants')
        
        # Delete auth events (optional - may want to keep for audit)
        from apps.auditing.models import AuthEvent
        auth_events_count = AuthEvent.objects.filter(user=user).count()
        # AuthEvent.objects.filter(user=user).delete()  # Uncomment to delete
        results['deleted'].append(f'{auth_events_count}_auth_events_kept_for_audit')
        
        # Finally, delete user
        user.delete()
        results['deleted'].append('user_account')
        
        results['completed_at'] = timezone.now().isoformat()
        results['status'] = 'success'
        
        logger.critical(f"User {original_username} (ID: {user_id}) permanently deleted")
        
        return results


class DataAnonymizer:
    """
    Utilities for anonymizing specific data types.
    """
    
    @staticmethod
    def anonymize_ip_address(ip: str) -> str:
        """
        Anonymize an IP address by zeroing last octet.
        
        Example: 192.168.1.100 -> 192.168.1.0
        """
        parts = ip.split('.')
        if len(parts) == 4:
            parts[-1] = '0'
            return '.'.join(parts)
        return ip
    
    @staticmethod
    def anonymize_email(email: str, user_id: int) -> str:
        """
        Anonymize an email address.
        
        Example: user@example.com -> deleted_123@deleted.local
        """
        return f"deleted_{user_id}@deleted.local"
    
    @staticmethod
    def anonymize_name(name: str) -> str:
        """Anonymize a name."""
        return '[REDACTED]'
    
    @staticmethod
    def anonymize_text_content(text: str) -> str:
        """Anonymize text content while preserving structure."""
        # Simple redaction - could be enhanced with NLP to preserve non-PII
        return '[CONTENT REDACTED]'
