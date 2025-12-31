"""
Tenant role model and permission system.
Centralized authorization for multi-tenant operations.
"""
from enum import Enum
from typing import Optional
from django.contrib.auth.models import User


class TenantRole(str, Enum):
    """Tenant role definitions."""
    OWNER = 'owner'
    ADMIN = 'admin'
    MEMBER = 'member'
    READ_ONLY = 'read_only'
    
    @classmethod
    def choices(cls):
        return [(role.value, role.name.replace('_', ' ').title()) for role in cls]


class Permission(str, Enum):
    """Permission definitions."""
    # Tenant management
    MANAGE_TENANT = 'manage_tenant'
    VIEW_TENANT = 'view_tenant'
    
    # User management
    MANAGE_USERS = 'manage_users'
    VIEW_USERS = 'view_users'
    
    # Worklog operations
    CREATE_WORKLOG = 'create_worklog'
    EDIT_WORKLOG = 'edit_worklog'
    DELETE_WORKLOG = 'delete_worklog'
    VIEW_WORKLOG = 'view_worklog'
    
    # Skill operations
    MANAGE_SKILLS = 'manage_skills'
    VIEW_SKILLS = 'view_skills'
    
    # Report operations
    GENERATE_REPORT = 'generate_report'
    VIEW_REPORT = 'view_report'
    DELETE_REPORT = 'delete_report'
    
    # Job operations
    TRIGGER_JOB = 'trigger_job'
    VIEW_JOB = 'view_job'
    CANCEL_JOB = 'cancel_job'
    
    # Billing operations
    VIEW_BILLING = 'view_billing'
    MANAGE_BILLING = 'manage_billing'
    
    # Share link operations
    CREATE_SHARE_LINK = 'create_share_link'
    MANAGE_SHARE_LINK = 'manage_share_link'
    VIEW_SHARE_LINK = 'view_share_link'
    
    # Export operations
    EXPORT_DATA = 'export_data'
    
    # System operations
    VIEW_AUDIT_LOG = 'view_audit_log'
    VIEW_SYSTEM_METRICS = 'view_system_metrics'


# Role to permissions mapping
ROLE_PERMISSIONS = {
    TenantRole.OWNER: [
        # All permissions
        Permission.MANAGE_TENANT,
        Permission.VIEW_TENANT,
        Permission.MANAGE_USERS,
        Permission.VIEW_USERS,
        Permission.CREATE_WORKLOG,
        Permission.EDIT_WORKLOG,
        Permission.DELETE_WORKLOG,
        Permission.VIEW_WORKLOG,
        Permission.MANAGE_SKILLS,
        Permission.VIEW_SKILLS,
        Permission.GENERATE_REPORT,
        Permission.VIEW_REPORT,
        Permission.DELETE_REPORT,
        Permission.TRIGGER_JOB,
        Permission.VIEW_JOB,
        Permission.CANCEL_JOB,
        Permission.VIEW_BILLING,
        Permission.MANAGE_BILLING,
        Permission.CREATE_SHARE_LINK,
        Permission.MANAGE_SHARE_LINK,
        Permission.VIEW_SHARE_LINK,
        Permission.EXPORT_DATA,
        Permission.VIEW_AUDIT_LOG,
        Permission.VIEW_SYSTEM_METRICS,
    ],
    TenantRole.ADMIN: [
        # Most permissions except tenant management
        Permission.VIEW_TENANT,
        Permission.MANAGE_USERS,
        Permission.VIEW_USERS,
        Permission.CREATE_WORKLOG,
        Permission.EDIT_WORKLOG,
        Permission.DELETE_WORKLOG,
        Permission.VIEW_WORKLOG,
        Permission.MANAGE_SKILLS,
        Permission.VIEW_SKILLS,
        Permission.GENERATE_REPORT,
        Permission.VIEW_REPORT,
        Permission.DELETE_REPORT,
        Permission.TRIGGER_JOB,
        Permission.VIEW_JOB,
        Permission.CANCEL_JOB,
        Permission.VIEW_BILLING,
        Permission.CREATE_SHARE_LINK,
        Permission.MANAGE_SHARE_LINK,
        Permission.VIEW_SHARE_LINK,
        Permission.EXPORT_DATA,
        Permission.VIEW_AUDIT_LOG,
    ],
    TenantRole.MEMBER: [
        # Standard user permissions
        Permission.VIEW_TENANT,
        Permission.CREATE_WORKLOG,
        Permission.EDIT_WORKLOG,
        Permission.DELETE_WORKLOG,
        Permission.VIEW_WORKLOG,
        Permission.VIEW_SKILLS,
        Permission.GENERATE_REPORT,
        Permission.VIEW_REPORT,
        Permission.DELETE_REPORT,
        Permission.TRIGGER_JOB,
        Permission.VIEW_JOB,
        Permission.VIEW_BILLING,
        Permission.CREATE_SHARE_LINK,
        Permission.VIEW_SHARE_LINK,
        Permission.EXPORT_DATA,
    ],
    TenantRole.READ_ONLY: [
        # View-only permissions
        Permission.VIEW_TENANT,
        Permission.VIEW_WORKLOG,
        Permission.VIEW_SKILLS,
        Permission.VIEW_REPORT,
        Permission.VIEW_JOB,
        Permission.VIEW_BILLING,
        Permission.VIEW_SHARE_LINK,
    ],
}


def get_user_role(user: User, tenant) -> Optional[TenantRole]:
    """
    Get user's role in a tenant.
    
    Args:
        user: Django user
        tenant: Tenant instance
    
    Returns:
        TenantRole or None if no membership
    """
    if not user or not user.is_authenticated:
        return None
    
    # Check if user is tenant owner
    if hasattr(tenant, 'owner') and tenant.owner == user:
        return TenantRole.OWNER
    
    # Check TenantMembership if exists
    try:
        from apps.tenants.models import TenantMembership
        membership = TenantMembership.objects.filter(
            tenant=tenant,
            user=user,
            is_active=True
        ).first()
        if membership:
            return TenantRole(membership.role)
    except (ImportError, Exception):
        pass
    
    # Fallback: if user has profile in tenant, treat as MEMBER
    if hasattr(user, 'profile') and user.profile.tenant == tenant:
        return TenantRole.MEMBER
    
    return None


def has_permission(user: User, tenant, permission: Permission) -> bool:
    """
    Check if user has permission in tenant.
    
    Args:
        user: Django user
        tenant: Tenant instance
        permission: Permission to check
    
    Returns:
        bool: True if user has permission
    """
    # Super users have all permissions
    if user and user.is_superuser:
        return True
    
    # Staff users have view permissions for system dashboards
    if user and user.is_staff and permission in [
        Permission.VIEW_SYSTEM_METRICS,
        Permission.VIEW_AUDIT_LOG,
    ]:
        return True
    
    role = get_user_role(user, tenant)
    if not role:
        return False
    
    return permission in ROLE_PERMISSIONS.get(role, [])


def require_permission(permission: Permission):
    """
    Decorator to enforce permission on views.
    
    Usage:
        @require_permission(Permission.MANAGE_USERS)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            from django.http import JsonResponse
            from django.core.exceptions import PermissionDenied
            
            # Get tenant from request
            tenant = getattr(request, 'tenant', None)
            if not tenant and hasattr(request.user, 'profile'):
                tenant = request.user.profile.tenant
            
            if not has_permission(request.user, tenant, permission):
                if request.content_type == 'application/json':
                    return JsonResponse({'error': 'Permission denied'}, status=403)
                raise PermissionDenied('You do not have permission to perform this action')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
