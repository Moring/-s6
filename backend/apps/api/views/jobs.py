"""
Jobs API views.
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from apps.jobs.models import Job
from apps.observability.models import Event


@api_view(['GET'])
def job_detail(request, job_id):
    """Get job status and result."""
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'id': str(job.id),
        'type': job.type,
        'status': job.status,
        'trigger': job.trigger,
        'payload': job.payload,
        'result': job.result,
        'error': job.error,
        'retry_count': job.retry_count,
        'created_at': job.created_at,
        'started_at': job.started_at,
        'finished_at': job.finished_at,
    })


@api_view(['GET'])
def job_events(request, job_id):
    """Get job event timeline."""
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    events = job.events.all()
    
    return Response({
        'job_id': str(job.id),
        'events': [
            {
                'timestamp': event.timestamp,
                'level': event.level,
                'source': event.source,
                'message': event.message,
                'data': event.data
            }
            for event in events
        ]
    })
