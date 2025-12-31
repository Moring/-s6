"""
Gamification API views.
"""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model

from apps.gamification import selectors, services
from apps.gamification.serializers import (
    GamificationSettingsSerializer,
    ManualXPGrantSerializer,
    ManualBadgeRevokeSerializer,
)
from apps.tenants.roles import has_permission, Permission, get_user_role
from apps.tenants.models import Tenant

User = get_user_model()
logger = logging.getLogger(__name__)


class GamificationSummaryView(APIView):
    """Get gamification summary for authenticated user."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        try:
            summary = selectors.get_user_summary(user)
            return Response(summary, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting gamification summary: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to get gamification summary'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BadgesView(APIView):
    """Get user's badges (earned and available)."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        try:
            badges = selectors.get_badges(user)
            return Response(badges, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting badges: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to get badges'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChallengesView(APIView):
    """Get user's challenges (active and history)."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        try:
            active = selectors.get_active_challenges(user)
            history = selectors.get_challenge_history(user, limit=10)
            
            return Response({
                'active': active,
                'history': history,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting challenges: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to get challenges'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GamificationSettingsView(APIView):
    """Get and update gamification settings."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        try:
            settings_data = selectors.get_user_settings(user)
            return Response(settings_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting settings: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to get settings'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request):
        user = request.user
        
        try:
            from apps.gamification.models import GamificationSettings
            settings, _ = GamificationSettings.objects.get_or_create(user=user)
            
            serializer = GamificationSettingsSerializer(settings, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating settings: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to update settings'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminGamificationMetricsView(APIView):
    """Get platform-wide gamification metrics (admin only)."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if user is staff/superuser
        if not request.user.is_staff:
            return Response(
                {'error': 'Admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            metrics = selectors.get_engagement_metrics()
            return Response(metrics, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting engagement metrics: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to get metrics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminManualXPGrantView(APIView):
    """Manually grant XP to user (admin only)."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check if user is staff/superuser
        if not request.user.is_staff:
            return Response(
                {'error': 'Admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ManualXPGrantSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        result = services.manual_grant_xp(
            user_id=serializer.validated_data['user_id'],
            amount=serializer.validated_data['amount'],
            reason=serializer.validated_data['reason'],
            granted_by_user_id=request.user.id
        )
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class AdminManualBadgeRevokeView(APIView):
    """Manually revoke badge from user (admin only)."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check if user is staff/superuser
        if not request.user.is_staff:
            return Response(
                {'error': 'Admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ManualBadgeRevokeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        result = services.manual_revoke_badge(
            user_id=serializer.validated_data['user_id'],
            badge_code=serializer.validated_data['badge_code'],
            reason=serializer.validated_data['reason'],
            revoked_by_user_id=request.user.id
        )
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
