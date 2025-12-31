"""
Artifact serializers.
"""
from rest_framework import serializers
from .models import Artifact


class ArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artifact
        fields = ['id', 'name', 'content_type', 'size', 'created_at']
        read_only_fields = ['id', 'created_at']
