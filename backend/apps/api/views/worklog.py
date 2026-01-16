"""
Worklog API views.
"""
from django.db import models
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from apps.worklog.models import (
    WorkLog, Client, Project, Epic, Feature, Story, Task, Sprint
)
from apps.worklog.serializers import (
    WorkLogSerializer, WorkLogListSerializer, ClientSerializer, ProjectSerializer,
    EpicSerializer, FeatureSerializer, StorySerializer, TaskSerializer, SprintSerializer
)
from apps.jobs.dispatcher import enqueue
from apps.api.rate_limiting import rate_limit, AI_ACTION_RATE_LIMITER


class WorkLogFilter(django_filters.FilterSet):
    """Filters for WorkLog queryset."""
    start_date = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = WorkLog
        fields = ['client', 'project', 'epic', 'feature', 'story', 'task', 'sprint', 
                  'work_type', 'is_draft']
    
    def filter_search(self, queryset, name, value):
        """Search across content, outcome, and tags."""
        return queryset.filter(
            models.Q(content__icontains=value) |
            models.Q(outcome__icontains=value) |
            models.Q(tags__icontains=value)
        )


class WorkLogListCreateView(generics.ListCreateAPIView):
    """List and create work logs."""
    queryset = WorkLog.objects.all()
    serializer_class = WorkLogListSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = WorkLogFilter
    ordering_fields = ['date', 'created_at', 'updated_at']
    ordering = ['-date', '-created_at']
    
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs.select_related('client', 'project').prefetch_related('attachments')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return WorkLogSerializer
        return WorkLogListSerializer
    
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
    
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs.select_related('client', 'project', 'epic', 'feature', 'story', 'task', 'sprint')
    
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


# Client management views
class ClientListCreateView(generics.ListCreateAPIView):
    """List and create clients."""
    serializer_class = ClientSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        return Client.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ClientDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a client."""
    serializer_class = ClientSerializer
    
    def get_queryset(self):
        return Client.objects.filter(user=self.request.user)


# Project management views
class ProjectListCreateView(generics.ListCreateAPIView):
    """List and create projects."""
    serializer_class = ProjectSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['client', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        return Project.objects.filter(client__user=self.request.user).select_related('client')


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a project."""
    serializer_class = ProjectSerializer
    
    def get_queryset(self):
        return Project.objects.filter(client__user=self.request.user)


# Sprint management views
class SprintListCreateView(generics.ListCreateAPIView):
    """List and create sprints."""
    serializer_class = SprintSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['project', 'is_active']
    ordering_fields = ['start_date', 'name']
    ordering = ['-start_date']
    
    def get_queryset(self):
        return Sprint.objects.filter(project__client__user=self.request.user).select_related('project')


class SprintDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a sprint."""
    serializer_class = SprintSerializer
    
    def get_queryset(self):
        return Sprint.objects.filter(project__client__user=self.request.user)
