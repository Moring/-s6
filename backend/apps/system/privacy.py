"""
Privacy controls for user data and AI context usage.
Enables users to control how their data is used for AI processing.
"""
from typing import Optional, Dict, Any, List
from django.contrib.auth.models import User
from django.utils import timezone
import logging

# Import models from system.models to avoid duplication
from apps.system.models import PrivacyConsent, DocumentPrivacySettings, EntryPrivacySettings

logger = logging.getLogger(__name__)


class PrivacyManager:
    """
    Manages user privacy settings and consent.
    """
    
    def __init__(self, user: User, tenant=None):
        self.user = user
        self.tenant = tenant or self._get_user_tenant()
    
    def _get_user_tenant(self):
        """Get user's primary tenant."""
        from apps.tenants.models import Tenant
        from django.db.models import Q
        
        return Tenant.objects.filter(
            Q(owner=self.user) | Q(members=self.user)
        ).first()
    
    def get_consent(self, consent_type: str) -> bool:
        """
        Check if user has granted specific consent.
        
        Args:
            consent_type: Type of consent to check
            
        Returns:
            True if consent granted, False otherwise
        """
        try:
            consent = PrivacyConsent.objects.get(
                user=self.user,
                tenant=self.tenant,
                consent_type=consent_type
            )
            return consent.granted
        except PrivacyConsent.DoesNotExist:
            # Default: AI context consent granted, others not granted
            return consent_type == 'ai_context'
    
    def grant_consent(self, consent_type: str):
        """Grant a specific consent."""
        consent, created = PrivacyConsent.objects.get_or_create(
            user=self.user,
            tenant=self.tenant,
            consent_type=consent_type,
            defaults={'granted': True, 'granted_at': timezone.now()}
        )
        
        if not created and not consent.granted:
            consent.grant()
        
        logger.info(f"User {self.user.username} granted consent: {consent_type}")
    
    def revoke_consent(self, consent_type: str):
        """Revoke a specific consent."""
        try:
            consent = PrivacyConsent.objects.get(
                user=self.user,
                tenant=self.tenant,
                consent_type=consent_type
            )
            consent.revoke()
            logger.info(f"User {self.user.username} revoked consent: {consent_type}")
        except PrivacyConsent.DoesNotExist:
            # Create revoked consent record
            PrivacyConsent.objects.create(
                user=self.user,
                tenant=self.tenant,
                consent_type=consent_type,
                granted=False,
                revoked_at=timezone.now()
            )
    
    def get_all_consents(self) -> Dict[str, bool]:
        """Get all consent settings for user."""
        consents = PrivacyConsent.objects.filter(
            user=self.user,
            tenant=self.tenant
        )
        
        result = {
            consent_type: self.get_consent(consent_type)
            for consent_type, _ in PrivacyConsent.CONSENT_TYPES
        }
        
        return result
    
    def set_document_privacy(self, artifact_id: int, allow_ai_context: bool = True, 
                            allow_indexing: bool = True):
        """
        Set privacy settings for a document.
        
        Args:
            artifact_id: Artifact ID
            allow_ai_context: Allow document to be used as AI context
            allow_indexing: Allow document to be indexed
        """
        from apps.artifacts.models import Artifact
        
        artifact = Artifact.objects.get(id=artifact_id, tenant=self.tenant)
        
        settings, created = DocumentPrivacySettings.objects.update_or_create(
            artifact=artifact,
            defaults={
                'allow_ai_context': allow_ai_context,
                'allow_indexing': allow_indexing,
                'updated_by': self.user,
            }
        )
        
        logger.info(
            f"Updated privacy settings for artifact {artifact_id}: "
            f"AI={allow_ai_context}, indexing={allow_indexing}"
        )
    
    def set_entry_privacy(self, entry_id: int, allow_ai_context: bool = True,
                         exclude_from_exports: bool = False):
        """
        Set privacy settings for a worklog entry.
        
        Args:
            entry_id: Worklog entry ID
            allow_ai_context: Allow entry to be used as AI context
            exclude_from_exports: Exclude from data exports
        """
        from apps.worklog.models import WorkLog
        
        entry = WorkLog.objects.get(id=entry_id, tenant=self.tenant)
        
        settings, created = EntryPrivacySettings.objects.update_or_create(
            worklog_entry=entry,
            defaults={
                'allow_ai_context': allow_ai_context,
                'exclude_from_exports': exclude_from_exports,
                'updated_by': self.user,
            }
        )
        
        logger.info(
            f"Updated privacy settings for entry {entry_id}: "
            f"AI={allow_ai_context}, exclude_exports={exclude_from_exports}"
        )
    
    def get_ai_allowed_documents(self) -> List[int]:
        """
        Get list of document IDs that can be used as AI context.
        
        Returns:
            List of artifact IDs
        """
        from apps.artifacts.models import Artifact
        
        # Check global AI context consent
        if not self.get_consent('ai_context'):
            return []
        
        # Get all artifacts for tenant
        all_artifacts = Artifact.objects.filter(tenant=self.tenant).values_list('id', flat=True)
        
        # Get artifacts with explicit privacy settings that disallow AI
        disallowed = DocumentPrivacySettings.objects.filter(
            artifact__tenant=self.tenant,
            allow_ai_context=False
        ).values_list('artifact_id', flat=True)
        
        # Return artifacts not in disallowed list
        return [aid for aid in all_artifacts if aid not in disallowed]
    
    def get_ai_allowed_entries(self) -> List[int]:
        """
        Get list of worklog entry IDs that can be used as AI context.
        
        Returns:
            List of entry IDs
        """
        from apps.worklog.models import WorkLog
        
        # Check global AI context consent
        if not self.get_consent('ai_context'):
            return []
        
        # Get all entries for tenant
        all_entries = WorkLog.objects.filter(tenant=self.tenant).values_list('id', flat=True)
        
        # Get entries with explicit privacy settings that disallow AI
        disallowed = EntryPrivacySettings.objects.filter(
            worklog_entry__tenant=self.tenant,
            allow_ai_context=False
        ).values_list('worklog_entry_id', flat=True)
        
        # Return entries not in disallowed list
        return [eid for eid in all_entries if eid not in disallowed]


def check_ai_context_allowed(user: User, tenant, artifact_id: Optional[int] = None,
                             entry_id: Optional[int] = None) -> bool:
    """
    Check if data can be used as AI context.
    
    Args:
        user: User making the request
        tenant: Tenant
        artifact_id: Optional artifact ID to check
        entry_id: Optional entry ID to check
        
    Returns:
        True if allowed, False otherwise
    """
    manager = PrivacyManager(user, tenant)
    
    # Check global consent
    if not manager.get_consent('ai_context'):
        return False
    
    # Check specific artifact
    if artifact_id:
        try:
            settings = DocumentPrivacySettings.objects.get(artifact_id=artifact_id)
            return settings.allow_ai_context
        except DocumentPrivacySettings.DoesNotExist:
            return True  # Default: allowed
    
    # Check specific entry
    if entry_id:
        try:
            settings = EntryPrivacySettings.objects.get(worklog_entry_id=entry_id)
            return settings.allow_ai_context
        except EntryPrivacySettings.DoesNotExist:
            return True  # Default: allowed
    
    return True
