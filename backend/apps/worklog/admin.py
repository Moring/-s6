"""
Django admin configuration for worklog models.
"""
from django.contrib import admin
from .models import (
    Client, Project, Epic, Feature, Story, Task, Sprint,
    WorkLog, WorkLogSkillSignal, WorkLogBullet, WorkLogPreset, WorkLogReport,
    Attachment, WorkLogExternalLink
)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'name', 'description', 'is_active')
        }),
        ('Additional Info', {
            'fields': ('website', 'notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'client', 'is_active', 'role', 'started_on', 'ended_on']
    list_filter = ['is_active', 'started_on', 'ended_on']
    search_fields = ['name', 'description', 'client__name', 'role']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('client', 'name', 'description', 'is_active')
        }),
        ('Project Details', {
            'fields': ('role', 'started_on', 'ended_on')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Epic)
class EpicAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'project__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ['name', 'epic', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'epic__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'feature', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'feature__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'story', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'story__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active', 'start_date', 'end_date']
    search_fields = ['name', 'goal', 'project__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('project', 'name', 'goal', 'is_active')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class WorkLogSkillSignalInline(admin.TabularInline):
    model = WorkLogSkillSignal
    extra = 0
    fields = ['name', 'kind', 'confidence', 'source', 'status']
    readonly_fields = ['created_at']


class WorkLogBulletInline(admin.TabularInline):
    model = WorkLogBullet
    extra = 0
    fields = ['kind', 'text', 'is_ai_generated', 'is_selected', 'order']
    readonly_fields = ['created_at']


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    fields = ['filename', 'kind', 'size_bytes', 'description']
    readonly_fields = ['created_at', 'uploaded_by']


class WorkLogExternalLinkInline(admin.TabularInline):
    model = WorkLogExternalLink
    extra = 0
    fields = ['system', 'key', 'url', 'title']
    readonly_fields = ['created_at']


@admin.register(WorkLog)
class WorkLogAdmin(admin.ModelAdmin):
    list_display = ['occurred_on', 'user', 'title_excerpt', 'status', 'work_type', 'client', 'project', 'effort_minutes']
    list_filter = ['status', 'work_type', 'enrichment_status', 'occurred_on', 'created_at']
    search_fields = ['title', 'content', 'outcome', 'user__username', 'client__name', 'project__name']
    readonly_fields = ['created_at', 'updated_at', 'hours']
    date_hierarchy = 'occurred_on'
    
    inlines = [AttachmentInline, WorkLogSkillSignalInline, WorkLogBulletInline, WorkLogExternalLinkInline]
    
    fieldsets = (
        (None, {
            'fields': ('user', 'occurred_on', 'title', 'status')
        }),
        ('Organization', {
            'fields': ('client', 'project', 'sprint')
        }),
        ('Agile Hierarchy', {
            'fields': ('epic', 'feature', 'story', 'task'),
            'classes': ('collapse',)
        }),
        ('Content', {
            'fields': ('work_type', 'content', 'outcome', 'impact', 'next_steps', 'tags')
        }),
        ('Effort', {
            'fields': ('effort_minutes', 'hours', 'is_billable')
        }),
        ('Source & Metadata', {
            'fields': ('source', 'source_ref', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Enrichment', {
            'fields': ('enrichment_status', 'enrichment_suggestions', 'ai_summary'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def title_excerpt(self, obj):
        return obj.title[:50] if obj.title else f"{obj.content[:50]}..." if obj.content else '(no content)'
    title_excerpt.short_description = 'Title/Content'


@admin.register(WorkLogSkillSignal)
class WorkLogSkillSignalAdmin(admin.ModelAdmin):
    list_display = ['name', 'kind', 'worklog', 'confidence', 'source', 'status', 'created_at']
    list_filter = ['kind', 'source', 'status', 'created_at']
    search_fields = ['name', 'evidence', 'worklog__content']
    readonly_fields = ['created_at']


@admin.register(WorkLogBullet)
class WorkLogBulletAdmin(admin.ModelAdmin):
    list_display = ['bullet_excerpt', 'worklog', 'kind', 'is_ai_generated', 'is_selected', 'order']
    list_filter = ['kind', 'is_ai_generated', 'is_selected', 'created_at']
    search_fields = ['text', 'worklog__content']
    readonly_fields = ['created_at']
    
    def bullet_excerpt(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    bullet_excerpt.short_description = 'Text'


@admin.register(WorkLogPreset)
class WorkLogPresetAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'client', 'project', 'default_work_type', 'is_active']
    list_filter = ['is_active', 'default_work_type', 'created_at']
    search_fields = ['name', 'description', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'name', 'description', 'is_active')
        }),
        ('Defaults', {
            'fields': ('client', 'project', 'default_work_type', 'default_tags')
        }),
        ('Assistant', {
            'fields': ('intake_prompt',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WorkLogReport)
class WorkLogReportAdmin(admin.ModelAdmin):
    list_display = ['title_excerpt', 'user', 'kind', 'period_start', 'period_end', 'created_at']
    list_filter = ['kind', 'created_via', 'created_at']
    search_fields = ['title', 'content_md', 'user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'kind', 'created_via')
        }),
        ('Scope', {
            'fields': ('client', 'project', 'sprint', 'period_start', 'period_end')
        }),
        ('Content', {
            'fields': ('content_md', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def title_excerpt(self, obj):
        return obj.title[:60] if obj.title else f"Report {obj.id}"
    title_excerpt.short_description = 'Title'


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'worklog', 'kind', 'size_bytes', 'uploaded_by', 'created_at']
    list_filter = ['kind', 'storage_provider', 'created_at']
    search_fields = ['filename', 'description', 'worklog__content']
    readonly_fields = ['created_at', 'checksum_sha256']
    
    fieldsets = (
        (None, {
            'fields': ('worklog', 'uploaded_by', 'filename', 'kind')
        }),
        ('Storage', {
            'fields': ('storage_provider', 'object_key', 'mime_type', 'size_bytes', 'checksum_sha256')
        }),
        ('Details', {
            'fields': ('description', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(WorkLogExternalLink)
class WorkLogExternalLinkAdmin(admin.ModelAdmin):
    list_display = ['title_or_url', 'worklog', 'system', 'key', 'created_at']
    list_filter = ['system', 'created_at']
    search_fields = ['title', 'url', 'key', 'worklog__content']
    readonly_fields = ['created_at']
    
    def title_or_url(self, obj):
        return obj.title if obj.title else obj.url[:60]
    title_or_url.short_description = 'Title/URL'
