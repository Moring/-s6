"""
Tool: Update weekly challenge progress.
"""
import logging
from datetime import date, timedelta
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def update_challenges(user, triggers: Dict, entry_date: date, config: Dict) -> List[Dict[str, Any]]:
    """
    Update user's active weekly challenges based on activity.
    
    Args:
        user: User instance
        triggers: Activity triggers (e.g., {'logged_today': True, 'has_attachment': True})
        entry_date: Date of activity
        config: Reward configuration
    
    Returns:
        List of challenge updates
    """
    from apps.gamification.models import ChallengeTemplate, UserChallenge
    
    updates = []
    
    # Get week boundaries (Monday to Sunday)
    week_start = entry_date - timedelta(days=entry_date.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Get or create active weekly challenges for this user
    active_templates = ChallengeTemplate.objects.filter(
        is_active=True,
        recurrence='weekly'
    )
    
    for template in active_templates:
        # Get or create user challenge for this week
        user_challenge, created = UserChallenge.objects.get_or_create(
            user=user,
            template=template,
            period_start=week_start,
            defaults={
                'period_end': week_end,
                'target_progress': template.goal_target,
                'status': 'active',
                'metadata': {'dates_logged': [], 'details': {}}
            }
        )
        
        if created:
            logger.info(f"Created new challenge {template.code} for user {user.id} for week {week_start}")
        
        # Skip if already completed
        if user_challenge.status == 'completed':
            continue
        
        # Update progress based on goal type
        progress_increased = False
        metadata = user_challenge.metadata or {'dates_logged': [], 'details': {}}
        
        if template.goal_type == 'log_days':
            # Count unique days logged this week
            date_str = entry_date.isoformat()
            if date_str not in metadata.get('dates_logged', []):
                metadata.setdefault('dates_logged', []).append(date_str)
                user_challenge.current_progress = len(metadata['dates_logged'])
                progress_increased = True
        
        elif template.goal_type == 'attach_evidence':
            # Count attachment events
            if triggers.get('has_attachment'):
                user_challenge.current_progress += 1
                metadata.setdefault('details', {}).setdefault('attachments', 0)
                metadata['details']['attachments'] += 1
                progress_increased = True
        
        elif template.goal_type == 'write_outcomes':
            # Count outcome/impact entries
            if triggers.get('has_outcome'):
                user_challenge.current_progress += 1
                metadata.setdefault('details', {}).setdefault('outcomes', 0)
                metadata['details']['outcomes'] += 1
                progress_increased = True
        
        # Check if challenge completed
        if user_challenge.current_progress >= user_challenge.target_progress:
            if user_challenge.status == 'active':
                user_challenge.status = 'completed'
                user_challenge.completed_at = timezone.now()
                
                # Award XP for challenge completion
                if template.xp_reward > 0:
                    from apps.gamification.tools.persister import persist_xp_event
                    persist_xp_event(
                        user=user,
                        amount=template.xp_reward,
                        reason=f"Challenge completed: {template.name}",
                        worklog_entry=None,
                        idempotency_key=f"challenge_xp:{user.id}:{template.code}:{week_start}",
                        metadata={'challenge_id': str(user_challenge.id), 'week_start': week_start.isoformat()}
                    )
                
                updates.append({
                    'challenge_code': template.code,
                    'challenge_name': template.name,
                    'completed': True,
                    'progress': user_challenge.current_progress,
                    'target': user_challenge.target_progress,
                    'xp_reward': template.xp_reward,
                })
                logger.info(f"User {user.id} completed challenge {template.code}")
        
        user_challenge.metadata = metadata
        user_challenge.save()
        
        if progress_increased:
            updates.append({
                'challenge_code': template.code,
                'challenge_name': template.name,
                'completed': False,
                'progress': user_challenge.current_progress,
                'target': user_challenge.target_progress,
            })
    
    return updates


from django.utils import timezone
