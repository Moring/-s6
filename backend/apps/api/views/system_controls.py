"""
System controls and switches admin view.
Provides operational dashboard for managing feature flags and incident response.
"""
from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from apps.api.feature_flags import (
    SHARING_ENABLED, EXPORTS_ENABLED, AI_WORKFLOWS_ENABLED,
    EMAIL_NOTIFICATIONS_ENABLED, STRIPE_ENABLED
)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def system_controls_view(request):
    """
    Get current system controls and feature flags status.
    
    GET /api/admin/system-controls/
    
    Returns:
        - Incident switches (maintenance mode, disable sharing)
        - Feature flags (sharing, exports, AI workflows, email, stripe)
        - Rate limiting status
        - Service health indicators
    """
    # Environment-level switches
    env_switches = {
        'maintenance_mode': getattr(settings, 'MAINTENANCE_MODE', False),
        'disable_sharing': getattr(settings, 'DISABLE_SHARING', False),
        'skip_service_auth': getattr(settings, 'SKIP_SERVICE_AUTH', False),
        'debug_mode': settings.DEBUG,
    }
    
    # Feature flags (cache-based, dynamic)
    feature_flags = {
        'sharing_enabled': SHARING_ENABLED.is_enabled(),
        'exports_enabled': EXPORTS_ENABLED.is_enabled(),
        'ai_workflows_enabled': AI_WORKFLOWS_ENABLED.is_enabled(),
        'email_notifications_enabled': EMAIL_NOTIFICATIONS_ENABLED.is_enabled(),
        'stripe_enabled': STRIPE_ENABLED.is_enabled(),
    }
    
    # LLM provider status
    llm_config = {
        'provider': getattr(settings, 'LLM_PROVIDER', 'local'),
        'model': getattr(settings, 'LLM_MODEL_NAME', 'unknown'),
    }
    
    # Database connections
    try:
        from django.db import connection
        connection.ensure_connection()
        db_healthy = True
    except Exception:
        db_healthy = False
    
    # Cache connection
    try:
        cache.get('health_check')
        cache_healthy = True
    except Exception:
        cache_healthy = False
    
    health = {
        'database': 'healthy' if db_healthy else 'unhealthy',
        'cache': 'healthy' if cache_healthy else 'unhealthy',
    }
    
    return Response({
        'env_switches': env_switches,
        'feature_flags': feature_flags,
        'llm_config': llm_config,
        'health': health,
        'timestamp': cache.get('system_controls_last_updated', 'never'),
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def toggle_feature_flag(request):
    """
    Toggle a feature flag dynamically.
    
    POST /api/admin/system-controls/feature-flag/
    Body: {
        "flag": "sharing" | "exports" | "ai_workflows" | "email_notifications" | "stripe",
        "enabled": true | false,
        "ttl": 3600  # optional, seconds
    }
    """
    flag_name = request.data.get('flag')
    enabled = request.data.get('enabled')
    ttl = request.data.get('ttl')
    
    if not flag_name or enabled is None:
        return Response({
            'error': 'Missing required fields: flag, enabled'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Map flag names to objects
    flags = {
        'sharing': SHARING_ENABLED,
        'exports': EXPORTS_ENABLED,
        'ai_workflows': AI_WORKFLOWS_ENABLED,
        'email_notifications': EMAIL_NOTIFICATIONS_ENABLED,
        'stripe': STRIPE_ENABLED,
    }
    
    flag_obj = flags.get(flag_name)
    if not flag_obj:
        return Response({
            'error': f'Invalid flag name: {flag_name}',
            'valid_flags': list(flags.keys())
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Toggle flag
    if enabled:
        flag_obj.enable(ttl=ttl)
    else:
        flag_obj.disable(ttl=ttl)
    
    # Update last modified timestamp
    from django.utils import timezone
    cache.set('system_controls_last_updated', timezone.now().isoformat(), 86400)
    
    return Response({
        'message': f'Feature flag {flag_name} {"enabled" if enabled else "disabled"}',
        'flag': flag_name,
        'enabled': flag_obj.is_enabled(),
        'ttl': ttl
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def failed_jobs_view(request):
    """
    Get list of failed jobs for visibility.
    
    GET /api/admin/failed-jobs/?limit=50
    """
    from apps.jobs.models import Job
    
    limit = int(request.query_params.get('limit', 50))
    
    failed_jobs = Job.objects.filter(status='failed').order_by('-finished_at')[:limit]
    
    jobs_data = []
    for job in failed_jobs:
        jobs_data.append({
            'id': str(job.id),
            'type': job.type,
            'status': job.status,
            'error': job.error,
            'created_at': job.created_at.isoformat(),
            'finished_at': job.finished_at.isoformat() if job.finished_at else None,
            'retry_count': job.retry_count,
            'user_id': job.user_id,
        })
    
    return Response({
        'failed_jobs': jobs_data,
        'count': len(jobs_data),
        'total_failed': Job.objects.filter(status='failed').count(),
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def retry_failed_job(request, job_id):
    """
    Retry a failed job.
    
    POST /api/admin/failed-jobs/<job_id>/retry/
    """
    from apps.jobs.models import Job
    from apps.jobs.dispatcher import enqueue
    
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return Response({
            'error': 'Job not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if job.status != 'failed':
        return Response({
            'error': 'Can only retry failed jobs',
            'current_status': job.status
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create new job with same payload
    new_job = enqueue(
        job_type=job.type,
        payload=job.payload,
        user=job.user
    )
    
    return Response({
        'message': 'Job retried successfully',
        'original_job_id': str(job.id),
        'new_job_id': str(new_job.id),
        'new_job_status': new_job.status,
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def rate_limit_status_view(request):
    """
    Get rate limiting statistics.
    
    GET /api/admin/rate-limits/
    """
    from apps.api.rate_limiting import (
        AUTH_RATE_LIMITER, SIGNUP_RATE_LIMITER, PASSKEY_RATE_LIMITER,
        SHARE_LINK_RATE_LIMITER, EXPORT_RATE_LIMITER, AI_ACTION_RATE_LIMITER,
        REPORT_RATE_LIMITER
    )
    
    limiters = {
        'auth': AUTH_RATE_LIMITER,
        'signup': SIGNUP_RATE_LIMITER,
        'passkey': PASSKEY_RATE_LIMITER,
        'share_link': SHARE_LINK_RATE_LIMITER,
        'export': EXPORT_RATE_LIMITER,
        'ai_action': AI_ACTION_RATE_LIMITER,
        'report': REPORT_RATE_LIMITER,
    }
    
    status_data = {}
    for name, limiter in limiters.items():
        status_data[name] = {
            'max_requests': limiter.max_requests,
            'window_seconds': limiter.window_seconds,
            'description': f'{limiter.max_requests} requests per {limiter.window_seconds}s',
        }
    
    return Response({
        'rate_limiters': status_data,
        'note': 'Use GET /api/admin/rate-limits/reset/?identifier=<ip> to reset specific limit'
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reset_rate_limit(request):
    """
    Reset rate limit for a specific identifier (IP or user).
    
    POST /api/admin/rate-limits/reset/
    Body: {
        "limiter": "auth" | "signup" | "passkey" | "share_link" | "export" | "ai_action" | "report",
        "identifier": "192.168.1.1" or "user-123"
    }
    """
    from apps.api.rate_limiting import (
        AUTH_RATE_LIMITER, SIGNUP_RATE_LIMITER, PASSKEY_RATE_LIMITER,
        SHARE_LINK_RATE_LIMITER, EXPORT_RATE_LIMITER, AI_ACTION_RATE_LIMITER,
        REPORT_RATE_LIMITER
    )
    
    limiter_name = request.data.get('limiter')
    identifier = request.data.get('identifier')
    
    if not limiter_name or not identifier:
        return Response({
            'error': 'Missing required fields: limiter, identifier'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    limiters = {
        'auth': AUTH_RATE_LIMITER,
        'signup': SIGNUP_RATE_LIMITER,
        'passkey': PASSKEY_RATE_LIMITER,
        'share_link': SHARE_LINK_RATE_LIMITER,
        'export': EXPORT_RATE_LIMITER,
        'ai_action': AI_ACTION_RATE_LIMITER,
        'report': REPORT_RATE_LIMITER,
    }
    
    limiter = limiters.get(limiter_name)
    if not limiter:
        return Response({
            'error': f'Invalid limiter name: {limiter_name}',
            'valid_limiters': list(limiters.keys())
        }, status=status.HTTP_400_BAD_REQUEST)
    
    limiter.reset(identifier)
    
    return Response({
        'message': f'Rate limit reset for {identifier} on {limiter_name}',
        'limiter': limiter_name,
        'identifier': identifier,
    })
