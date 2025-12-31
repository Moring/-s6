from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class AuthEvent(models.Model):
    """
    Audit log for authentication and authorization events.
    """
    EVENT_TYPES = [
        ('login_success', 'Login Success'),
        ('login_failure', 'Login Failure'),
        ('signup_success', 'Signup Success'),
        ('signup_failure', 'Signup Failure'),
        ('logout', 'Logout'),
        ('password_change', 'Password Change'),
        ('password_reset_request', 'Password Reset Request'),
        ('password_reset_complete', 'Password Reset Complete'),
        ('passkey_validated', 'Passkey Validated'),
        ('passkey_consumed', 'Passkey Consumed'),
        ('passkey_rejected', 'Passkey Rejected'),
        ('user_disabled', 'User Disabled'),
        ('user_enabled', 'User Enabled'),
        ('tenant_changed', 'Tenant Changed'),
        ('profile_updated', 'Profile Updated'),
        ('admin_action', 'Admin Action'),
    ]
    
    # Event details
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # User information
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                            related_name='auth_events', help_text="User associated with event (if known)")
    
    # Request information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    
    # Related objects
    passkey = models.ForeignKey('invitations.InvitePasskey', on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='audit_events')
    
    # Additional context
    details = models.JSONField(default=dict, blank=True, help_text="Additional event-specific data")
    
    # Success/failure
    success = models.BooleanField(default=True)
    failure_reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'auditing_auth_event'
        ordering = ['-timestamp']
        verbose_name = 'Auth Event'
        verbose_name_plural = 'Auth Events'
        indexes = [
            models.Index(fields=['-timestamp', 'event_type']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        status = "✓" if self.success else "✗"
        return f"{status} {self.event_type} - {user_str} @ {self.timestamp:%Y-%m-%d %H:%M}"
    
    @classmethod
    def log(cls, event_type, user=None, ip_address=None, user_agent=None, 
            passkey=None, details=None, success=True, failure_reason=''):
        """
        Convenience method to create an auth event.
        """
        # Build kwargs, only including user_agent if explicitly provided
        kwargs = {
            'event_type': event_type,
            'user': user,
            'ip_address': ip_address,
            'passkey': passkey,
            'details': details or {},
            'success': success,
            'failure_reason': failure_reason
        }
        
        # Only add user_agent if it's not None (to allow model default to work)
        if user_agent is not None:
            kwargs['user_agent'] = user_agent
        
        return cls.objects.create(**kwargs)
