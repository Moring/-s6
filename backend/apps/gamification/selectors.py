"""
Gamification read-only query selectors.
"""
import logging
from typing import Dict, List, Any, Optional
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import date, timedelta

from apps.gamification.models import (
    UserStreak, UserXP, XPEvent, BadgeDefinition, UserBadge,
    ChallengeTemplate, UserChallenge, GamificationSettings
)

User = get_user_model()
logger = logging.getLogger(__name__)


def get_user_summary(user) -> Dict[str, Any]:
    """
    Get complete gamification summary for a user.
    
    Returns:
        {
            'streak': {...},
            'xp': {...},
            'level': {...},
            'daily_progress': {...},
            'active_challenges': [...],
        }
    """
    # Streak
    streak = UserStreak.objects.filter(user=user).first()
    streak_data = {
        'current': streak.current_streak if streak else 0,
        'longest': streak.longest_streak if streak else 0,
        'freezes_remaining': streak.freezes_remaining if streak else 3,
        'last_logged': streak.last_counted_date.isoformat() if streak and streak.last_counted_date else None,
    }
    
    # XP and Level
    user_xp = UserXP.objects.filter(user=user).first()
    if user_xp:
        today = timezone.now().date()
        if user_xp.daily_xp_date != today:
            daily_xp = 0
        else:
            daily_xp = user_xp.daily_xp
        
        xp_data = {
            'total': user_xp.total_xp,
            'level': user_xp.level,
            'daily_xp': daily_xp,
            'daily_goal': 50,  # Could be configurable
            'daily_progress_percent': min(100, int((daily_xp / 50) * 100)),
        }
    else:
        xp_data = {
            'total': 0,
            'level': 1,
            'daily_xp': 0,
            'daily_goal': 50,
            'daily_progress_percent': 0,
        }
    
    # Active challenges
    active_challenges = get_active_challenges(user)
    
    return {
        'streak': streak_data,
        'xp': xp_data,
        'active_challenges': active_challenges,
    }


def get_badges(user) -> Dict[str, Any]:
    """
    Get user's earned and available badges.
    """
    earned_badges = UserBadge.objects.filter(user=user).select_related('badge').order_by('-awarded_at')
    all_badges = BadgeDefinition.objects.filter(is_active=True).order_by('order', 'name')
    
    earned_codes = set(ub.badge.code for ub in earned_badges)
    
    earned_list = [
        {
            'code': ub.badge.code,
            'name': ub.badge.name,
            'description': ub.badge.description,
            'category': ub.badge.category,
            'icon': ub.badge.icon,
            'awarded_at': ub.awarded_at.isoformat(),
        }
        for ub in earned_badges
    ]
    
    available_list = [
        {
            'code': badge.code,
            'name': badge.name,
            'description': badge.description,
            'category': badge.category,
            'icon': badge.icon,
            'earned': badge.code in earned_codes,
        }
        for badge in all_badges
    ]
    
    return {
        'earned': earned_list,
        'all': available_list,
        'earned_count': len(earned_list),
        'total_count': all_badges.count(),
    }


def get_active_challenges(user) -> List[Dict[str, Any]]:
    """
    Get user's active challenges.
    """
    today = date.today()
    
    active = UserChallenge.objects.filter(
        user=user,
        status='active',
        period_end__gte=today
    ).select_related('template').order_by('period_end')
    
    challenges = []
    for challenge in active:
        progress_percent = int((challenge.current_progress / challenge.target_progress) * 100) if challenge.target_progress > 0 else 0
        
        challenges.append({
            'id': str(challenge.id),
            'name': challenge.template.name,
            'description': challenge.template.description,
            'progress': challenge.current_progress,
            'target': challenge.target_progress,
            'progress_percent': progress_percent,
            'xp_reward': challenge.template.xp_reward,
            'period_end': challenge.period_end.isoformat(),
            'days_remaining': (challenge.period_end - today).days,
        })
    
    return challenges


def get_challenge_history(user, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get user's completed challenges.
    """
    completed = UserChallenge.objects.filter(
        user=user,
        status='completed'
    ).select_related('template').order_by('-completed_at')[:limit]
    
    history = []
    for challenge in completed:
        history.append({
            'id': str(challenge.id),
            'name': challenge.template.name,
            'completed_at': challenge.completed_at.isoformat() if challenge.completed_at else None,
            'xp_reward': challenge.template.xp_reward,
            'period_start': challenge.period_start.isoformat(),
            'period_end': challenge.period_end.isoformat(),
        })
    
    return history


def get_user_settings(user) -> Dict[str, Any]:
    """
    Get user's gamification settings.
    """
    settings, _ = GamificationSettings.objects.get_or_create(user=user)
    
    return {
        'quiet_mode': settings.quiet_mode,
        'notifications_enabled': settings.notifications_enabled,
        'show_xp_details': settings.show_xp_details,
        'show_challenges': settings.show_challenges,
    }


def get_engagement_metrics() -> Dict[str, Any]:
    """
    Get platform-wide engagement metrics (admin view).
    """
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    # Active users (logged in last 7 days)
    from apps.worklog.models import WorkLog
    active_users = WorkLog.objects.filter(
        created_at__date__gte=week_ago
    ).values('user').distinct().count()
    
    # Streak distribution
    streak_stats = UserStreak.objects.aggregate(
        avg_current=Sum('current_streak') / Count('id') if Count('id') > 0 else 0,
        max_current=models.Max('current_streak'),
    )
    
    # Top level users
    top_users = UserXP.objects.select_related('user').order_by('-total_xp')[:10]
    
    # Challenge completion rate
    total_challenges = UserChallenge.objects.filter(period_end__gte=week_ago).count()
    completed_challenges = UserChallenge.objects.filter(
        period_end__gte=week_ago,
        status='completed'
    ).count()
    
    completion_rate = (completed_challenges / total_challenges * 100) if total_challenges > 0 else 0
    
    return {
        'active_users_7d': active_users,
        'streak_avg': round(streak_stats['avg_current'] or 0, 1),
        'streak_max': streak_stats['max_current'] or 0,
        'challenge_completion_rate': round(completion_rate, 1),
        'top_users': [
            {
                'user_id': uxp.user.id,
                'username': uxp.user.username,
                'level': uxp.level,
                'total_xp': uxp.total_xp,
            }
            for uxp in top_users
        ],
    }


from django.db import models
