"""
Serializers for worklog API.
"""
from rest_framework import serializers
from .models import (
    WorkLog, Attachment, Client, Project, Epic, Feature, Story, Task, Sprint,
    WorkLogSkillSignal, WorkLogBullet, WorkLogPreset, WorkLogReport, WorkLogExternalLink
)


# ================================
# Organizational hierarchy serializers
# ================================

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'description', 'is_active', 'website', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'client', 'client_name', 'name', 'description', 'is_active',
            'role', 'started_on', 'ended_on', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class EpicSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = Epic
        fields = ['id', 'project', 'project_name', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class FeatureSerializer(serializers.ModelSerializer):
    epic_name = serializers.CharField(source='epic.name', read_only=True)
    
    class Meta:
        model = Feature
        fields = ['id', 'epic', 'epic_name', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class StorySerializer(serializers.ModelSerializer):
    feature_name = serializers.CharField(source='feature.name', read_only=True)
    
    class Meta:
        model = Story
        fields = ['id', 'feature', 'feature_name', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class TaskSerializer(serializers.ModelSerializer):
    story_name = serializers.CharField(source='story.name', read_only=True)
    
    class Meta:
        model = Task
        fields = ['id', 'story', 'story_name', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class SprintSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = Sprint
        fields = [
            'id', 'project', 'project_name', 'name', 'goal', 'start_date', 'end_date', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


# ================================
# Attachment and external links
# ================================

class AttachmentSerializer(serializers.ModelSerializer):
    uploader_username = serializers.CharField(source='uploaded_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = Attachment
        fields = [
            'id', 'kind', 'storage_provider', 'object_key', 'filename', 'mime_type',
            'description', 'size_bytes', 'checksum_sha256', 'uploaded_by', 'uploader_username',
            'metadata', 'created_at'
        ]
        read_only_fields = ['created_at', 'uploaded_by', 'uploader_username']


class WorkLogExternalLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkLogExternalLink
        fields = ['id', 'system', 'key', 'url', 'title', 'metadata', 'created_at']
        read_only_fields = ['created_at']


# ================================
# Enrichment artifacts
# ================================

class WorkLogSkillSignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkLogSkillSignal
        fields = [
            'id', 'name', 'kind', 'confidence', 'source', 'status', 
            'evidence', 'metadata', 'created_at'
        ]
        read_only_fields = ['created_at']


class WorkLogBulletSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkLogBullet
        fields = [
            'id', 'kind', 'text', 'is_ai_generated', 'is_selected', 
            'order', 'metrics', 'metadata', 'created_at'
        ]
        read_only_fields = ['created_at']


# ================================
# WorkLog main serializers
# ================================

class WorkLogSerializer(serializers.ModelSerializer):
    """Full detail serializer for WorkLog."""
    attachments = AttachmentSerializer(many=True, read_only=True)
    external_links = WorkLogExternalLinkSerializer(many=True, read_only=True)
    skill_signals = WorkLogSkillSignalSerializer(many=True, read_only=True)
    bullets = WorkLogBulletSerializer(many=True, read_only=True)
    
    client_name = serializers.CharField(source='client.name', read_only=True, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    hours = serializers.FloatField(read_only=True)
    
    class Meta:
        model = WorkLog
        fields = [
            'id', 'user', 'occurred_on', 'title',
            'client', 'client_name', 'project', 'project_name',
            'epic', 'feature', 'story', 'task', 'sprint',
            'work_type', 'status', 'content', 'outcome', 'impact', 'next_steps',
            'effort_minutes', 'hours', 'is_billable', 'tags',
            'source', 'source_ref', 'metadata',
            'enrichment_status', 'enrichment_suggestions', 'ai_summary',
            'created_at', 'updated_at',
            'attachments', 'external_links', 'skill_signals', 'bullets'
        ]
        read_only_fields = ['created_at', 'updated_at', 'hours']


class WorkLogListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""
    client_name = serializers.CharField(source='client.name', read_only=True, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    attachment_count = serializers.SerializerMethodField()
    hours = serializers.FloatField(read_only=True)
    
    class Meta:
        model = WorkLog
        fields = [
            'id', 'occurred_on', 'title', 'status',
            'client', 'client_name', 'project', 'project_name',
            'work_type', 'content', 'effort_minutes', 'hours', 'tags',
            'enrichment_status', 'attachment_count', 'created_at'
        ]
    
    def get_attachment_count(self, obj):
        return obj.attachments.count()


class WorkLogCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating WorkLog entries with validation."""
    
    class Meta:
        model = WorkLog
        fields = [
            'occurred_on', 'title',
            'client', 'project', 'epic', 'feature', 'story', 'task', 'sprint',
            'work_type', 'status', 'content', 'outcome', 'impact', 'next_steps',
            'effort_minutes', 'is_billable', 'tags',
            'source', 'source_ref', 'metadata'
        ]
    
    def validate(self, attrs):
        """Run model-level validation."""
        instance = WorkLog(**attrs)
        if self.instance:
            # Update existing instance for validation
            for key, value in attrs.items():
                setattr(self.instance, key, value)
            instance = self.instance
        
        # Set user for validation
        request = self.context.get('request')
        if request and request.user:
            instance.user = request.user
        
        try:
            instance.clean()
        except Exception as e:
            raise serializers.ValidationError(str(e))
        
        return attrs


# ================================
# Preset and report serializers
# ================================

class WorkLogPresetSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    
    class Meta:
        model = WorkLogPreset
        fields = [
            'id', 'name', 'description',
            'client', 'client_name', 'project', 'project_name',
            'default_work_type', 'default_tags', 'intake_prompt',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class WorkLogReportSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    sprint_name = serializers.CharField(source='sprint.name', read_only=True, allow_null=True)
    
    class Meta:
        model = WorkLogReport
        fields = [
            'id', 'user',
            'client', 'client_name', 'project', 'project_name', 'sprint', 'sprint_name',
            'kind', 'created_via', 'period_start', 'period_end',
            'title', 'content_md', 'metadata', 'created_at'
        ]
        read_only_fields = ['created_at']
