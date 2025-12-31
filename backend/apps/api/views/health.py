"""
Health check endpoints.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection


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
    
    # Overall status
    all_ok = all(v == 'ok' for v in checks.values())
    status_code = 200 if all_ok else 503
    
    return Response({
        'status': 'ready' if all_ok else 'not_ready',
        'checks': checks
    }, status=status_code)
