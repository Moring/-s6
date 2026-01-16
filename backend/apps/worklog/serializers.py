"""
Serializers for worklog API.
"""
from rest_framework import serializers
from .models import (
    WorkLog, Attachment, Client, Project, Epic, Feature, Story, Task, Sprint
)


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = Project
        fields = ['id', 'client', 'client_name', 'name', 'description', 'is_active', 'created_at', 'updated_at']
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
        fields = ['id', 'project', 'project_name', 'name', 'goal', 'start_date', 'end_date', 
                  'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ['id', 'kind', 'filename', 'description', 'size_bytes', 'created_at']


class WorkLogSerializer(serializers.ModelSerializer):
    attachments = AttachmentSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    
    class Meta:
        model = WorkLog
        fields = [
            'id', 'user', 'date', 
            'client', 'client_name', 'project', 'project_name',
            'epic', 'feature', 'story', 'task', 'sprint',
            'content', 'outcome', 'work_type', 'hours', 'tags',
            'source', 'metadata', 'enrichment_status', 'enrichment_suggestions',
            'is_draft', 'created_at', 'updated_at', 'attachments'
        ]
        read_only_fields = ['created_at', 'updated_at']


class WorkLogListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""
    client_name = serializers.CharField(source='client.name', read_only=True, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    attachment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkLog
        fields = [
            'id', 'date', 'client', 'client_name', 'project', 'project_name',
            'work_type', 'content', 'hours', 'tags', 'is_draft',
            'attachment_count', 'created_at'
        ]
    
    def get_attachment_count(self, obj):
        return obj.attachments.count()
