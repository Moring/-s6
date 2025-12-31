"""
Development settings.
"""
from .base import *

DEBUG = True

HUEY['immediate'] = False  # Still async in dev

# Add browsable API in dev
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
]

# More verbose logging in dev
LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['apps']['level'] = 'DEBUG'
