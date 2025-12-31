"""
Worklog API views.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.worklog.models import WorkLog
from apps.worklog.serializers import WorkLogSerializer
from apps.jobs.dispatcher import enqueue
from apps.api.rate_limiting import rate_limit, AI_ACTION_RATE_LIMITER


class WorkLogListCreateView(generics.ListCreateAPIView):
    """List and create work logs."""
    queryset = WorkLog.objects.all()
    serializer_class = WorkLogSerializer
    
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs
    
    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user if self.request.user.is_authenticated else None)
        
        # Trigger gamification reward evaluation
        if instance.user:
            from apps.gamification import services as gamification_services
            gamification_services.trigger_reward_evaluation(instance.id, instance.user.id)


class WorkLogDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a work log."""
    queryset = WorkLog.objects.all()
    serializer_class = WorkLogSerializer
    
    def perform_update(self, serializer):
        instance = serializer.save()
        
        # Trigger gamification reward evaluation on update
        if instance.user:
            from apps.gamification import services as gamification_services
            gamification_services.trigger_reward_evaluation(instance.id, instance.user.id)


@rate_limit(AI_ACTION_RATE_LIMITER)
@api_view(['POST'])
def analyze_worklog(request, pk):
    """Enqueue worklog analysis job."""
    try:
        worklog = WorkLog.objects.get(id=pk)
    except WorkLog.DoesNotExist:
        return Response({'error': 'WorkLog not found'}, status=status.HTTP_404_NOT_FOUND)
    
    job = enqueue(
        job_type='worklog.analyze',
        payload={'worklog_id': worklog.id},
        trigger='api',
        user=request.user if request.user.is_authenticated else None
    )
    
    return Response({
        'job_id': str(job.id),
        'status': job.status,
        'message': 'Analysis job enqueued'
    }, status=status.HTTP_202_ACCEPTED)
