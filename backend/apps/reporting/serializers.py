"""
Serializers for reporting API.
"""
from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'user', 'kind', 'content', 'rendered_text', 'rendered_html',
                  'metadata', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'rendered_text', 'rendered_html']
