"""
Development settings.
"""
from .base import *

DEBUG = True

# More verbose logging in dev
LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['apps']['level'] = 'DEBUG'
