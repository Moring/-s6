"""
Data export system for user data portability.
Enables users to export all their data in safe formats.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone


class DataExportFormat:
    """Supported export formats."""
    JSON = 'json'
    CSV = 'csv'
    
    CHOICES = [
        (JSON, 'JSON'),
        (CSV, 'CSV'),
    ]


class DataExporter:
    """
    Base class for exporting tenant-scoped data.
    Ensures data is properly scoped and redacted.
    """
    
    def __init__(self, user: User, tenant=None):
        """
        Initialize exporter for a user.
        
        Args:
            user: User requesting export
            tenant: Specific tenant to export (defaults to user's primary tenant)
        """
        self.user = user
        
        # Get tenant
        if tenant:
            self.tenant = tenant
        else:
            from apps.tenants.models import Tenant
            self.tenant = Tenant.objects.filter(
                Q(owner=user) | Q(members=user)
            ).first()
        
        if not self.tenant:
            raise ValueError(f"No tenant found for user {user.username}")
    
    def export_all(self, format: str = DataExportFormat.JSON) -> Dict[str, Any]:
        """
        Export all user data across all categories.
        
        Returns:
            Dictionary with all exported data
        """
        export_data = {
            'export_metadata': self._get_export_metadata(),
            'user_profile': self._export_user_profile(),
            'worklog': self._export_worklog(),
            'skills': self._export_skills(),
            'documents': self._export_documents(),
            'reports': self._export_reports(),
            'billing': self._export_billing(),
        }
        
        return export_data
    
    def _get_export_metadata(self) -> Dict[str, Any]:
        """Get export metadata."""
        return {
            'export_date': timezone.now().isoformat(),
            'user_id': self.user.id,
            'username': self.user.username,
            'tenant_id': self.tenant.id,
            'tenant_name': self.tenant.name,
            'format': 'json',
            'version': '1.0',
        }
    
    def _export_user_profile(self) -> Dict[str, Any]:
        """Export user profile data."""
        return {
            'username': self.user.username,
            'email': self.user.email,
            'date_joined': self.user.date_joined.isoformat(),
            'is_active': self.user.is_active,
            'tenant_role': self._get_user_tenant_role(),
        }
    
    def _get_user_tenant_role(self) -> str:
        """Get user's role in tenant."""
        from apps.tenants.models import TenantMembership
        
        if self.tenant.owner == self.user:
            return 'owner'
        
        membership = TenantMembership.objects.filter(
            tenant=self.tenant,
            user=self.user
        ).first()
        
        if membership:
            return membership.role
        
        return 'none'
    
    def _export_worklog(self) -> List[Dict[str, Any]]:
        """Export worklog entries."""
        from apps.worklog.models import WorkLog
        
        entries = WorkLog.objects.filter(
            user=self.user
        ).order_by('-date')
        
        return [
            {
                'id': entry.id,
                'date': entry.date.isoformat(),
                'content': entry.content,
                'source': entry.source,
                'metadata': entry.metadata,
                'created_at': entry.created_at.isoformat(),
                'updated_at': entry.updated_at.isoformat(),
            }
            for entry in entries
        ]
    
    def _export_skills(self) -> List[Dict[str, Any]]:
        """Export skills data."""
        from apps.skills.models import Skill
        
        skills = Skill.objects.filter(
            user=self.user
        ).order_by('normalized')
        
        return [
            {
                'id': skill.id,
                'name': skill.name,
                'normalized': skill.normalized,
                'confidence': skill.confidence,
                'level': skill.level,
                'metadata': skill.metadata,
                'created_at': skill.created_at.isoformat(),
                'updated_at': skill.updated_at.isoformat(),
            }
            for skill in skills
        ]
    
    def _export_documents(self) -> List[Dict[str, Any]]:
        """Export document metadata (not file contents)."""
        from apps.artifacts.models import Artifact
        
        artifacts = Artifact.objects.filter(
            tenant=self.tenant
        ).order_by('-created_at')
        
        return [
            {
                'id': artifact.id,
                'filename': artifact.filename,
                'file_type': artifact.file_type,
                'file_size': artifact.file_size,
                'storage_key': artifact.storage_key,
                'created_at': artifact.created_at.isoformat(),
                'uploaded_by': artifact.uploaded_by.username if artifact.uploaded_by else None,
                # Note: Actual file content not included in export
                # Users can download files separately via UI
            }
            for artifact in artifacts
        ]
    
    def _export_reports(self) -> List[Dict[str, Any]]:
        """Export generated reports."""
        from apps.reporting.models import Report
        
        reports = Report.objects.filter(
            user=self.user
        ).order_by('-created_at')
        
        return [
            {
                'id': report.id,
                'kind': report.kind,
                'content': report.content,
                'rendered_text': report.rendered_text,
                'rendered_html': report.rendered_html,
                'metadata': report.metadata,
                'created_at': report.created_at.isoformat(),
                'updated_at': report.updated_at.isoformat(),
            }
            for report in reports
        ]
    
    def _export_billing(self) -> Dict[str, Any]:
        """Export billing data."""
        from apps.billing.models import ReserveLedgerEntry
        
        ledger_entries = ReserveLedgerEntry.objects.filter(
            tenant=self.tenant
        ).order_by('-created_at')
        
        return {
            'ledger_entries': [
                {
                    'created_at': entry.created_at.isoformat(),
                    'entry_type': entry.entry_type,
                    'amount_cents': entry.amount_cents,
                    'balance_after_cents': entry.balance_after_cents,
                    'notes': entry.notes,
                }
                for entry in ledger_entries
            ],
        }
    
    def export_to_file(self, output_path: str, format: str = DataExportFormat.JSON):
        """
        Export data to a file.
        
        Args:
            output_path: Path to write export file
            format: Export format (json or csv)
        """
        data = self.export_all(format=format)
        
        if format == DataExportFormat.JSON:
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        elif format == DataExportFormat.CSV:
            # CSV export would require separate files for each category
            raise NotImplementedError("CSV export not yet implemented")
        else:
            raise ValueError(f"Unsupported format: {format}")


class ExportRequest:
    """
    Manages data export requests.
    Tracks export status and provides download links.
    """
    
    @staticmethod
    def create_export_request(user: User, tenant=None) -> Dict[str, Any]:
        """
        Create a new export request.
        
        Returns:
            Export request metadata
        """
        from apps.jobs.dispatcher import enqueue
        
        # Enqueue export job
        job = enqueue(
            'system.data_export',
            {
                'user_id': user.id,
                'tenant_id': tenant.id if tenant else None,
            },
            user=user
        )
        
        return {
            'job_id': job.id,
            'status': job.status,
            'created_at': job.created_at.isoformat(),
            'message': 'Export request created. You will be notified when ready.',
        }
    
    @staticmethod
    def get_export_status(job_id: int) -> Dict[str, Any]:
        """Get status of an export request."""
        from apps.jobs.models import Job
        
        job = Job.objects.get(id=job_id)
        
        result = {
            'job_id': job.id,
            'status': job.status,
            'created_at': job.created_at.isoformat(),
        }
        
        if job.status == 'completed':
            result['download_url'] = f'/api/exports/{job.id}/download'
            result['expires_at'] = (job.completed_at + timezone.timedelta(days=7)).isoformat()
        elif job.status == 'failed':
            result['error'] = job.error
        
        return result
