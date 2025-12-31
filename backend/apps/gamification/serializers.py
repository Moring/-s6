"""
Gamification API serializers.
"""
from rest_framework import serializers
from apps.gamification.models import (
    BadgeDefinition, UserBadge, ChallengeTemplate, 
    UserChallenge, GamificationSettings
)


class BadgeDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BadgeDefinition
        fields = ['code', 'name', 'description', 'category', 'icon', 'trigger_type']


class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeDefinitionSerializer(read_only=True)
    
    class Meta:
        model = UserBadge
        fields = ['id', 'badge', 'awarded_at']


class ChallengeTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeTemplate
        fields = ['code', 'name', 'description', 'goal_type', 'goal_target', 'xp_reward', 'recurrence']


class UserChallengeSerializer(serializers.ModelSerializer):
    template = ChallengeTemplateSerializer(read_only=True)
    progress_percent = serializers.SerializerMethodField()
    
    class Meta:
        model = UserChallenge
        fields = ['id', 'template', 'status', 'current_progress', 'target_progress', 
                 'progress_percent', 'period_start', 'period_end', 'completed_at']
    
    def get_progress_percent(self, obj):
        if obj.target_progress > 0:
            return int((obj.current_progress / obj.target_progress) * 100)
        return 0


class GamificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GamificationSettings
        fields = ['quiet_mode', 'notifications_enabled', 'show_xp_details', 'show_challenges']
        read_only_fields = []


class ManualXPGrantSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=500)


class ManualBadgeRevokeSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    badge_code = serializers.CharField(max_length=100)
    reason = serializers.CharField(max_length=500)
