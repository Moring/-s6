from django.contrib import admin
from apps.accounts.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_username', 'get_email', 'tenant', 'stripe_customer_id', 'created_at']
    list_filter = ['tenant', 'created_at']
    search_fields = ['user__username', 'user__email', 'stripe_customer_id', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'tenant')
        }),
        ('Billing', {
            'fields': ('stripe_customer_id',)
        }),
        ('Settings & Notes', {
            'fields': ('settings', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'user__username'
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    get_email.admin_order_field = 'user__email'
