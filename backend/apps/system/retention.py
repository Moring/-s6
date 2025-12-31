"""
Data retention policies for logs, AI transcripts, artifacts, and audit logs.
Implements automatic cleanup and retention controls.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """Retention policy definition."""
    name: str
    days: int
    description: str
    enabled: bool = True


# Default retention policies
DEFAULT_RETENTION_POLICIES = {
    'system_logs': RetentionPolicy(
        name='system_logs',
        days=90,
        description='System and application logs'
    ),
    'ai_transcripts': RetentionPolicy(
        name='ai_transcripts',
        days=180,
        description='AI conversation transcripts and prompts'
    ),
    'job_artifacts': RetentionPolicy(
        name='job_artifacts',
        days=365,
        description='Job execution artifacts and results'
    ),
    'share_link_access_logs': RetentionPolicy(
        name='share_link_access_logs',
        days=90,
        description='Share link access audit logs'
    ),
    'auth_events': RetentionPolicy(
        name='auth_events',
        days=365,
        description='Authentication and authorization audit logs'
    ),
    'observability_events': RetentionPolicy(
        name='observability_events',
        days=90,
        description='Observability timeline events'
    ),
    'failed_jobs': RetentionPolicy(
        name='failed_jobs',
        days=180,
        description='Failed job records for debugging'
    ),
}


class RetentionManager:
    """
    Manages retention policies and cleanup operations.
    """
    
    def __init__(self):
        self.policies = DEFAULT_RETENTION_POLICIES.copy()
    
    def get_policy(self, policy_name: str) -> Optional[RetentionPolicy]:
        """Get retention policy by name."""
        return self.policies.get(policy_name)
    
    def update_policy(self, policy_name: str, days: int, enabled: bool = True):
        """Update retention policy."""
        if policy_name in self.policies:
            self.policies[policy_name].days = days
            self.policies[policy_name].enabled = enabled
        else:
            raise ValueError(f"Unknown retention policy: {policy_name}")
    
    def cleanup_auth_events(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up old auth events per retention policy.
        
        Args:
            dry_run: If True, return count without deleting
            
        Returns:
            Cleanup results
        """
        from apps.auditing.models import AuthEvent
        
        policy = self.get_policy('auth_events')
        if not policy or not policy.enabled:
            return {'policy': 'auth_events', 'status': 'disabled', 'deleted': 0}
        
        cutoff_date = timezone.now() - timedelta(days=policy.days)
        
        old_events = AuthEvent.objects.filter(timestamp__lt=cutoff_date)
        count = old_events.count()
        
        if not dry_run:
            old_events.delete()
            logger.info(f"Cleaned up {count} auth events older than {policy.days} days")
        
        return {
            'policy': 'auth_events',
            'status': 'success',
            'deleted': count,
            'cutoff_date': cutoff_date.isoformat(),
            'dry_run': dry_run,
        }
    
    def cleanup_observability_events(self, dry_run: bool = False) -> Dict[str, Any]:
        """Clean up old observability events."""
        from apps.observability.models import Event
        
        policy = self.get_policy('observability_events')
        if not policy or not policy.enabled:
            return {'policy': 'observability_events', 'status': 'disabled', 'deleted': 0}
        
        cutoff_date = timezone.now() - timedelta(days=policy.days)
        
        old_events = Event.objects.filter(timestamp__lt=cutoff_date)
        count = old_events.count()
        
        if not dry_run:
            old_events.delete()
            logger.info(f"Cleaned up {count} observability events older than {policy.days} days")
        
        return {
            'policy': 'observability_events',
            'status': 'success',
            'deleted': count,
            'cutoff_date': cutoff_date.isoformat(),
            'dry_run': dry_run,
        }
    
    def cleanup_failed_jobs(self, dry_run: bool = False) -> Dict[str, Any]:
        """Clean up old failed job records."""
        from apps.jobs.models import Job
        
        policy = self.get_policy('failed_jobs')
        if not policy or not policy.enabled:
            return {'policy': 'failed_jobs', 'status': 'disabled', 'deleted': 0}
        
        cutoff_date = timezone.now() - timedelta(days=policy.days)
        
        old_jobs = Job.objects.filter(
            status='failed',
            finished_at__lt=cutoff_date
        )
        count = old_jobs.count()
        
        if not dry_run:
            old_jobs.delete()
            logger.info(f"Cleaned up {count} failed jobs older than {policy.days} days")
        
        return {
            'policy': 'failed_jobs',
            'status': 'success',
            'deleted': count,
            'cutoff_date': cutoff_date.isoformat(),
            'dry_run': dry_run,
        }
    
    def cleanup_ai_transcripts(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up old AI transcripts.
        Note: Actual implementation depends on where transcripts are stored.
        """
        policy = self.get_policy('ai_transcripts')
        if not policy or not policy.enabled:
            return {'policy': 'ai_transcripts', 'status': 'disabled', 'deleted': 0}
        
        # TODO: Implement based on actual AI transcript storage
        # This is a placeholder for the structure
        return {
            'policy': 'ai_transcripts',
            'status': 'not_implemented',
            'deleted': 0,
            'message': 'AI transcript cleanup not yet implemented',
        }
    
    def cleanup_job_artifacts(self, dry_run: bool = False) -> Dict[str, Any]:
        """Clean up old job artifacts from storage."""
        from apps.artifacts.models import Artifact
        
        policy = self.get_policy('job_artifacts')
        if not policy or not policy.enabled:
            return {'policy': 'job_artifacts', 'status': 'disabled', 'deleted': 0}
        
        cutoff_date = timezone.now() - timedelta(days=policy.days)
        
        # For now, we'll skip artifact cleanup since we don't have a clear way to distinguish
        # job artifacts from user uploads without an artifact_type field
        # TODO: Add artifact_type field or use path/name patterns to identify job artifacts
        logger.info(f"Job artifact cleanup skipped - needs artifact_type field")
        
        return {
            'policy': 'job_artifacts',
            'status': 'not_implemented',
            'deleted': 0,
            'message': 'Job artifact cleanup requires artifact_type field',
            'dry_run': dry_run,
        }
    
    def cleanup_share_link_access_logs(self, dry_run: bool = False) -> Dict[str, Any]:
        """Clean up old share link access logs."""
        # TODO: Implement based on share link access log storage
        policy = self.get_policy('share_link_access_logs')
        if not policy or not policy.enabled:
            return {'policy': 'share_link_access_logs', 'status': 'disabled', 'deleted': 0}
        
        return {
            'policy': 'share_link_access_logs',
            'status': 'not_implemented',
            'deleted': 0,
            'message': 'Share link access log cleanup not yet implemented',
        }
    
    def cleanup_all(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Run all cleanup operations.
        
        Args:
            dry_run: If True, return counts without deleting
            
        Returns:
            List of cleanup results
        """
        results = []
        
        results.append(self.cleanup_auth_events(dry_run=dry_run))
        results.append(self.cleanup_observability_events(dry_run=dry_run))
        results.append(self.cleanup_failed_jobs(dry_run=dry_run))
        results.append(self.cleanup_job_artifacts(dry_run=dry_run))
        results.append(self.cleanup_ai_transcripts(dry_run=dry_run))
        results.append(self.cleanup_share_link_access_logs(dry_run=dry_run))
        
        return results
    
    def get_cleanup_summary(self) -> Dict[str, Any]:
        """
        Get summary of what would be cleaned up (dry run).
        
        Returns:
            Summary of cleanup operations
        """
        results = self.cleanup_all(dry_run=True)
        
        total_to_delete = sum(r['deleted'] for r in results if r['status'] == 'success')
        
        return {
            'timestamp': timezone.now().isoformat(),
            'total_records_to_delete': total_to_delete,
            'policies': results,
        }


# Global retention manager instance
retention_manager = RetentionManager()


def run_retention_cleanup(dry_run: bool = False) -> List[Dict[str, Any]]:
    """
    Run retention cleanup.
    Called by periodic task.
    
    Args:
        dry_run: If True, return counts without deleting
        
    Returns:
        List of cleanup results
    """
    return retention_manager.cleanup_all(dry_run=dry_run)
