"""
Tool: Validate if worklog entry is meaningful for reward purposes.
"""
import logging
from typing import Dict, Tuple
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


def is_meaningful_entry(entry, config: Dict) -> Tuple[bool, Dict]:
    """
    Determine if a worklog entry qualifies for rewards.
    
    Args:
        entry: WorkLog instance
        config: Reward configuration dict with rules
    
    Returns:
        (is_meaningful: bool, reasons: Dict)
    """
    reasons = {
        'valid': True,
        'checks': [],
        'failures': [],
    }
    
    min_length = config.get('min_entry_length', 20)
    max_entries_per_hour = config.get('max_entries_per_hour', 10)
    duplicate_threshold_seconds = config.get('duplicate_threshold_seconds', 60)
    
    # Check 1: Minimum content length
    content_length = len(entry.content.strip()) if entry.content else 0
    if content_length < min_length:
        reasons['valid'] = False
        reasons['failures'].append(f'Content too short: {content_length} < {min_length} chars')
    else:
        reasons['checks'].append(f'Content length OK: {content_length} chars')
    
    # Check 2: Rate limiting - check for spam (too many entries in short time)
    from apps.worklog.models import WorkLog
    recent_cutoff = timezone.now() - timedelta(hours=1)
    recent_count = WorkLog.objects.filter(
        user=entry.user,
        created_at__gte=recent_cutoff
    ).count()
    
    if recent_count > max_entries_per_hour:
        reasons['valid'] = False
        reasons['failures'].append(f'Too many entries in last hour: {recent_count} > {max_entries_per_hour}')
    else:
        reasons['checks'].append(f'Rate limit OK: {recent_count} entries in last hour')
    
    # Check 3: Duplicate detection (very similar timestamp and same date)
    duplicate_cutoff = timezone.now() - timedelta(seconds=duplicate_threshold_seconds)
    duplicate_count = WorkLog.objects.filter(
        user=entry.user,
        date=entry.date,
        created_at__gte=duplicate_cutoff
    ).exclude(id=entry.id).count()
    
    if duplicate_count > 0:
        reasons['valid'] = False
        reasons['failures'].append(f'Duplicate entry detected within {duplicate_threshold_seconds}s')
    else:
        reasons['checks'].append('No duplicate detected')
    
    logger.info(f"Entry {entry.id} validation: valid={reasons['valid']}, checks={len(reasons['checks'])}, failures={len(reasons['failures'])}")
    
    return reasons['valid'], reasons
