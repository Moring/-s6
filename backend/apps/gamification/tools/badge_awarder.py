"""
Tool: Award badges based on triggers (idempotent).
"""
import logging
from typing import Dict, List, Any
from django.db import IntegrityError

logger = logging.getLogger(__name__)


def award_badges(user, triggers: Dict, config: Dict, job_id: str) -> List[Dict[str, Any]]:
    """
    Award badges to user based on triggered conditions.
    Idempotent - will not double-award.
    
    Args:
        user: User instance
        triggers: Dict of trigger conditions met (e.g., {'first_entry': True, 'streak_7': True})
        config: Reward configuration
        job_id: Job ID for provenance tracking
    
    Returns:
        List of awarded badges with details
    """
    from apps.gamification.models import BadgeDefinition, UserBadge, UserStreak, UserXP
    from apps.worklog.models import WorkLog
    
    awarded = []
    
    # Get badge definitions for active badges
    all_badges = BadgeDefinition.objects.filter(is_active=True)
    
    for badge_def in all_badges:
        should_award = False
        trigger_data = {}
        
        # Check trigger conditions
        if badge_def.trigger_type == 'first_entry':
            entry_count = WorkLog.objects.filter(user=user).count()
            if entry_count == 1:
                should_award = True
                trigger_data = {'entry_count': entry_count}
        
        elif badge_def.trigger_type.startswith('streak_'):
            try:
                threshold = int(badge_def.trigger_type.split('_')[1])
                streak = UserStreak.objects.filter(user=user).first()
                if streak and streak.current_streak >= threshold:
                    should_award = True
                    trigger_data = {'current_streak': streak.current_streak}
            except (ValueError, IndexError):
                logger.warning(f"Invalid streak trigger: {badge_def.trigger_type}")
        
        elif badge_def.trigger_type == 'first_attachment':
            if triggers.get('has_attachment'):
                # Check if this is their first attachment ever
                from apps.worklog.models import Attachment
                attachment_count = Attachment.objects.filter(worklog__user=user).count()
                if attachment_count == 1:
                    should_award = True
                    trigger_data = {'first_attachment': True}
        
        elif badge_def.trigger_type.startswith('total_entries_'):
            try:
                threshold = int(badge_def.trigger_type.split('_')[-1])
                entry_count = WorkLog.objects.filter(user=user).count()
                if entry_count >= threshold:
                    should_award = True
                    trigger_data = {'total_entries': entry_count}
            except (ValueError, IndexError):
                logger.warning(f"Invalid entry count trigger: {badge_def.trigger_type}")
        
        elif badge_def.trigger_type.startswith('level_'):
            try:
                level_threshold = int(badge_def.trigger_type.split('_')[1])
                user_xp = UserXP.objects.filter(user=user).first()
                if user_xp and user_xp.level >= level_threshold:
                    should_award = True
                    trigger_data = {'level': user_xp.level}
            except (ValueError, IndexError):
                logger.warning(f"Invalid level trigger: {badge_def.trigger_type}")
        
        # Award badge if conditions met and not already awarded
        if should_award:
            idempotency_key = f"badge:{user.id}:{badge_def.code}:auto"
            try:
                user_badge, created = UserBadge.objects.get_or_create(
                    user=user,
                    badge=badge_def,
                    defaults={
                        'idempotency_key': idempotency_key,
                        'provenance': {
                            'job_id': job_id,
                            'trigger_type': badge_def.trigger_type,
                            'trigger_data': trigger_data,
                        }
                    }
                )
                
                if created:
                    awarded.append({
                        'badge_code': badge_def.code,
                        'badge_name': badge_def.name,
                        'category': badge_def.category,
                        'trigger_data': trigger_data,
                    })
                    logger.info(f"Awarded badge {badge_def.code} to user {user.id}")
                else:
                    logger.debug(f"Badge {badge_def.code} already awarded to user {user.id}")
            
            except IntegrityError as e:
                logger.warning(f"Badge {badge_def.code} already awarded to user {user.id} (race condition)")
    
    return awarded
