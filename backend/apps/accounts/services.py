"""
Business logic for user account management and authentication.
"""
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db import transaction
from apps.accounts.models import UserProfile
from apps.tenants.models import Tenant
from apps.invitations import services as invite_services
from apps.auditing.models import AuthEvent


def signup_with_passkey(username, email, password, passkey_raw, ip_address=None, user_agent=None):
    """
    Create a new user account using an invite passkey.
    
    Args:
        username: Desired username
        email: User email
        password: Password
        passkey_raw: Plain text invite passkey
        ip_address: Request IP
        user_agent: Request user agent
    
    Returns:
        tuple: (success, user_or_error_message)
    """
    # Validate passkey first
    is_valid, reason, passkey = invite_services.validate_passkey(
        passkey_raw, ip_address, user_agent
    )
    
    if not is_valid:
        AuthEvent.log(
            event_type='signup_failure',
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason=f"Invalid passkey: {reason}",
            details={'username': username, 'email': email}
        )
        return False, reason
    
    # Check if username/email already exist
    if User.objects.filter(username=username).exists():
        AuthEvent.log(
            event_type='signup_failure',
            ip_address=ip_address,
            user_agent=user_agent,
            passkey=passkey,
            success=False,
            failure_reason="Username already exists",
            details={'username': username}
        )
        return False, "Username already exists"
    
    if User.objects.filter(email=email).exists():
        AuthEvent.log(
            event_type='signup_failure',
            ip_address=ip_address,
            user_agent=user_agent,
            passkey=passkey,
            success=False,
            failure_reason="Email already exists",
            details={'email': email}
        )
        return False, "Email already exists"
    
    # Create user, tenant, and profile in transaction
    try:
        with transaction.atomic():
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Tenant and profile are created by signals
            # But we need to ensure tenant scope matches if set
            user.refresh_from_db()
            
            if passkey.tenant_scope:
                # Move user to specified tenant
                user.profile.tenant = passkey.tenant_scope
                user.profile.save()
            
            # Consume passkey
            invite_services.consume_passkey(passkey, user, ip_address, user_agent)
            
            # Log success
            AuthEvent.log(
                event_type='signup_success',
                user=user,
                passkey=passkey,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    'username': username,
                    'email': email,
                    'tenant': user.profile.tenant.name
                }
            )
            
            return True, user
            
    except Exception as e:
        AuthEvent.log(
            event_type='signup_failure',
            ip_address=ip_address,
            user_agent=user_agent,
            passkey=passkey,
            success=False,
            failure_reason=str(e),
            details={'username': username, 'email': email}
        )
        return False, f"Signup failed: {str(e)}"


def authenticate_user(username, password, ip_address=None, user_agent=None):
    """
    Authenticate a user and log the attempt.
    
    Args:
        username: Username or email
        password: Password
        ip_address: Request IP
        user_agent: Request user agent
    
    Returns:
        tuple: (success, user_or_error_message)
    """
    user = authenticate(username=username, password=password)
    
    if user is not None:
        if user.is_active:
            AuthEvent.log(
                event_type='login_success',
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                details={'username': username}
            )
            return True, user
        else:
            AuthEvent.log(
                event_type='login_failure',
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason="Account is disabled",
                details={'username': username}
            )
            return False, "Account is disabled"
    else:
        AuthEvent.log(
            event_type='login_failure',
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason="Invalid credentials",
            details={'username': username}
        )
        return False, "Invalid username or password"


def log_logout(user, ip_address=None, user_agent=None):
    """Log a logout event."""
    AuthEvent.log(
        event_type='logout',
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        details={'username': user.username}
    )


def log_password_change(user, ip_address=None, user_agent=None):
    """Log a password change event."""
    AuthEvent.log(
        event_type='password_change',
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        details={'username': user.username}
    )


def log_password_reset_request(email, ip_address=None, user_agent=None):
    """Log a password reset request."""
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        user = None
    
    AuthEvent.log(
        event_type='password_reset_request',
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        details={'email': email}
    )


def log_password_reset_complete(user, ip_address=None, user_agent=None):
    """Log a password reset completion."""
    AuthEvent.log(
        event_type='password_reset_complete',
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        details={'username': user.username}
    )


def disable_user(user, admin_user, reason='', ip_address=None):
    """Disable a user account."""
    user.is_active = False
    user.save()
    
    AuthEvent.log(
        event_type='user_disabled',
        user=admin_user,
        ip_address=ip_address,
        details={
            'target_user': user.username,
            'reason': reason
        }
    )


def enable_user(user, admin_user, ip_address=None):
    """Enable a user account."""
    user.is_active = True
    user.save()
    
    AuthEvent.log(
        event_type='user_enabled',
        user=admin_user,
        ip_address=ip_address,
        details={'target_user': user.username}
    )


def change_user_tenant(user, new_tenant, admin_user, ip_address=None):
    """Move a user to a different tenant."""
    old_tenant = user.profile.tenant
    user.profile.tenant = new_tenant
    user.profile.save()
    
    AuthEvent.log(
        event_type='tenant_changed',
        user=admin_user,
        ip_address=ip_address,
        details={
            'target_user': user.username,
            'old_tenant': old_tenant.name,
            'new_tenant': new_tenant.name
        }
    )
