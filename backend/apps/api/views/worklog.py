"""
Worklog API views.
"""
from django.db import models
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from apps.worklog.models import (
    WorkLog, Client, Project, Epic, Feature, Story, Task, Sprint,
    WorkLogSkillSignal, WorkLogBullet, WorkLogPreset, WorkLogReport, WorkLogExternalLink
)
from apps.worklog.serializers import (
    WorkLogSerializer, WorkLogListSerializer, WorkLogCreateUpdateSerializer,
    ClientSerializer, ProjectSerializer,
    EpicSerializer, FeatureSerializer, StorySerializer, TaskSerializer, SprintSerializer,
    WorkLogSkillSignalSerializer, WorkLogBulletSerializer,
    WorkLogPresetSerializer, WorkLogReportSerializer, WorkLogExternalLinkSerializer
)
from apps.jobs.dispatcher import enqueue
from apps.api.rate_limiting import rate_limit, AI_ACTION_RATE_LIMITER


class WorkLogFilter(django_filters.FilterSet):
    """Filters for WorkLog queryset."""
    start_date = django_filters.DateFilter(field_name='occurred_on', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='occurred_on', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = WorkLog
        fields = ['client', 'project', 'epic', 'feature', 'story', 'task', 'sprint', 
                  'work_type', 'status', 'enrichment_status']
    
    def filter_search(self, queryset, name, value):
        """Search across content, outcome, tags, title."""
        return queryset.filter(
            models.Q(content__icontains=value) |
            models.Q(outcome__icontains=value) |
            models.Q(title__icontains=value) |
            models.Q(tags__icontains=value)
        )


class WorkLogListCreateView(generics.ListCreateAPIView):
    """List and create work logs."""
    queryset = WorkLog.objects.all()
    serializer_class = WorkLogListSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = WorkLogFilter
    ordering_fields = ['occurred_on', 'created_at', 'updated_at', 'status']
    ordering = ['-occurred_on', '-created_at']
    
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs.select_related('client', 'project').prefetch_related('attachments')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return WorkLogCreateUpdateSerializer
        return WorkLogListSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user if self.request.user.is_authenticated else None)
        
        # Trigger gamification reward evaluation
        if instance.user:
            try:
                from apps.gamification import services as gamification_services
                gamification_services.trigger_reward_evaluation(instance.id, instance.user.id)
            except ImportError:
                pass
    
    def create(self, request, *args, **kwargs):
        """Override create to return full WorkLogSerializer on success."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return full serializer with id field
        instance = serializer.instance
        output_serializer = WorkLogSerializer(instance)
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class WorkLogDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a work log."""
    queryset = WorkLog.objects.all()
    
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs.select_related(
            'client', 'project', 'epic', 'feature', 'story', 'task', 'sprint'
        ).prefetch_related(
            'attachments', 'external_links', 'skill_signals', 'bullets'
        )
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return WorkLogCreateUpdateSerializer
        return WorkLogSerializer
    
    def perform_update(self, serializer):
        instance = serializer.save()
        
        # Trigger gamification reward evaluation on update
        if instance.user:
            try:
                from apps.gamification import services as gamification_services
                gamification_services.trigger_reward_evaluation(instance.id, instance.user.id)
            except ImportError:
                pass


@rate_limit(AI_ACTION_RATE_LIMITER)
@api_view(['POST'])
def analyze_worklog(request, pk):
    """Enqueue worklog analysis job."""
    try:
        worklog = WorkLog.objects.get(id=pk)
    except WorkLog.DoesNotExist:
        return Response({'error': 'WorkLog not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if not request.user.is_staff and worklog.user != request.user:
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
    
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


# ================================
# Client management views
# ================================

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


# ================================
# Project management views
# ================================

class ProjectListCreateView(generics.ListCreateAPIView):
    """List and create projects."""
    serializer_class = ProjectSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['client', 'is_active']
    search_fields = ['name', 'description', 'role']
    ordering_fields = ['name', 'created_at', 'started_on']
    ordering = ['name']
    
    def get_queryset(self):
        return Project.objects.filter(client__user=self.request.user).select_related('client')


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a project."""
    serializer_class = ProjectSerializer
    
    def get_queryset(self):
        return Project.objects.filter(client__user=self.request.user)


# ================================
# Agile hierarchy views
# ================================

class EpicListCreateView(generics.ListCreateAPIView):
    """List and create epics."""
    serializer_class = EpicSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['project', 'is_active']
    ordering = ['name']
    
    def get_queryset(self):
        return Epic.objects.filter(project__client__user=self.request.user).select_related('project')


class EpicDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an epic."""
    serializer_class = EpicSerializer
    
    def get_queryset(self):
        return Epic.objects.filter(project__client__user=self.request.user)


class FeatureListCreateView(generics.ListCreateAPIView):
    """List and create features."""
    serializer_class = FeatureSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['epic', 'is_active']
    ordering = ['name']
    
    def get_queryset(self):
        return Feature.objects.filter(epic__project__client__user=self.request.user).select_related('epic__project')


class FeatureDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a feature."""
    serializer_class = FeatureSerializer
    
    def get_queryset(self):
        return Feature.objects.filter(epic__project__client__user=self.request.user)


class StoryListCreateView(generics.ListCreateAPIView):
    """List and create stories."""
    serializer_class = StorySerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['feature', 'is_active']
    ordering = ['name']
    
    def get_queryset(self):
        return Story.objects.filter(
            feature__epic__project__client__user=self.request.user
        ).select_related('feature__epic__project')


class StoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a story."""
    serializer_class = StorySerializer
    
    def get_queryset(self):
        return Story.objects.filter(feature__epic__project__client__user=self.request.user)


class TaskListCreateView(generics.ListCreateAPIView):
    """List and create tasks."""
    serializer_class = TaskSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['story', 'is_active']
    ordering = ['name']
    
    def get_queryset(self):
        return Task.objects.filter(
            story__feature__epic__project__client__user=self.request.user
        ).select_related('story__feature__epic__project')


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a task."""
    serializer_class = TaskSerializer
    
    def get_queryset(self):
        return Task.objects.filter(story__feature__epic__project__client__user=self.request.user)


# ================================
# Sprint management views
# ================================

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


# ================================
# Enrichment views (skill signals, bullets, external links)
# ================================

class WorkLogSkillSignalListView(generics.ListCreateAPIView):
    """List and create skill signals for a worklog."""
    serializer_class = WorkLogSkillSignalSerializer
    
    def get_queryset(self):
        worklog_id = self.kwargs.get('worklog_id')
        return WorkLogSkillSignal.objects.filter(
            worklog_id=worklog_id,
            worklog__user=self.request.user
        )
    
    def perform_create(self, serializer):
        worklog_id = self.kwargs.get('worklog_id')
        worklog = WorkLog.objects.get(id=worklog_id, user=self.request.user)
        serializer.save(worklog=worklog)


class WorkLogSkillSignalDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a skill signal."""
    serializer_class = WorkLogSkillSignalSerializer
    
    def get_queryset(self):
        return WorkLogSkillSignal.objects.filter(worklog__user=self.request.user)


class WorkLogBulletListView(generics.ListCreateAPIView):
    """List and create bullets for a worklog."""
    serializer_class = WorkLogBulletSerializer
    
    def get_queryset(self):
        worklog_id = self.kwargs.get('worklog_id')
        return WorkLogBullet.objects.filter(
            worklog_id=worklog_id,
            worklog__user=self.request.user
        )
    
    def perform_create(self, serializer):
        worklog_id = self.kwargs.get('worklog_id')
        worklog = WorkLog.objects.get(id=worklog_id, user=self.request.user)
        serializer.save(worklog=worklog)


class WorkLogBulletDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a bullet."""
    serializer_class = WorkLogBulletSerializer
    
    def get_queryset(self):
        return WorkLogBullet.objects.filter(worklog__user=self.request.user)


class WorkLogExternalLinkListView(generics.ListCreateAPIView):
    """List and create external links for a worklog."""
    serializer_class = WorkLogExternalLinkSerializer
    
    def get_queryset(self):
        worklog_id = self.kwargs.get('worklog_id')
        return WorkLogExternalLink.objects.filter(
            worklog_id=worklog_id,
            worklog__user=self.request.user
        )
    
    def perform_create(self, serializer):
        worklog_id = self.kwargs.get('worklog_id')
        worklog = WorkLog.objects.get(id=worklog_id, user=self.request.user)
        serializer.save(worklog=worklog)


class WorkLogExternalLinkDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an external link."""
    serializer_class = WorkLogExternalLinkSerializer
    
    def get_queryset(self):
        return WorkLogExternalLink.objects.filter(worklog__user=self.request.user)


# ================================
# Preset views
# ================================

class WorkLogPresetListCreateView(generics.ListCreateAPIView):
    """List and create worklog presets."""
    serializer_class = WorkLogPresetSerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ['-is_active', 'name']
    
    def get_queryset(self):
        return WorkLogPreset.objects.filter(user=self.request.user).select_related('client', 'project')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WorkLogPresetDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a worklog preset."""
    serializer_class = WorkLogPresetSerializer
    
    def get_queryset(self):
        return WorkLogPreset.objects.filter(user=self.request.user)


# ================================
# Report views
# ================================

class WorkLogReportListView(generics.ListAPIView):
    """List worklog reports."""
    serializer_class = WorkLogReportSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['client', 'project', 'sprint', 'kind', 'created_via']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return WorkLogReport.objects.filter(user=self.request.user).select_related('client', 'project', 'sprint')


class WorkLogReportDetailView(generics.RetrieveDestroyAPIView):
    """Retrieve or delete a worklog report."""
    serializer_class = WorkLogReportSerializer
    
    def get_queryset(self):
        return WorkLogReport.objects.filter(user=self.request.user)
