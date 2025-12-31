"""
Tool: Update user streak based on worklog activity.
"""
import logging
from datetime import date, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)


def update_streak(user, entry_date: date, config: Dict) -> Dict[str, Any]:
    """
    Update user's daily logging streak.
    
    Args:
        user: User instance
        entry_date: Date of the worklog entry
        config: Reward configuration with freeze rules
    
    Returns:
        {
            'current_streak': int,
            'longest_streak': int,
            'freeze_used': bool,
            'streak_broken': bool,
            'changes': Dict
        }
    """
    from apps.gamification.models import UserStreak
    
    streak, created = UserStreak.objects.get_or_create(user=user)
    
    if created:
        # First ever entry
        streak.current_streak = 1
        streak.longest_streak = 1
        streak.last_counted_date = entry_date
        streak.save()
        
        logger.info(f"User {user.id} started first streak")
        
        return {
            'current_streak': 1,
            'longest_streak': 1,
            'freeze_used': False,
            'streak_broken': False,
            'changes': {'started_streak': True}
        }
    
    # Check if this date already counted
    if streak.last_counted_date == entry_date:
        logger.info(f"User {user.id} already logged for {entry_date}, no streak update")
        return {
            'current_streak': streak.current_streak,
            'longest_streak': streak.longest_streak,
            'freeze_used': False,
            'streak_broken': False,
            'changes': {'already_counted': True}
        }
    
    # Calculate days since last entry
    if streak.last_counted_date:
        days_diff = (entry_date - streak.last_counted_date).days
    else:
        days_diff = 999  # Large number to indicate first entry
    
    freeze_used = False
    streak_broken = False
    changes = {}
    
    if days_diff == 1:
        # Consecutive day - increment streak
        streak.current_streak += 1
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
            changes['new_longest'] = True
        changes['incremented'] = True
        logger.info(f"User {user.id} streak incremented to {streak.current_streak}")
    
    elif days_diff == 2 and streak.freezes_remaining > 0:
        # Missed one day but has freeze available
        streak.freezes_remaining -= 1
        streak.freezes_used += 1
        freeze_used = True
        streak.current_streak += 1
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
        changes['freeze_applied'] = True
        logger.info(f"User {user.id} used freeze, streak continues at {streak.current_streak}")
    
    else:
        # Streak broken
        streak_broken = True
        old_streak = streak.current_streak
        streak.current_streak = 1
        changes['broken'] = True
        changes['old_streak'] = old_streak
        logger.info(f"User {user.id} streak broken (was {old_streak}), restarting at 1")
    
    streak.last_counted_date = entry_date
    streak.save()
    
    return {
        'current_streak': streak.current_streak,
        'longest_streak': streak.longest_streak,
        'freeze_used': freeze_used,
        'streak_broken': streak_broken,
        'changes': changes,
    }
