from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from apps.invitations.models import InvitePasskey


@admin.register(InvitePasskey)
class InvitePasskeyAdmin(admin.ModelAdmin):
    list_display = ['key_preview', 'status_badge', 'created_by', 'created_at', 'expires_at', 'used_by', 'used_at', 'tenant_scope']
    list_filter = ['created_at', 'expires_at', 'tenant_scope']
    search_fields = ['key', 'notes', 'created_by__username', 'used_by__username']
    readonly_fields = ['key', 'raw_key', 'created_at', 'used_at', 'used_by', 'actual_uses']
    
    fieldsets = (
        ('Passkey Information', {
            'fields': ('key', 'raw_key', 'notes')
        }),
        ('Usage Limits', {
            'fields': ('max_uses', 'actual_uses', 'tenant_scope')
        }),
        ('Lifecycle', {
            'fields': ('created_by', 'created_at', 'expires_at', 'used_by', 'used_at')
        }),
    )
    
    def key_preview(self, obj):
        return f"{obj.key[:12]}..."
    key_preview.short_description = 'Key'
    
    def status_badge(self, obj):
        if obj.is_used():
            return format_html('<span style="color: #666;">● Used</span>')
        elif obj.is_expired():
            return format_html('<span style="color: #dc3545;">● Expired</span>')
        else:
            return format_html('<span style="color: #28a745;">● Active</span>')
    status_badge.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new passkey
            obj.created_by = request.user
            if not obj.key:  # Generate if not set
                raw_key = InvitePasskey.generate_key()
                obj.raw_key = raw_key
                obj.key = InvitePasskey.hash_key(raw_key)
        super().save_model(request, obj, form, change)
