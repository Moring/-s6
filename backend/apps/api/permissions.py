"""
API permissions.
"""
from rest_framework import permissions


class IsOwnerOrStaff(permissions.BasePermission):
    """Allow access to object owner or staff."""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False
