"""
Serializers for skills API.
"""
from rest_framework import serializers
from .models import Skill, SkillEvidence


class SkillEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillEvidence
        fields = ['id', 'source_type', 'source_id', 'excerpt', 'weight', 'created_at']


class SkillSerializer(serializers.ModelSerializer):
    evidence_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Skill
        fields = ['id', 'user', 'name', 'normalized', 'confidence', 'level', 
                  'metadata', 'created_at', 'updated_at', 'evidence_count']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_evidence_count(self, obj):
        return obj.evidence.count()
