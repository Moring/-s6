"""
Admin audit log viewer with filters and tenant management.
Provides governance surfaces for admin operations.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
import logging

logger = logging.getLogger(__name__)


class AuditLogViewer:
    """
    Admin viewer for audit logs with filtering capabilities.
    """
    
    def __init__(self, requesting_user: User):
        """
        Initialize audit log viewer.
        
        Args:
            requesting_user: Admin user viewing logs
        """
        if not requesting_user.is_staff:
            raise PermissionError("Only staff users can view audit logs")
        
        self.requesting_user = requesting_user
    
    def get_auth_events(
        self,
        user: Optional[User] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        success: Optional[bool] = None,
        ip_address: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Get auth events with filters.
        
        Args:
            user: Filter by user
            event_type: Filter by event type
            start_date: Filter by start date
            end_date: Filter by end date
            success: Filter by success/failure
            ip_address: Filter by IP address
            page: Page number
            per_page: Results per page
            
        Returns:
            Paginated audit log results
        """
        from apps.auditing.models import AuthEvent
        
        # Build query
        query = Q()
        
        if user:
            query &= Q(user=user)
        
        if event_type:
            query &= Q(event_type=event_type)
        
        if start_date:
            query &= Q(timestamp__gte=start_date)
        
        if end_date:
            query &= Q(timestamp__lte=end_date)
        
        if success is not None:
            query &= Q(success=success)
        
        if ip_address:
            query &= Q(ip_address=ip_address)
        
        # Get events
        events = AuthEvent.objects.filter(query).order_by('-timestamp')
        
        # Paginate
        paginator = Paginator(events, per_page)
        page_obj = paginator.get_page(page)
        
        return {
            'events': [
                {
                    'id': event.id,
                    'event_type': event.event_type,
                    'timestamp': event.timestamp.isoformat(),
                    'user': event.user.username if event.user else None,
                    'user_id': event.user.id if event.user else None,
                    'ip_address': event.ip_address,
                    'user_agent': event.user_agent,
                    'success': event.success,
                    'failure_reason': event.failure_reason,
                    'details': event.details,
                }
                for event in page_obj
            ],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginator.count,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            },
            'filters': {
                'user': user.username if user else None,
                'event_type': event_type,
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'success': success,
                'ip_address': ip_address,
            },
        }
    
    def get_admin_actions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        admin_user: Optional[User] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Get admin-specific actions.
        
        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            admin_user: Filter by admin user
            page: Page number
            per_page: Results per page
            
        Returns:
            Paginated admin action results
        """
        from apps.auditing.models import AuthEvent
        
        query = Q(event_type='admin_action')
        
        if start_date:
            query &= Q(timestamp__gte=start_date)
        
        if end_date:
            query &= Q(timestamp__lte=end_date)
        
        if admin_user:
            query &= Q(user=admin_user)
        
        events = AuthEvent.objects.filter(query).order_by('-timestamp')
        
        paginator = Paginator(events, per_page)
        page_obj = paginator.get_page(page)
        
        return {
            'actions': [
                {
                    'id': event.id,
                    'timestamp': event.timestamp.isoformat(),
                    'admin_user': event.user.username if event.user else None,
                    'action': event.details.get('action', 'unknown'),
                    'target': event.details.get('target_user_id', event.details.get('target_username')),
                    'details': event.details,
                    'success': event.success,
                }
                for event in page_obj
            ],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginator.count,
                'pages': paginator.num_pages,
            },
        }
    
    def get_event_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get summary of events for the last N days.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Event summary statistics
        """
        from apps.auditing.models import AuthEvent
        
        start_date = timezone.now() - timedelta(days=days)
        
        total_events = AuthEvent.objects.filter(timestamp__gte=start_date).count()
        failed_events = AuthEvent.objects.filter(
            timestamp__gte=start_date,
            success=False
        ).count()
        
        # Group by event type
        by_type = AuthEvent.objects.filter(
            timestamp__gte=start_date
        ).values('event_type').annotate(count=Count('id')).order_by('-count')
        
        # Failed logins
        failed_logins = AuthEvent.objects.filter(
            timestamp__gte=start_date,
            event_type='login_failure'
        ).count()
        
        return {
            'period_days': days,
            'start_date': start_date.isoformat(),
            'total_events': total_events,
            'failed_events': failed_events,
            'failed_logins': failed_logins,
            'by_type': [
                {'event_type': item['event_type'], 'count': item['count']}
                for item in by_type
            ],
        }


class TenantManager:
    """
    Admin tenant management interface.
    """
    
    def __init__(self, requesting_user: User):
        """
        Initialize tenant manager.
        
        Args:
            requesting_user: Admin user
        """
        if not requesting_user.is_staff:
            raise PermissionError("Only staff users can manage tenants")
        
        self.requesting_user = requesting_user
    
    def list_tenants(
        self,
        is_active: Optional[bool] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """
        List all tenants with filtering.
        
        Args:
            is_active: Filter by active status
            page: Page number
            per_page: Results per page
            
        Returns:
            Paginated tenant list
        """
        from apps.tenants.models import Tenant
        
        query = Q()
        if is_active is not None:
            query &= Q(is_active=is_active)
        
        tenants = Tenant.objects.filter(query).order_by('-created_at')
        
        paginator = Paginator(tenants, per_page)
        page_obj = paginator.get_page(page)
        
        return {
            'tenants': [
                {
                    'id': tenant.id,
                    'name': tenant.name,
                    'owner': tenant.owner.username,
                    'owner_id': tenant.owner.id,
                    'is_active': tenant.is_active if hasattr(tenant, 'is_active') else True,
                    'created_at': tenant.created_at.isoformat(),
                    'member_count': tenant.members.count(),
                    'plan': getattr(tenant, 'plan', 'free'),
                }
                for tenant in page_obj
            ],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginator.count,
                'pages': paginator.num_pages,
            },
        }
    
    def get_tenant_detail(self, tenant_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Tenant details
        """
        from apps.tenants.models import Tenant, TenantMembership
        from apps.tenants.quotas import QuotaManager
        
        tenant = Tenant.objects.get(id=tenant_id)
        
        # Get members
        memberships = TenantMembership.objects.filter(tenant=tenant)
        
        # Get quota info
        quota_manager = QuotaManager(tenant)
        
        # Get usage stats
        from apps.worklog.models import WorklogEntry
        from apps.artifacts.models import Artifact
        from apps.jobs.models import Job
        
        worklog_count = WorklogEntry.objects.filter(tenant=tenant).count()
        artifact_count = Artifact.objects.filter(tenant=tenant).count()
        job_count = Job.objects.filter(tenant=tenant).count()
        
        return {
            'id': tenant.id,
            'name': tenant.name,
            'owner': {
                'id': tenant.owner.id,
                'username': tenant.owner.username,
                'email': tenant.owner.email,
            },
            'is_active': getattr(tenant, 'is_active', True),
            'plan': getattr(tenant, 'plan', 'free'),
            'created_at': tenant.created_at.isoformat(),
            'members': [
                {
                    'user_id': m.user.id,
                    'username': m.user.username,
                    'role': m.role,
                    'joined_at': m.joined_at.isoformat(),
                }
                for m in memberships
            ],
            'quotas': {
                name: {
                    'limit': quota.limit,
                    'window_hours': quota.window_hours,
                    'description': quota.description,
                }
                for name, quota in quota_manager.quotas.items()
            },
            'usage': {
                'worklog_entries': worklog_count,
                'artifacts': artifact_count,
                'jobs': job_count,
            },
        }
    
    def create_tenant(self, name: str, owner_username: str, plan: str = 'free') -> Dict[str, Any]:
        """
        Create a new tenant (admin action).
        
        Args:
            name: Tenant name
            owner_username: Username of tenant owner
            plan: Tenant plan
            
        Returns:
            Created tenant details
        """
        from apps.tenants.models import Tenant
        from apps.auditing.models import AuthEvent
        
        owner = User.objects.get(username=owner_username)
        
        tenant = Tenant.objects.create(
            name=name,
            owner=owner,
        )
        
        if hasattr(tenant, 'plan'):
            tenant.plan = plan
            tenant.save()
        
        # Log admin action
        AuthEvent.log(
            event_type='admin_action',
            user=self.requesting_user,
            details={
                'action': 'tenant_created',
                'tenant_id': tenant.id,
                'tenant_name': name,
                'owner_username': owner_username,
                'plan': plan,
            },
            success=True
        )
        
        logger.info(f"Admin {self.requesting_user.username} created tenant {tenant.id}")
        
        return {
            'id': tenant.id,
            'name': tenant.name,
            'owner': owner.username,
            'plan': plan,
            'created_at': tenant.created_at.isoformat(),
        }
    
    def update_tenant_plan(self, tenant_id: int, plan: str) -> Dict[str, Any]:
        """
        Update tenant plan (admin action).
        
        Args:
            tenant_id: Tenant ID
            plan: New plan
            
        Returns:
            Updated tenant details
        """
        from apps.tenants.models import Tenant
        from apps.auditing.models import AuthEvent
        
        tenant = Tenant.objects.get(id=tenant_id)
        old_plan = getattr(tenant, 'plan', 'free')
        
        if hasattr(tenant, 'plan'):
            tenant.plan = plan
            tenant.save()
        
        # Log admin action
        AuthEvent.log(
            event_type='admin_action',
            user=self.requesting_user,
            details={
                'action': 'tenant_plan_updated',
                'tenant_id': tenant_id,
                'old_plan': old_plan,
                'new_plan': plan,
            },
            success=True
        )
        
        logger.info(
            f"Admin {self.requesting_user.username} updated tenant {tenant_id} "
            f"plan from {old_plan} to {plan}"
        )
        
        return {
            'id': tenant.id,
            'name': tenant.name,
            'old_plan': old_plan,
            'new_plan': plan,
        }
    
    def update_tenant_quotas(self, tenant_id: int, quotas: Dict[str, int]) -> Dict[str, Any]:
        """
        Update tenant quotas (admin action).
        
        Args:
            tenant_id: Tenant ID
            quotas: Dictionary of quota name -> limit
            
        Returns:
            Updated quota details
        """
        from apps.tenants.models import Tenant
        from apps.tenants.quotas import QuotaManager
        from apps.auditing.models import AuthEvent
        
        tenant = Tenant.objects.get(id=tenant_id)
        quota_manager = QuotaManager(tenant)
        
        old_quotas = {
            name: quota.limit
            for name, quota in quota_manager.quotas.items()
        }
        
        # Update quotas
        for quota_name, limit in quotas.items():
            if quota_name in quota_manager.quotas:
                quota_manager.quotas[quota_name].limit = limit
        
        # Log admin action
        AuthEvent.log(
            event_type='admin_action',
            user=self.requesting_user,
            details={
                'action': 'tenant_quotas_updated',
                'tenant_id': tenant_id,
                'old_quotas': old_quotas,
                'new_quotas': quotas,
            },
            success=True
        )
        
        logger.info(
            f"Admin {self.requesting_user.username} updated quotas for tenant {tenant_id}"
        )
        
        return {
            'tenant_id': tenant_id,
            'tenant_name': tenant.name,
            'updated_quotas': quotas,
        }
    
    def disable_tenant(self, tenant_id: int, reason: str) -> Dict[str, Any]:
        """
        Disable a tenant (admin action).
        
        Args:
            tenant_id: Tenant ID
            reason: Reason for disabling
            
        Returns:
            Disabled tenant details
        """
        from apps.tenants.models import Tenant
        from apps.auditing.models import AuthEvent
        
        tenant = Tenant.objects.get(id=tenant_id)
        
        if hasattr(tenant, 'is_active'):
            tenant.is_active = False
            tenant.save()
        
        # Log admin action
        AuthEvent.log(
            event_type='admin_action',
            user=self.requesting_user,
            details={
                'action': 'tenant_disabled',
                'tenant_id': tenant_id,
                'tenant_name': tenant.name,
                'reason': reason,
            },
            success=True
        )
        
        logger.warning(
            f"Admin {self.requesting_user.username} disabled tenant {tenant_id}: {reason}"
        )
        
        return {
            'tenant_id': tenant_id,
            'tenant_name': tenant.name,
            'is_active': False,
            'reason': reason,
        }
