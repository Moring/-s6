"""
Django admin for gamification models.
"""
from django.contrib import admin
from django.utils.html import format_html
from apps.gamification.models import (
    UserStreak, UserXP, XPEvent, BadgeDefinition, UserBadge,
    ChallengeTemplate, UserChallenge, RewardConfig, GamificationSettings
)


@admin.register(UserStreak)
class UserStreakAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_streak', 'longest_streak', 'last_counted_date', 'freezes_remaining']
    list_filter = ['last_counted_date']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserXP)
class UserXPAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'total_xp', 'daily_xp', 'daily_xp_date']
    list_filter = ['level', 'daily_xp_date']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-total_xp']


@admin.register(XPEvent)
class XPEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'reason', 'worklog_entry', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'reason', 'idempotency_key']
    readonly_fields = ['id', 'user', 'amount', 'reason', 'worklog_entry', 'metadata', 'idempotency_key', 'created_at']
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BadgeDefinition)
class BadgeDefinitionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'trigger_type', 'trigger_threshold', 'is_active', 'order']
    list_filter = ['category', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('code', 'name', 'description', 'category', 'icon')
        }),
        ('Trigger Configuration', {
            'fields': ('trigger_type', 'trigger_threshold')
        }),
        ('Display', {
            'fields': ('is_active', 'order')
        }),
    )


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'badge', 'awarded_at']
    list_filter = ['awarded_at', 'badge__category']
    search_fields = ['user__username', 'badge__name', 'badge__code']
    readonly_fields = ['id', 'awarded_at', 'provenance', 'idempotency_key']
    ordering = ['-awarded_at']


@admin.register(ChallengeTemplate)
class ChallengeTemplateAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'goal_type', 'goal_target', 'xp_reward', 'recurrence', 'is_active']
    list_filter = ['goal_type', 'recurrence', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('code', 'name', 'description')
        }),
        ('Goal Configuration', {
            'fields': ('goal_type', 'goal_target', 'xp_reward')
        }),
        ('Recurrence & Display', {
            'fields': ('recurrence', 'is_active', 'order')
        }),
    )


@admin.register(UserChallenge)
class UserChallengeAdmin(admin.ModelAdmin):
    list_display = ['user', 'template', 'status', 'progress_display', 'period_start', 'period_end']
    list_filter = ['status', 'period_start', 'template']
    search_fields = ['user__username', 'template__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'completed_at']
    ordering = ['-created_at']
    
    def progress_display(self, obj):
        percent = int((obj.current_progress / obj.target_progress) * 100) if obj.target_progress > 0 else 0
        return format_html(
            '<div style="width:100px; background-color: #f0f0f0;">'
            '<div style="width: {}px; background-color: #4CAF50; height: 20px;"></div>'
            '</div> {}/{}',
            percent, obj.current_progress, obj.target_progress
        )
    progress_display.short_description = 'Progress'


@admin.register(RewardConfig)
class RewardConfigAdmin(admin.ModelAdmin):
    list_display = ['version', 'is_active', 'activated_at', 'created_at']
    list_filter = ['is_active', 'created_at']
    ordering = ['-version']
    
    fieldsets = (
        ('Version', {
            'fields': ('version', 'is_active')
        }),
        ('Configuration (JSON)', {
            'fields': ('config',),
            'classes': ('monospace',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'activated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'activated_at']


@admin.register(GamificationSettings)
class GamificationSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'quiet_mode', 'notifications_enabled', 'show_xp_details', 'show_challenges']
    list_filter = ['quiet_mode', 'notifications_enabled']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
