"""
Business logic for invite passkey management.
"""
from django.utils import timezone
from django.contrib.auth.models import User
from apps.invitations.models import InvitePasskey
from apps.auditing.models import AuthEvent


def create_passkey(creator, expires_at=None, tenant_scope=None, max_uses=1, notes=''):
    """
    Create a new invite passkey.
    
    Args:
        creator: User creating the passkey
        expires_at: Optional expiration datetime
        tenant_scope: Optional tenant to limit signup to
        max_uses: Maximum number of uses (default 1)
        notes: Admin notes
    
    Returns:
        tuple: (passkey_object, raw_key_string)
    """
    raw_key = InvitePasskey.generate_key()
    hashed_key = InvitePasskey.hash_key(raw_key)
    
    passkey = InvitePasskey.objects.create(
        key=hashed_key,
        raw_key=raw_key,  # Store temporarily for display
        created_by=creator,
        expires_at=expires_at,
        tenant_scope=tenant_scope,
        max_uses=max_uses,
        notes=notes
    )
    
    # Log creation
    AuthEvent.log(
        event_type='admin_action',
        user=creator,
        details={
            'action': 'passkey_created',
            'passkey_id': passkey.id,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'tenant_scope': tenant_scope.id if tenant_scope else None
        }
    )
    
    return passkey, raw_key


def validate_passkey(raw_key, ip_address=None, user_agent=None):
    """
    Validate a passkey without consuming it.
    
    Args:
        raw_key: The plain text passkey
        ip_address: Optional IP for audit
        user_agent: Optional user agent for audit
    
    Returns:
        tuple: (is_valid, reason, passkey_object or None)
    """
    is_valid, reason, passkey = InvitePasskey.validate_key(raw_key)
    
    # Log validation attempt
    AuthEvent.log(
        event_type='passkey_validated' if is_valid else 'passkey_rejected',
        passkey=passkey if passkey else None,
        ip_address=ip_address,
        user_agent=user_agent,
        success=is_valid,
        failure_reason=reason if not is_valid else '',
        details={'raw_key_length': len(raw_key)}
    )
    
    return is_valid, reason, passkey


def consume_passkey(passkey, user, ip_address=None, user_agent=None):
    """
    Mark a passkey as used by a user.
    
    Args:
        passkey: InvitePasskey object
        user: User who used the passkey
        ip_address: Optional IP for audit
        user_agent: Optional user agent for audit
    
    Returns:
        bool: Success
    """
    try:
        passkey.consume(user)
        
        # Log consumption
        AuthEvent.log(
            event_type='passkey_consumed',
            user=user,
            passkey=passkey,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                'passkey_id': passkey.id,
                'actual_uses': passkey.actual_uses,
                'max_uses': passkey.max_uses
            }
        )
        
        return True
    except ValueError as e:
        # Log failure
        AuthEvent.log(
            event_type='passkey_rejected',
            user=user,
            passkey=passkey,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason=str(e),
            details={'passkey_id': passkey.id}
        )
        return False


def list_passkeys(creator=None, tenant_scope=None, active_only=False):
    """
    List passkeys with optional filters.
    
    Args:
        creator: Filter by creator
        tenant_scope: Filter by tenant
        active_only: Only return valid/unexpired passkeys
    
    Returns:
        QuerySet of InvitePasskey
    """
    qs = InvitePasskey.objects.all()
    
    if creator:
        qs = qs.filter(created_by=creator)
    
    if tenant_scope:
        qs = qs.filter(tenant_scope=tenant_scope)
    
    if active_only:
        now = timezone.now()
        qs = qs.filter(
            actual_uses__lt=models.F('max_uses')
        ).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )
    
    return qs.select_related('created_by', 'used_by', 'tenant_scope')
