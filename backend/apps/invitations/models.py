import secrets
import hashlib
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class InvitePasskey(models.Model):
    """
    Single-use invite passkey for controlled signup.
    """
    key = models.CharField(max_length=64, unique=True, db_index=True, help_text="Hashed passkey")
    raw_key = models.CharField(max_length=32, blank=True, help_text="Plain text key shown once at creation")
    
    # Lifecycle
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_passkeys')
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional expiration time")
    
    # Usage tracking
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='used_passkeys')
    max_uses = models.IntegerField(default=1, help_text="Maximum number of times this passkey can be used")
    actual_uses = models.IntegerField(default=0, help_text="Number of times actually used")
    
    # Tenant scoping
    tenant_scope = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, 
                                     help_text="If set, limits signup to this tenant")
    
    # Metadata
    notes = models.TextField(blank=True, help_text="Admin notes about this passkey")
    
    class Meta:
        db_table = 'invitations_passkey'
        ordering = ['-created_at']
        verbose_name = 'Invite Passkey'
        verbose_name_plural = 'Invite Passkeys'
    
    def __str__(self):
        status = "used" if self.is_used() else "active" if self.is_valid() else "expired"
        return f"Passkey {self.key[:8]}... ({status})"
    
    def is_expired(self):
        """Check if passkey has expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def is_used(self):
        """Check if passkey has been fully consumed."""
        return self.actual_uses >= self.max_uses
    
    def is_valid(self):
        """Check if passkey is currently valid for use."""
        return not self.is_expired() and not self.is_used()
    
    @staticmethod
    def generate_key():
        """Generate a random passkey."""
        return secrets.token_urlsafe(24)
    
    @staticmethod
    def hash_key(raw_key):
        """Hash a passkey for storage."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
    
    def consume(self, user):
        """Mark passkey as used by a user."""
        if not self.is_valid():
            raise ValueError("Passkey is not valid")
        
        self.actual_uses += 1
        if self.actual_uses == 1:  # First use
            self.used_at = timezone.now()
            self.used_by = user
        self.save()
    
    @classmethod
    def validate_key(cls, raw_key):
        """
        Validate a passkey and return (is_valid, reason, passkey_obj).
        """
        try:
            hashed = cls.hash_key(raw_key)
            passkey = cls.objects.get(key=hashed)
            
            if passkey.is_expired():
                return False, "Passkey has expired", passkey
            
            if passkey.is_used():
                return False, "Passkey has already been used", passkey
            
            return True, "Passkey is valid", passkey
            
        except cls.DoesNotExist:
            return False, "Invalid passkey", None
