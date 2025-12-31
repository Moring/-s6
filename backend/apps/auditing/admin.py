from django.contrib import admin
from django.utils.html import format_html
from apps.auditing.models import AuthEvent


@admin.register(AuthEvent)
class AuthEventAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'event_type', 'success_badge', 'user', 'ip_address', 'passkey_preview']
    list_filter = ['event_type', 'success', 'timestamp']
    search_fields = ['user__username', 'ip_address', 'user_agent', 'failure_reason']
    readonly_fields = ['timestamp', 'event_type', 'user', 'ip_address', 'user_agent', 'passkey', 'details', 'success', 'failure_reason']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False  # Events are created programmatically only
    
    def has_change_permission(self, request, obj=None):
        return False  # Events are immutable
    
    def success_badge(self, obj):
        if obj.success:
            return format_html('<span style="color: #28a745;">✓</span>')
        else:
            return format_html('<span style="color: #dc3545;">✗</span>')
    success_badge.short_description = 'Status'
    
    def passkey_preview(self, obj):
        if obj.passkey:
            return f"{obj.passkey.key[:8]}..."
        return "-"
    passkey_preview.short_description = 'Passkey'
