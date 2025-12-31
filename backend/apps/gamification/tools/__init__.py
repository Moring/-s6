"""
Gamification reward calculation tools.
Used by DAG nodes to compute XP, update streaks, award badges, etc.
All tools are pure functions or have explicit side effects documented.
"""

from .entry_validator import is_meaningful_entry
from .xp_calculator import compute_xp
from .streak_updater import update_streak
from .badge_awarder import award_badges
from .challenge_updater import update_challenges
from .persister import persist_events

__all__ = [
    'is_meaningful_entry',
    'compute_xp',
    'update_streak',
    'award_badges',
    'update_challenges',
    'persist_events',
]
