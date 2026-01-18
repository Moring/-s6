"""
Selectors for worklog queries.
"""
from typing import Optional
from django.contrib.auth import get_user_model
from django.db.models import QuerySet, Prefetch
from datetime import date, datetime
from .models import (
    WorkLog, Client, Project, Epic, Feature, Story, Task, Sprint,
    WorkLogSkillSignal, WorkLogBullet, WorkLogPreset, WorkLogReport,
    Attachment, WorkLogExternalLink
)

User = get_user_model()


# ================================
# WorkLog selectors
# ================================

def list_worklogs(
    user: Optional[User] = None,
    client_id: Optional[int] = None,
    project_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None,
    work_type: Optional[str] = None,
    limit: int = 50
) -> QuerySet[WorkLog]:
    """List work logs with optional filters."""
    qs = WorkLog.objects.all()
    
    if user:
        qs = qs.filter(user=user)
    if client_id:
        qs = qs.filter(client_id=client_id)
    if project_id:
        qs = qs.filter(project_id=project_id)
    if start_date:
        qs = qs.filter(occurred_on__gte=start_date)
    if end_date:
        qs = qs.filter(occurred_on__lte=end_date)
    if status:
        qs = qs.filter(status=status)
    if work_type:
        qs = qs.filter(work_type=work_type)
    
    return qs.select_related('client', 'project').prefetch_related('attachments')[:limit]


def get_worklog(worklog_id: int, user: Optional[User] = None) -> Optional[WorkLog]:
    """Get a single work log by ID with full relations."""
    try:
        qs = WorkLog.objects.select_related(
            'client', 'project', 'epic', 'feature', 'story', 'task', 'sprint'
        ).prefetch_related(
            'attachments', 'external_links', 'skill_signals', 'bullets'
        )
        
        if user:
            qs = qs.filter(user=user)
        
        return qs.get(id=worklog_id)
    except WorkLog.DoesNotExist:
        return None


def get_worklog_with_enrichment(worklog_id: int, user: Optional[User] = None) -> Optional[WorkLog]:
    """Get worklog with all enrichment artifacts."""
    return get_worklog(worklog_id, user=user)


# ================================
# Client and Project selectors
# ================================

def list_clients(user: User, is_active: Optional[bool] = None) -> QuerySet[Client]:
    """List clients for a user."""
    qs = Client.objects.filter(user=user)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def get_client(client_id: int, user: User) -> Optional[Client]:
    """Get a client by ID for a user."""
    try:
        return Client.objects.get(id=client_id, user=user)
    except Client.DoesNotExist:
        return None


def list_projects(
    user: User,
    client_id: Optional[int] = None,
    is_active: Optional[bool] = None
) -> QuerySet[Project]:
    """List projects for a user."""
    qs = Project.objects.filter(client__user=user).select_related('client')
    if client_id:
        qs = qs.filter(client_id=client_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def get_project(project_id: int, user: User) -> Optional[Project]:
    """Get a project by ID for a user."""
    try:
        return Project.objects.select_related('client').get(
            id=project_id, client__user=user
        )
    except Project.DoesNotExist:
        return None


# ================================
# Agile hierarchy selectors
# ================================

def list_epics(user: User, project_id: Optional[int] = None, is_active: Optional[bool] = None) -> QuerySet[Epic]:
    """List epics for a user."""
    qs = Epic.objects.filter(project__client__user=user).select_related('project')
    if project_id:
        qs = qs.filter(project_id=project_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def list_features(user: User, epic_id: Optional[int] = None, is_active: Optional[bool] = None) -> QuerySet[Feature]:
    """List features for a user."""
    qs = Feature.objects.filter(epic__project__client__user=user).select_related('epic__project')
    if epic_id:
        qs = qs.filter(epic_id=epic_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def list_stories(user: User, feature_id: Optional[int] = None, is_active: Optional[bool] = None) -> QuerySet[Story]:
    """List stories for a user."""
    qs = Story.objects.filter(feature__epic__project__client__user=user).select_related('feature__epic__project')
    if feature_id:
        qs = qs.filter(feature_id=feature_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def list_tasks(user: User, story_id: Optional[int] = None, is_active: Optional[bool] = None) -> QuerySet[Task]:
    """List tasks for a user."""
    qs = Task.objects.filter(story__feature__epic__project__client__user=user).select_related('story__feature__epic__project')
    if story_id:
        qs = qs.filter(story_id=story_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def list_sprints(user: User, project_id: Optional[int] = None, is_active: Optional[bool] = None) -> QuerySet[Sprint]:
    """List sprints for a user."""
    qs = Sprint.objects.filter(project__client__user=user).select_related('project')
    if project_id:
        qs = qs.filter(project_id=project_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


# ================================
# Preset and Report selectors
# ================================

def list_presets(user: User, is_active: Optional[bool] = None) -> QuerySet[WorkLogPreset]:
    """List worklog presets for a user."""
    qs = WorkLogPreset.objects.filter(user=user).select_related('client', 'project')
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def get_preset(preset_id: int, user: User) -> Optional[WorkLogPreset]:
    """Get a preset by ID for a user."""
    try:
        return WorkLogPreset.objects.select_related('client', 'project').get(
            id=preset_id, user=user
        )
    except WorkLogPreset.DoesNotExist:
        return None


def list_reports(
    user: User,
    client_id: Optional[int] = None,
    project_id: Optional[int] = None,
    kind: Optional[str] = None,
    limit: int = 50
) -> QuerySet[WorkLogReport]:
    """List worklog reports for a user."""
    qs = WorkLogReport.objects.filter(user=user).select_related('client', 'project', 'sprint')
    if client_id:
        qs = qs.filter(client_id=client_id)
    if project_id:
        qs = qs.filter(project_id=project_id)
    if kind:
        qs = qs.filter(kind=kind)
    return qs[:limit]


def get_report(report_id: int, user: User) -> Optional[WorkLogReport]:
    """Get a report by ID for a user."""
    try:
        return WorkLogReport.objects.select_related('client', 'project', 'sprint').get(
            id=report_id, user=user
        )
    except WorkLogReport.DoesNotExist:
        return None
