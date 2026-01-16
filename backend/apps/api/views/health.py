"""
Health check endpoints.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
from django.db import connection
from apps.storage.minio import get_minio_client
from django.conf import settings as django_settings


@api_view(['GET'])
@permission_classes([AllowAny])
def healthz(request):
    """Basic health check."""
    return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([AllowAny])
def readyz(request):
    """Readiness check with dependency verification."""
    checks = {}
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'
    
    # MinIO check
    if getattr(settings, 'MINIO_HEALTHCHECK_SKIP', False):
        checks['minio'] = 'skipped'
    else:
        try:
            minio_client = get_minio_client()
            if minio_client.health_check():
                checks['minio'] = 'ok'
            else:
                checks['minio'] = 'error: bucket not accessible'
        except Exception as e:
            checks['minio'] = f'error: {str(e)}'
    
    # Overall status
    # Container statuses (via Docker) - optional
    try:
        # Lazy import so tests / environments without docker don't fail
        import docker

        docker_client = docker.from_env()
        # Default list of container names to check (matches docker-compose container_name fields)
        default_names = [
            'afterresume-backend-init',
            'afterresume-backend-api',
            'afterresume-backend-worker',
            'afterresume-postgres',
            'afterresume-valkey',
            'afterresume-minio',
            'afterresume-minio-init',
            'afterresume-ollama',
            'afterresume-tika',
            'afterresume-chroma',
        ]
        names = getattr(django_settings, 'DOCKER_CONTAINERS_TO_CHECK', default_names)
        container_statuses = {}
        for name in names:
            try:
                c = docker_client.containers.get(name)
                # docker-py's Container.status gives 'running', 'exited', etc.
                container_statuses[name] = c.status
            except docker.errors.NotFound:
                container_statuses[name] = 'not_found'
            except Exception as e:
                container_statuses[name] = f'error: {str(e)}'
        checks['containers'] = container_statuses
    except Exception as e:
        # Docker not available or import failed
        checks['containers'] = {'docker_client': f'unavailable: {str(e)}'}

    def _is_ok(val):
        if isinstance(val, dict):
            # For container dict, consider 'running' or 'skipped' as ok
            return all(v in ['running', 'skipped'] for v in val.values())
        return val in ['ok', 'skipped']

    all_ok = all(_is_ok(v) for v in checks.values())
    status_code = 200 if all_ok else 503
    
    return Response({
        'status': 'ready' if all_ok else 'not_ready',
        'checks': checks
    }, status=status_code)
