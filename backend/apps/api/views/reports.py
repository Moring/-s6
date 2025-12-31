"""
Reports API views.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.reporting.models import Report
from apps.reporting.serializers import ReportSerializer
from apps.jobs.dispatcher import enqueue


class ReportListView(generics.ListAPIView):
    """List reports."""
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        
        # Filter by kind
        kind = self.request.query_params.get('kind')
        if kind:
            qs = qs.filter(kind=kind)
        
        return qs


@api_view(['POST'])
def generate_report_view(request):
    """Enqueue report generation job."""
    kind = request.data.get('kind', 'status')
    window_days = request.data.get('window_days', 7)
    
    job = enqueue(
        job_type='report.generate',
        payload={
            'user_id': request.user.id if request.user.is_authenticated else None,
            'kind': kind,
            'window_days': window_days
        },
        trigger='api',
        user=request.user if request.user.is_authenticated else None
    )
    
    return Response({
        'job_id': str(job.id),
        'status': job.status,
        'message': f'{kind} report generation enqueued'
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['POST'])
def refresh_resume_view(request):
    """Enqueue resume refresh job."""
    job = enqueue(
        job_type='resume.refresh',
        payload={
            'user_id': request.user.id if request.user.is_authenticated else None
        },
        trigger='api',
        user=request.user if request.user.is_authenticated else None
    )
    
    return Response({
        'job_id': str(job.id),
        'status': job.status,
        'message': 'Resume refresh job enqueued'
    }, status=status.HTTP_202_ACCEPTED)
