"""
System dashboard views.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from .permissions import IsStaffOrSystemEnabled
from .selectors import get_system_overview, get_recent_jobs, get_job_by_id, get_schedules
from .serializers import JobSerializer, ScheduleSerializer, EventSerializer


@api_view(['GET'])
@permission_classes([IsStaffOrSystemEnabled])
def overview(request):
    """Get system overview."""
    data = get_system_overview()
    return Response(data)


@api_view(['GET'])
@permission_classes([IsStaffOrSystemEnabled])
def jobs_list(request):
    """List jobs with filters."""
    job_status = request.query_params.get('status')
    job_type = request.query_params.get('type')
    limit = int(request.query_params.get('limit', 50))
    
    jobs = get_recent_jobs(limit=limit, status=job_status, job_type=job_type)
    serializer = JobSerializer(jobs, many=True)
    
    return Response({
        'count': len(serializer.data),
        'jobs': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsStaffOrSystemEnabled])
def job_detail(request, job_id):
    """Get job detail."""
    job = get_job_by_id(job_id)
    if not job:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = JobSerializer(job)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsStaffOrSystemEnabled])
def job_events(request, job_id):
    """Get job events timeline."""
    job = get_job_by_id(job_id)
    if not job:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    events = job.events.all()
    serializer = EventSerializer(events, many=True)
    
    return Response({
        'job_id': str(job.id),
        'count': len(serializer.data),
        'events': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsStaffOrSystemEnabled])
def schedules_list(request):
    """List schedules."""
    schedules = get_schedules()
    serializer = ScheduleSerializer(schedules, many=True)
    
    return Response({
        'count': len(serializer.data),
        'schedules': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsStaffOrSystemEnabled])
def health(request):
    """System health check."""
    checks = {}
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'
    
    # MinIO check (stub)
    checks['minio'] = 'ok (stub)'
    
    # Redis check (stub)
    checks['redis'] = 'ok (stub)'
    
    all_ok = all(v.startswith('ok') for v in checks.values())
    
    return Response({
        'status': 'healthy' if all_ok else 'unhealthy',
        'checks': checks
    }, status=200 if all_ok else 503)
