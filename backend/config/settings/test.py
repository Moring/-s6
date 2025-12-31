"""
Test settings.
"""
from .base import *

# Use memory database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'ATOMIC_REQUESTS': False,
    }
}

# Use in-memory Huey for tests
HUEY = {
    'huey_class': 'huey.MemoryHuey',
    'name': 'test-huey',
    'immediate': True,
    'consumer': {'workers': 1, 'worker_type': 'thread'},
}

# Use fake LLM
LLM_PROVIDER = 'local'

# Simpler logging in tests
LOGGING['root']['level'] = 'WARNING'
