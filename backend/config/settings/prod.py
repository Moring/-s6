"""
Production settings.
"""
from .base import *

DEBUG = False

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Require proper secret key
if SECRET_KEY == 'django-insecure-dev-key-change-in-production':
    raise ValueError("SECRET_KEY must be set in production")

# Database should be PostgreSQL in production
# Override via DATABASE_URL environment variable if needed
