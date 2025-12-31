"""
Huey task queue configuration.
"""
from huey.contrib.djhuey import db_task, db_periodic_task

# Re-export decorators for convenience
__all__ = ['db_task', 'db_periodic_task']
