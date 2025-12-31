"""
DAG Workflow: Evaluate rewards on worklog change.
Computes XP, updates streaks, awards badges, updates challenges.
"""
import logging
from typing import Dict, Any
from django.utils import timezone

from apps.jobs.registry import register
from apps.observability.services import log_event

logger = logging.getLogger(__name__)


@register('gamification.reward_evaluate')
def execute(ctx, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute reward evaluation workflow.
    
    Payload:
        - entry_id: WorkLog ID
    
    Returns:
        Workflow result with all reward updates
    """
    from apps.worklog.models import WorkLog, Attachment
    from apps.gamification.models import RewardConfig
    from apps.gamification.tools import (
        is_meaningful_entry,
        compute_xp,
        update_streak,
        award_badges,
        update_challenges,
        persist_events,
    )
    
    entry_id = payload.get('entry_id')
    job_id = ctx.job_id if hasattr(ctx, 'job_id') else 'unknown'
    
    logger.info(f"Starting reward evaluation for entry {entry_id}, job {job_id}")
    log_event(ctx, f"Starting reward evaluation for entry {entry_id}", source='workflow.reward')
    
    result = {
        'entry_id': entry_id,
        'job_id': job_id,
        'valid': False,
        'xp_awarded': 0,
        'streak_updated': False,
        'badges_awarded': [],
        'challenges_updated': [],
        'errors': [],
    }
    
    try:
        # Step 1: Load entry
        try:
            entry = WorkLog.objects.select_related('user').get(id=entry_id)
        except WorkLog.DoesNotExist:
            result['errors'].append(f"WorkLog {entry_id} not found")
            return result
        
        user = entry.user
        if not user:
            result['errors'].append("Entry has no associated user")
            return result
        
        # Step 2: Load reward config
        config_obj = RewardConfig.objects.filter(is_active=True).first()
        if config_obj:
            config = config_obj.config
        else:
            # Default config
            config = {
                'min_entry_length': 20,
                'max_entries_per_hour': 10,
                'duplicate_threshold_seconds': 60,
                'max_daily_xp': 200,
                'xp_rules': {
                    'base_entry': 10,
                    'per_attachment': 5,
                    'per_tag': 3,
                    'length_bonus_threshold': 200,
                    'length_bonus': 10,
                },
                'max_freezes': 3,
            }
        
        log_event(ctx, 'Validating entry meaningfulness', source='workflow.reward')
        
        # Step 3: Validate meaningful entry
        is_valid, validation_reasons = is_meaningful_entry(entry, config)
        result['valid'] = is_valid
        result['validation_reasons'] = validation_reasons
        
        if not is_valid:
            logger.info(f"Entry {entry_id} not valid for rewards: {validation_reasons['failures']}")
            log_event(ctx, f"Entry not valid: {validation_reasons['failures']}", level='info', source='workflow.reward')
            return result
        
        log_event(ctx, 'Computing XP', source='workflow.reward')
        
        # Step 4: Compute XP
        attachments_count = Attachment.objects.filter(worklog=entry).count()
        tags = entry.metadata.get('tags', []) if entry.metadata else []
        
        xp_result = compute_xp(entry, attachments_count, tags, config)
        
        # Step 5: Persist XP
        if xp_result['total_xp'] > 0:
            persist_result = persist_events(xp_result, user, entry, job_id)
            result['xp_awarded'] = persist_result.get('xp_amount', 0)
            if persist_result.get('errors'):
                result['errors'].extend(persist_result['errors'])
            
            log_event(ctx, f"Awarded {result['xp_awarded']} XP", source='workflow.reward')
        
        # Step 6: Update streak
        log_event(ctx, 'Updating streak', source='workflow.reward')
        streak_result = update_streak(user, entry.date, config)
        result['streak_updated'] = True
        result['streak'] = {
            'current': streak_result['current_streak'],
            'longest': streak_result['longest_streak'],
            'freeze_used': streak_result['freeze_used'],
            'broken': streak_result['streak_broken'],
        }
        
        # Step 7: Award badges
        log_event(ctx, 'Checking badges', source='workflow.reward')
        triggers = {
            'has_attachment': attachments_count > 0,
            'has_outcome': bool(entry.metadata and (entry.metadata.get('outcome') or entry.metadata.get('impact'))),
        }
        
        badges_awarded = award_badges(user, triggers, config, job_id)
        result['badges_awarded'] = badges_awarded
        
        if badges_awarded:
            log_event(ctx, f"Awarded {len(badges_awarded)} badges", source='workflow.reward')
        
        # Step 8: Update challenges
        log_event(ctx, 'Updating challenges', source='workflow.reward')
        challenges_updated = update_challenges(user, triggers, entry.date, config)
        result['challenges_updated'] = challenges_updated
        
        log_event(
            ctx,
            f"Reward evaluation completed: XP={result['xp_awarded']}, badges={len(badges_awarded)}, challenges={len(challenges_updated)}",
            level='info',
            source='workflow.reward'
        )
        
        logger.info(f"Reward evaluation completed for entry {entry_id}: XP={result['xp_awarded']}, badges={len(badges_awarded)}, challenges={len(challenges_updated)}")
    
    except Exception as e:
        logger.error(f"Error in reward evaluation: {e}", exc_info=True)
        result['errors'].append(f"Workflow error: {str(e)}")
        log_event(ctx, f"Reward evaluation failed: {str(e)}", level='error', source='workflow.reward')
    
    return result
