"""
Services for worklog business logic.
"""
from datetime import date
from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import (
    WorkLog, Client, Project, Epic, Feature, Story, Task, Sprint,
    WorkLogSkillSignal, WorkLogBullet, WorkLogPreset, WorkLogReport,
    Attachment, WorkLogExternalLink
)

User = get_user_model()


# ================================
# WorkLog CRUD services
# ================================

def create_worklog(
    user: User,
    occurred_on: date,
    content: str,
    title: str = '',
    client_id: Optional[int] = None,
    project_id: Optional[int] = None,
    epic_id: Optional[int] = None,
    feature_id: Optional[int] = None,
    story_id: Optional[int] = None,
    task_id: Optional[int] = None,
    sprint_id: Optional[int] = None,
    work_type: str = 'delivery',
    status: str = 'draft',
    outcome: str = '',
    impact: str = '',
    next_steps: str = '',
    effort_minutes: Optional[int] = None,
    is_billable: bool = False,
    tags: Optional[list] = None,
    source: str = 'manual',
    source_ref: str = '',
    metadata: Optional[dict] = None
) -> WorkLog:
    """Create a new work log entry with validation."""
    worklog = WorkLog(
        user=user,
        occurred_on=occurred_on,
        title=title,
        content=content,
        client_id=client_id,
        project_id=project_id,
        epic_id=epic_id,
        feature_id=feature_id,
        story_id=story_id,
        task_id=task_id,
        sprint_id=sprint_id,
        work_type=work_type,
        status=status,
        outcome=outcome,
        impact=impact,
        next_steps=next_steps,
        effort_minutes=effort_minutes,
        is_billable=is_billable,
        tags=tags or [],
        source=source,
        source_ref=source_ref,
        metadata=metadata or {}
    )
    
    # Full clean includes hierarchy validation and backfilling
    worklog.full_clean()
    worklog.save()
    
    # Trigger gamification reward evaluation
    try:
        from apps.gamification.services import trigger_reward_evaluation
        trigger_reward_evaluation(worklog.id, user.id)
    except ImportError:
        pass  # Gamification not installed yet
    
    return worklog


def update_worklog(worklog_id: int, user: User, **kwargs) -> Optional[WorkLog]:
    """Update a work log entry with validation."""
    try:
        worklog = WorkLog.objects.get(id=worklog_id, user=user)
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(worklog, key):
                setattr(worklog, key, value)
        
        # Full clean includes hierarchy validation and backfilling
        worklog.full_clean()
        worklog.save()
        
        # Trigger gamification reward evaluation on update
        try:
            from apps.gamification.services import trigger_reward_evaluation
            trigger_reward_evaluation(worklog.id, user.id)
        except ImportError:
            pass
        
        return worklog
    except WorkLog.DoesNotExist:
        return None


def delete_worklog(worklog_id: int, user: User) -> bool:
    """Delete a work log entry."""
    try:
        worklog = WorkLog.objects.get(id=worklog_id, user=user)
        worklog.delete()
        return True
    except WorkLog.DoesNotExist:
        return False


# ================================
# Client and Project services
# ================================

def create_client(user: User, name: str, description: str = '', **kwargs) -> Client:
    """Create a client."""
    client = Client(
        user=user,
        name=name,
        description=description,
        **kwargs
    )
    client.full_clean()
    client.save()
    return client


def update_client(client_id: int, user: User, **kwargs) -> Optional[Client]:
    """Update a client."""
    try:
        client = Client.objects.get(id=client_id, user=user)
        for key, value in kwargs.items():
            if hasattr(client, key):
                setattr(client, key, value)
        client.full_clean()
        client.save()
        return client
    except Client.DoesNotExist:
        return None


def create_project(client_id: int, user: User, name: str, description: str = '', **kwargs) -> Project:
    """Create a project under a client."""
    client = Client.objects.get(id=client_id, user=user)
    project = Project(
        client=client,
        name=name,
        description=description,
        **kwargs
    )
    project.full_clean()
    project.save()
    return project


def update_project(project_id: int, user: User, **kwargs) -> Optional[Project]:
    """Update a project."""
    try:
        project = Project.objects.get(id=project_id, client__user=user)
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)
        project.full_clean()
        project.save()
        return project
    except Project.DoesNotExist:
        return None


# ================================
# Agile hierarchy services
# ================================

def create_epic(project_id: int, user: User, name: str, description: str = '') -> Epic:
    """Create an epic under a project."""
    project = Project.objects.get(id=project_id, client__user=user)
    epic = Epic(
        project=project,
        name=name,
        description=description
    )
    epic.full_clean()
    epic.save()
    return epic


def create_feature(epic_id: int, user: User, name: str, description: str = '') -> Feature:
    """Create a feature under an epic."""
    epic = Epic.objects.get(id=epic_id, project__client__user=user)
    feature = Feature(
        epic=epic,
        name=name,
        description=description
    )
    feature.full_clean()
    feature.save()
    return feature


def create_story(feature_id: int, user: User, name: str, description: str = '') -> Story:
    """Create a story under a feature."""
    feature = Feature.objects.get(id=feature_id, epic__project__client__user=user)
    story = Story(
        feature=feature,
        name=name,
        description=description
    )
    story.full_clean()
    story.save()
    return story


def create_task(story_id: int, user: User, name: str, description: str = '') -> Task:
    """Create a task under a story."""
    story = Story.objects.get(id=story_id, feature__epic__project__client__user=user)
    task = Task(
        story=story,
        name=name,
        description=description
    )
    task.full_clean()
    task.save()
    return task


def create_sprint(project_id: int, user: User, name: str, **kwargs) -> Sprint:
    """Create a sprint under a project."""
    project = Project.objects.get(id=project_id, client__user=user)
    sprint = Sprint(
        project=project,
        name=name,
        **kwargs
    )
    sprint.full_clean()
    sprint.save()
    return sprint


# ================================
# Enrichment services
# ================================

def add_skill_signal(
    worklog_id: int,
    user: User,
    name: str,
    kind: str = 'skill',
    confidence: float = 0.5,
    source: str = 'ai',
    status: str = 'suggested',
    evidence: str = '',
    metadata: Optional[dict] = None
) -> WorkLogSkillSignal:
    """Add a skill signal to a worklog."""
    worklog = WorkLog.objects.get(id=worklog_id, user=user)
    signal = WorkLogSkillSignal(
        worklog=worklog,
        name=name,
        kind=kind,
        confidence=confidence,
        source=source,
        status=status,
        evidence=evidence,
        metadata=metadata or {}
    )
    signal.full_clean()
    signal.save()
    return signal


def update_skill_signal_status(signal_id: int, user: User, status: str) -> Optional[WorkLogSkillSignal]:
    """Update the status of a skill signal (accept/reject)."""
    try:
        signal = WorkLogSkillSignal.objects.get(id=signal_id, worklog__user=user)
        signal.status = status
        signal.save()
        return signal
    except WorkLogSkillSignal.DoesNotExist:
        return None


def add_bullet(
    worklog_id: int,
    user: User,
    text: str,
    kind: str = 'note',
    is_ai_generated: bool = False,
    is_selected: bool = False,
    order: int = 0,
    metrics: Optional[dict] = None,
    metadata: Optional[dict] = None
) -> WorkLogBullet:
    """Add a bullet to a worklog."""
    worklog = WorkLog.objects.get(id=worklog_id, user=user)
    bullet = WorkLogBullet(
        worklog=worklog,
        text=text,
        kind=kind,
        is_ai_generated=is_ai_generated,
        is_selected=is_selected,
        order=order,
        metrics=metrics or {},
        metadata=metadata or {}
    )
    bullet.full_clean()
    bullet.save()
    return bullet


def add_external_link(
    worklog_id: int,
    user: User,
    url: str,
    system: str = 'other',
    key: str = '',
    title: str = '',
    metadata: Optional[dict] = None
) -> WorkLogExternalLink:
    """Add an external link to a worklog."""
    worklog = WorkLog.objects.get(id=worklog_id, user=user)
    link = WorkLogExternalLink(
        worklog=worklog,
        system=system,
        key=key,
        url=url,
        title=title,
        metadata=metadata or {}
    )
    link.full_clean()
    link.save()
    return link


# ================================
# Preset services
# ================================

def create_preset(user: User, name: str, **kwargs) -> WorkLogPreset:
    """Create a worklog preset."""
    preset = WorkLogPreset(
        user=user,
        name=name,
        **kwargs
    )
    preset.full_clean()
    preset.save()
    return preset


def update_preset(preset_id: int, user: User, **kwargs) -> Optional[WorkLogPreset]:
    """Update a worklog preset."""
    try:
        preset = WorkLogPreset.objects.get(id=preset_id, user=user)
        for key, value in kwargs.items():
            if hasattr(preset, key):
                setattr(preset, key, value)
        preset.full_clean()
        preset.save()
        return preset
    except WorkLogPreset.DoesNotExist:
        return None


# ================================
# Report services
# ================================

def create_report(
    user: User,
    content_md: str,
    kind: str = 'weekly',
    created_via: str = 'assistant',
    title: str = '',
    **kwargs
) -> WorkLogReport:
    """Create a worklog report."""
    report = WorkLogReport(
        user=user,
        kind=kind,
        created_via=created_via,
        title=title,
        content_md=content_md,
        **kwargs
    )
    report.full_clean()
    report.save()
    return report
