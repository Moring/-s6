"""Gamification views."""
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.api_proxy.client import get_backend_client

logger = logging.getLogger(__name__)


@login_required
def achievements(request):
    """View user achievements and badges."""
    client = get_backend_client(request)
    
    try:
        # Call backend API for badges and summary
        response_badges = client.get('/api/gamification/badges/')
        response_summary = client.get('/api/gamification/summary/')
        
        context = {
            'badges': response_badges.get('earned', []) if response_badges else [],
            'all_badges': response_badges.get('all', []) if response_badges else [],
            'earned_count': response_badges.get('earned_count', 0) if response_badges else 0,
            'total_count': response_badges.get('total_count', 0) if response_badges else 0,
            'xp': response_summary.get('xp', {}) if response_summary else {},
            'streak': response_summary.get('streak', {}) if response_summary else {},
        }
        
        return render(request, 'gamification/achievements.html', context)
    
    except Exception as e:
        logger.error(f"Error loading achievements: {e}", exc_info=True)
        return render(request, 'gamification/achievements.html', {
            'error': 'Unable to load achievements'
        })


@login_required
def challenges(request):
    """View user challenges."""
    client = get_backend_client(request)
    
    try:
        response_challenges = client.get('/api/gamification/challenges/')
        response_summary = client.get('/api/gamification/summary/')
        
        context = {
            'active_challenges': response_challenges.get('active', []) if response_challenges else [],
            'challenge_history': response_challenges.get('history', []) if response_challenges else [],
            'xp': response_summary.get('xp', {}) if response_summary else {},
            'streak': response_summary.get('streak', {}) if response_summary else {},
        }
        
        return render(request, 'gamification/challenges.html', context)
    
    except Exception as e:
        logger.error(f"Error loading challenges: {e}", exc_info=True)
        return render(request, 'gamification/challenges.html', {
            'error': 'Unable to load challenges'
        })


@login_required
def summary_partial(request):
    """HTMX partial for gamification summary widget."""
    client = get_backend_client(request)
    
    try:
        response_summary = client.get('/api/gamification/summary/')
        response_settings = client.get('/api/gamification/settings/')
        
        context = {
            'streak': response_summary.get('streak', {}) if response_summary else {},
            'xp': response_summary.get('xp', {}) if response_summary else {},
            'active_challenges': response_summary.get('active_challenges', []) if response_summary else [],
            'quiet_mode': response_settings.get('quiet_mode', False) if response_settings else False,
        }
        
        return render(request, 'gamification/summary_widget.html', context)
    
    except Exception as e:
        logger.error(f"Error loading gamification summary: {e}", exc_info=True)
        return render(request, 'gamification/summary_widget.html', {
            'error': True
        })
