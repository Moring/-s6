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

# Use local memory cache to avoid external services in tests.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Skip MinIO checks in readyz during tests.
MINIO_HEALTHCHECK_SKIP = True

# Use fake LLM
LLM_PROVIDER = 'local'

# Simpler logging in tests
LOGGING['root']['level'] = 'WARNING'
