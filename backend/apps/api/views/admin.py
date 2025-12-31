"""
API views for admin operations.
Staff-only endpoints.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from apps.invitations import services as invite_services
from apps.invitations.serializers import InvitePasskeySerializer, PasskeyCreateSerializer
from apps.invitations.models import InvitePasskey
from apps.accounts.serializers import UserSerializer
from apps.accounts import services as account_services
from apps.auditing.models import AuthEvent
from apps.auditing.serializers import AuthEventSerializer
from apps.tenants.models import Tenant


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_passkey(request):
    """
    Create a new invite passkey.
    
    POST /api/admin/passkeys/
    Body: {expires_at, tenant_scope, max_uses, notes}
    """
    serializer = PasskeyCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Get tenant if specified
    tenant_scope = None
    if data.get('tenant_scope'):
        try:
            tenant_scope = Tenant.objects.get(id=data['tenant_scope'])
        except Tenant.DoesNotExist:
            return Response({
                'error': 'Tenant not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    passkey, raw_key = invite_services.create_passkey(
        creator=request.user,
        expires_at=data.get('expires_at'),
        tenant_scope=tenant_scope,
        max_uses=data.get('max_uses', 1),
        notes=data.get('notes', '')
    )
    
    result_serializer = InvitePasskeySerializer(passkey)
    return Response({
        'message': 'Passkey created successfully',
        'passkey': result_serializer.data,
        'raw_key': raw_key  # Only returned once at creation
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_passkeys(request):
    """
    List passkeys with optional filters.
    
    GET /api/admin/passkeys/?active_only=true&tenant_scope=1
    """
    active_only = request.GET.get('active_only', 'false').lower() == 'true'
    tenant_scope_id = request.GET.get('tenant_scope')
    
    tenant_scope = None
    if tenant_scope_id:
        try:
            tenant_scope = Tenant.objects.get(id=tenant_scope_id)
        except Tenant.DoesNotExist:
            pass
    
    passkeys = invite_services.list_passkeys(
        creator=None,  # Can filter by creator if needed
        tenant_scope=tenant_scope,
        active_only=active_only
    )
    
    serializer = InvitePasskeySerializer(passkeys, many=True)
    return Response({
        'count': passkeys.count(),
        'passkeys': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_users(request):
    """
    List users with optional search.
    
    GET /api/admin/users/?search=username&is_active=true
    """
    search = request.GET.get('search', '')
    is_active = request.GET.get('is_active')
    
    users = User.objects.all()
    
    if search:
        users = users.filter(
            username__icontains=search
        ) | users.filter(
            email__icontains=search
        )
    
    if is_active is not None:
        users = users.filter(is_active=is_active.lower() == 'true')
    
    users = users.select_related('profile', 'profile__tenant')
    
    serializer = UserSerializer(users, many=True)
    return Response({
        'count': users.count(),
        'users': serializer.data
    })


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def update_user(request, user_id):
    """
    Update user account (enable/disable, tenant change, profile updates).
    
    PATCH /api/admin/users/{id}/
    Body: {is_active, tenant_id, stripe_customer_id, settings, notes}
    """
    user = get_object_or_404(User, id=user_id)
    ip_address = get_client_ip(request)
    
    # Handle is_active change
    if 'is_active' in request.data:
        new_active = request.data['is_active']
        if new_active != user.is_active:
            if new_active:
                account_services.enable_user(user, request.user, ip_address)
            else:
                reason = request.data.get('disable_reason', '')
                account_services.disable_user(user, request.user, reason, ip_address)
    
    # Handle tenant change
    if 'tenant_id' in request.data:
        try:
            new_tenant = Tenant.objects.get(id=request.data['tenant_id'])
            if new_tenant != user.profile.tenant:
                account_services.change_user_tenant(user, new_tenant, request.user, ip_address)
        except Tenant.DoesNotExist:
            return Response({
                'error': 'Tenant not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    # Handle profile updates
    profile = user.profile
    profile_updated = False
    
    if 'stripe_customer_id' in request.data:
        profile.stripe_customer_id = request.data['stripe_customer_id']
        profile_updated = True
    
    if 'settings' in request.data:
        profile.settings = request.data['settings']
        profile_updated = True
    
    if 'notes' in request.data:
        profile.notes = request.data['notes']
        profile_updated = True
    
    if profile_updated:
        profile.save()
        AuthEvent.log(
            event_type='profile_updated',
            user=request.user,
            ip_address=ip_address,
            details={
                'target_user': user.username,
                'updated_fields': list(request.data.keys())
            }
        )
    
    serializer = UserSerializer(user)
    return Response({
        'message': 'User updated successfully',
        'user': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_audit_events(request):
    """
    List audit events with filters.
    
    GET /api/admin/audit-events/?user_id=1&event_type=login_success&limit=50
    """
    user_id = request.GET.get('user_id')
    event_type = request.GET.get('event_type')
    limit = int(request.GET.get('limit', 100))
    
    events = AuthEvent.objects.all()
    
    if user_id:
        events = events.filter(user_id=user_id)
    
    if event_type:
        events = events.filter(event_type=event_type)
    
    events = events.select_related('user', 'passkey')[:limit]
    
    serializer = AuthEventSerializer(events, many=True)
    return Response({
        'count': events.count(),
        'events': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_reset_password(request, user_id):
    """
    Admin-initiated password reset.
    
    POST /api/admin/users/{id}/reset-password/
    Body: {new_password}
    """
    user = get_object_or_404(User, id=user_id)
    new_password = request.data.get('new_password')
    
    if not new_password:
        return Response({
            'error': 'new_password is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user.set_password(new_password)
    user.save()
    
    ip_address = get_client_ip(request)
    AuthEvent.log(
        event_type='admin_action',
        user=request.user,
        ip_address=ip_address,
        details={
            'action': 'password_reset',
            'target_user': user.username
        }
    )
    
    return Response({'message': 'Password reset successfully'})
