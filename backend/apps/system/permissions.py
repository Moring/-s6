"""
System dashboard permissions.
"""
from rest_framework import permissions
from django.conf import settings


class IsStaffOrSystemEnabled(permissions.BasePermission):
    """Allow staff or if system dashboard is enabled in DEBUG mode."""
    
    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
        
        # Allow in dev if system dashboard is enabled
        if settings.DEBUG and settings.SYSTEM_DASHBOARD_ENABLED:
            return True
        
        return False
