from rest_framework import serializers
from apps.invitations.models import InvitePasskey
from django.utils import timezone


class InvitePasskeySerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    used_by_username = serializers.CharField(source='used_by.username', read_only=True, allow_null=True)
    tenant_name = serializers.CharField(source='tenant_scope.name', read_only=True, allow_null=True)
    status = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = InvitePasskey
        fields = [
            'id', 'key', 'raw_key', 'created_at', 'created_by', 'created_by_username',
            'expires_at', 'used_at', 'used_by', 'used_by_username',
            'max_uses', 'actual_uses', 'tenant_scope', 'tenant_name',
            'notes', 'status', 'is_valid'
        ]
        read_only_fields = ['key', 'raw_key', 'created_at', 'used_at', 'used_by', 'actual_uses']
    
    def get_status(self, obj):
        if obj.is_used():
            return 'used'
        elif obj.is_expired():
            return 'expired'
        else:
            return 'active'
    
    def get_is_valid(self, obj):
        return obj.is_valid()


class PasskeyCreateSerializer(serializers.Serializer):
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    tenant_scope = serializers.IntegerField(required=False, allow_null=True)
    max_uses = serializers.IntegerField(default=1, min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_expires_at(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Expiration date must be in the future")
        return value
