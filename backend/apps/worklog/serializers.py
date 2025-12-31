"""
Serializers for worklog API.
"""
from rest_framework import serializers
from .models import WorkLog, Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ['id', 'kind', 'filename', 'size_bytes', 'created_at']


class WorkLogSerializer(serializers.ModelSerializer):
    attachments = AttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = WorkLog
        fields = ['id', 'user', 'date', 'content', 'source', 'metadata', 
                  'created_at', 'updated_at', 'attachments']
        read_only_fields = ['created_at', 'updated_at']
