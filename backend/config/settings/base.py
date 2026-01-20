"""
Base Django settings for AfterResume backend.
"""
import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # Third party
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'django_filters',
    'huey.contrib.djhuey',
    'corsheaders',
    # Core apps
    'apps.tenants',
    'apps.accounts',
    'apps.invitations',
    'apps.auditing',
    'apps.artifacts',
    # Domain apps
    'apps.worklog',
    'apps.skills',
    'apps.reporting',
    'apps.gamification',
    'apps.jobs',
    'apps.observability',
    # Infrastructure apps
    'apps.workers',
    'apps.orchestration',
    'apps.agents',
    'apps.llm',
    'apps.storage',
    'apps.api',
    'apps.system',
    'apps.billing',
    # Frontend UI
    'frontend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'apps.tenants.middleware.TenantMiddleware',
    # Security and observability
    'apps.api.security_middleware.SecurityHeadersMiddleware',
    'apps.api.security_middleware.IPAllowlistMiddleware',
    'apps.api.security_middleware.MaintenanceModeMiddleware',
    'apps.observability.correlation.CorrelationIDMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Production/Docker: use PostgreSQL from environment
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
        }
    except ImportError:
        # Fallback if dj_database_url not installed
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.environ.get('POSTGRES_DB', 'afterresume'),
                'USER': os.environ.get('POSTGRES_USER', 'afterresume'),
                'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'afterresume'),
                'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
                'PORT': os.environ.get('POSTGRES_PORT', '5432'),
            }
        }
else:
    # Development: fallback to SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'ATOMIC_REQUESTS': False,
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

JWT_REFRESH_COOKIE_NAME = os.environ.get('JWT_REFRESH_COOKIE_NAME', 'afterresume_refresh')
JWT_REFRESH_COOKIE_PATH = os.environ.get('JWT_REFRESH_COOKIE_PATH', '/api/auth/')

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=10),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Huey configuration
HUEY = {
    'huey_class': 'huey.RedisHuey',
    'name': 'afterresume',
    'url': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    'immediate': False,  # Process tasks asynchronously
    'consumer': {
        'workers': int(os.environ.get('HUEY_WORKERS', '4')),
        'worker_type': 'thread',
    },
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'correlation_id': {
            '()': 'apps.observability.correlation.CorrelationIDFilter',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} [{correlation_id}] {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['correlation_id'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Security settings
# Service-to-service authentication
SERVICE_TO_SERVICE_SECRET = os.environ.get('SERVICE_TO_SERVICE_SECRET', SECRET_KEY)
SKIP_SERVICE_AUTH = os.environ.get('SKIP_SERVICE_AUTH', 'False') == 'True'

# CORS settings for local frontend development
# Allow requests from the frontend dev server and enable credentials for cookie-based auth
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CORS_ALLOW_CREDENTIALS = True

# Feature flags
MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', 'False') == 'True'
DISABLE_SHARING = os.environ.get('DISABLE_SHARING', 'False') == 'True'

# Admin IP allowlist (comma-separated)
admin_ips = os.environ.get('ADMIN_IP_ALLOWLIST', '')
ADMIN_IP_ALLOWLIST = [ip.strip() for ip in admin_ips.split(',') if ip.strip()]

# CSRF settings
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'False') == 'True'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if os.environ.get('CSRF_TRUSTED_ORIGINS') else []

# MinIO configuration
MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
MINIO_SECURE = os.environ.get('MINIO_SECURE', 'False') == 'True'
MINIO_BUCKET = os.environ.get('MINIO_BUCKET', 'afterresume')

# Tika
TIKA_ENDPOINT = os.environ.get('TIKA_ENDPOINT', 'http://tika:9998')

# LLM configuration
LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'local')
LLM_VLLM_ENDPOINT = os.environ.get('LLM_VLLM_ENDPOINT', 'http://localhost:8000')
LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4')
OLLAMA_ENDPOINT = os.environ.get('OLLAMA_ENDPOINT', 'http://ollama:11434')

# System dashboard
SYSTEM_DASHBOARD_ENABLED = os.environ.get('SYSTEM_DASHBOARD_ENABLED', 'True') == 'True'

# Django sites framework (required by allauth)
SITE_ID = 1

# Allauth configuration
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Allauth configuration
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'  # For MVP, no email verification
LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/login/'

# REST Framework authentication
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'rest_framework_simplejwt.authentication.JWTAuthentication',
    'rest_framework.authentication.SessionAuthentication',
]
REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
    'rest_framework.permissions.IsAuthenticated',
]

# drf-spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'AfterResume API',
    'DESCRIPTION': 'API schema for AfterResume backend',
    'VERSION': os.environ.get('API_VERSION', '0.1.0'),
    # Other settings can be added as needed
}

# Content Security Policy: allow extra hosts (used by SecurityHeadersMiddleware)
# Include jsDelivr so the default Spectacular Swagger UI CDN assets can load.
CSP_EXTRA_SRC = [
    'https://cdn.jsdelivr.net',
]

# Cache configuration (Valkey/Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://valkey:6379/0'),
        'KEY_PREFIX': 'afterresume',
    }
}

# Session Security
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Allow remember me
SESSION_SAVE_EVERY_REQUEST = True  # Sliding window
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'  # True in production
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_NAME = 'afterresume_session'

# CSRF Protection
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'False') == 'True'
CSRF_COOKIE_SAMESITE = 'Lax'

# Rate Limiting Cache (uses Valkey/Redis)

# Stripe configuration
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
