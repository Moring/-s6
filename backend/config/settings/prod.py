"""
Production settings.
"""
from .base import *

DEBUG = False

# Security settings
# Do not force TLS in this deployment (service runs over HTTP).
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Production host and CSRF origin (frontend TLS terminator will present this)
ALLOWED_HOSTS = ['agentic.digimuse.ai','localhost']
CSRF_TRUSTED_ORIGINS = ['https://agentic.digimuse.ai']

# Trust the upstream TLS-terminator's X-Forwarded-Proto header so Django
# can correctly identify secure requests while the backend itself speaks HTTP.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Require proper secret key
if SECRET_KEY == 'django-insecure-dev-key-change-in-production':
    raise ValueError("SECRET_KEY must be set in production")

# Database should be PostgreSQL in production
# Override via DATABASE_URL environment variable if needed

# Running over plain HTTP; do not trust or rely on X-Forwarded headers here.
