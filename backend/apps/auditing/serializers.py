from rest_framework import serializers
from apps.auditing.models import AuthEvent


class AuthEventSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    passkey_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = AuthEvent
        fields = [
            'id', 'event_type', 'timestamp', 'user', 'username',
            'ip_address', 'user_agent', 'passkey', 'passkey_preview',
            'details', 'success', 'failure_reason'
        ]
        read_only_fields = ['__all__']
    
    def get_passkey_preview(self, obj):
        if obj.passkey:
            return f"{obj.passkey.key[:8]}..."
        return None
