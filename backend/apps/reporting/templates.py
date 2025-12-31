"""
Report template utilities.
"""


def get_resume_template() -> dict:
    """Get default resume template structure."""
    return {
        'sections': [
            {'name': 'summary', 'title': 'Professional Summary'},
            {'name': 'experience', 'title': 'Experience'},
            {'name': 'skills', 'title': 'Skills'},
            {'name': 'education', 'title': 'Education'},
        ]
    }


def get_status_template() -> dict:
    """Get default status report template structure."""
    return {
        'sections': [
            {'name': 'completed', 'title': 'Completed This Week'},
            {'name': 'in_progress', 'title': 'In Progress'},
            {'name': 'upcoming', 'title': 'Upcoming'},
            {'name': 'blockers', 'title': 'Blockers'},
        ]
    }


def get_standup_template() -> dict:
    """Get default standup template structure."""
    return {
        'sections': [
            {'name': 'yesterday', 'title': 'Yesterday'},
            {'name': 'today', 'title': 'Today'},
            {'name': 'blockers', 'title': 'Blockers'},
        ]
    }
