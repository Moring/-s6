from __future__ import annotations

from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model

User = get_user_model()


# ----------------------------
# Org / Agile reference models
# ----------------------------

class Client(models.Model):
    """Client/Employer organization (per-user)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clients")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    # Optional convenience fields
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "name"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["user", "name"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="uq_client_user_name"),
        ]

    def __str__(self) -> str:
        return self.name


class Project(models.Model):
    """Project under a Client (per-user via client)."""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    # Optional context for reporting/resume
    role = models.CharField(max_length=200, blank=True, help_text="Your role on this project (optional)")
    started_on = models.DateField(null=True, blank=True)
    ended_on = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "name"]
        indexes = [
            models.Index(fields=["client", "is_active"]),
            models.Index(fields=["client", "name"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["client", "name"], name="uq_project_client_name"),
            models.CheckConstraint(
                condition=Q(ended_on__isnull=True) | Q(started_on__isnull=True) | Q(ended_on__gte=models.F("started_on")),
                name="ck_project_dates",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.client.name} - {self.name}"


class Epic(models.Model):
    """Agile Epic (optional, project-scoped)."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="epics")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["project", "is_active"]),
            models.Index(fields=["project", "name"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="uq_epic_project_name"),
        ]

    def __str__(self) -> str:
        return f"{self.project.name} - Epic: {self.name}"


class Feature(models.Model):
    """Agile Feature under an Epic (optional)."""
    epic = models.ForeignKey(Epic, on_delete=models.CASCADE, related_name="features")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["epic", "is_active"]),
            models.Index(fields=["epic", "name"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["epic", "name"], name="uq_feature_epic_name"),
        ]

    def __str__(self) -> str:
        return f"{self.epic.name} - Feature: {self.name}"


class Story(models.Model):
    """Agile Story under a Feature (optional)."""
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name="stories")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Stories"
        indexes = [
            models.Index(fields=["feature", "is_active"]),
            models.Index(fields=["feature", "name"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["feature", "name"], name="uq_story_feature_name"),
        ]

    def __str__(self) -> str:
        return f"{self.feature.name} - Story: {self.name}"


class Task(models.Model):
    """Agile Task under a Story (optional)."""
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="tasks")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["story", "is_active"]),
            models.Index(fields=["story", "name"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["story", "name"], name="uq_task_story_name"),
        ]

    def __str__(self) -> str:
        return f"{self.story.name} - Task: {self.name}"


class Sprint(models.Model):
    """Sprint/Iteration (optional, project-scoped)."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="sprints")
    name = models.CharField(max_length=200)
    goal = models.TextField(blank=True, help_text="Sprint goal/objective")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["project", "is_active"]),
            models.Index(fields=["project", "-start_date"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="uq_sprint_project_name"),
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(start_date__isnull=True) | Q(end_date__gte=models.F("start_date")),
                name="ck_sprint_dates",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.project.name} - {self.name}"


# ----------------------------
# Work log core
# ----------------------------

class WorkType(models.TextChoices):
    DELIVERY = "delivery", "Delivery"
    PLANNING = "planning", "Planning"
    INCIDENT = "incident", "Incident Response"
    SUPPORT = "support", "Support"
    LEARNING = "learning", "Learning/Training"
    OTHER = "other", "Other"


class WorkLogStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    READY = "ready", "Ready for review"
    FINAL = "final", "Final"
    ARCHIVED = "archived", "Archived"


class EnrichmentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ENRICHED = "enriched", "Enriched"
    REVIEWED = "reviewed", "Reviewed/Accepted"
    REJECTED = "rejected", "Rejected"
    ERROR = "error", "Error"


class WorkSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    ASSISTANT = "assistant", "AI Assistant"
    IMPORT_EMAIL = "email", "Email Import"
    IMPORT_SLACK = "slack", "Slack Import"
    IMPORT_CALENDAR = "calendar", "Calendar Import"
    IMPORT_TICKET = "ticket", "Ticket System Import"
    OTHER = "other", "Other"


class WorkLog(models.Model):
    """
    User work log entry with optional organizational + agile context.

    Designed to support:
      - manual or assistant-driven capture
      - attachments/evidence
      - AI enrichment (skills + resume bullets + summaries)
      - reporting (weekly/monthly/status updates)
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="worklogs")

    occurred_on = models.DateField(db_index=True)

    # Optional: short summary for lists / reports
    title = models.CharField(max_length=240, blank=True)

    # Organizational hierarchy (optional, but validated if present)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name="worklogs")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="worklogs")

    # Agile hierarchy (all optional)
    epic = models.ForeignKey(Epic, on_delete=models.SET_NULL, null=True, blank=True, related_name="worklogs")
    feature = models.ForeignKey(Feature, on_delete=models.SET_NULL, null=True, blank=True, related_name="worklogs")
    story = models.ForeignKey(Story, on_delete=models.SET_NULL, null=True, blank=True, related_name="worklogs")
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name="worklogs")
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="worklogs")

    work_type = models.CharField(max_length=50, choices=WorkType.choices, default=WorkType.DELIVERY)
    status = models.CharField(max_length=20, choices=WorkLogStatus.choices, default=WorkLogStatus.DRAFT)

    # Core content
    content = models.TextField(help_text="What you did (raw notes are fine).")
    outcome = models.TextField(blank=True, help_text="What was accomplished / delivered.")
    impact = models.TextField(blank=True, help_text="Why it mattered (metrics, customer impact, risk reduction).")
    next_steps = models.TextField(blank=True, help_text="What’s next / follow-ups.")

    # Time tracking (optional)
    effort_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Effort in minutes (optional).",
    )
    is_billable = models.BooleanField(default=False)

    # Tags/keywords (lightweight; canonical skills live elsewhere)
    tags = models.JSONField(default=list, blank=True, help_text="Keywords: skills, tech, tools, etc.")

    # Source and enrichment
    source = models.CharField(max_length=30, choices=WorkSource.choices, default=WorkSource.MANUAL)
    source_ref = models.CharField(max_length=200, blank=True, help_text="Optional external reference id (email id, ticket id).")

    metadata = models.JSONField(default=dict, blank=True, help_text="Arbitrary structured metadata.")
    enrichment_status = models.CharField(max_length=20, choices=EnrichmentStatus.choices, default=EnrichmentStatus.PENDING)
    enrichment_suggestions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Assistant suggestions (skills, bullets, summary, etc.).",
    )

    # Optional assistant-produced summary (for reports)
    ai_summary = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_on", "-created_at"]
        indexes = [
            models.Index(fields=["user", "-occurred_on"]),
            models.Index(fields=["status", "-occurred_on"]),
            models.Index(fields=["work_type", "-occurred_on"]),
            models.Index(fields=["client", "-occurred_on"]),
            models.Index(fields=["project", "-occurred_on"]),
            models.Index(fields=["enrichment_status"]),
        ]

    def __str__(self) -> str:
        return f"WorkLog {self.occurred_on} ({self.id})"

    @property
    def hours(self) -> float | None:
        if self.effort_minutes is None:
            return None
        return float(self.effort_minutes) / 60.0

    def clean(self) -> None:
        """
        Enforce tenant + hierarchy consistency and opportunistically backfill implied parents.
        """
        errors = {}

        # --- Tenant validation: selected client/project/etc must belong to this user ---
        if self.client and self.client.user_id != self.user_id:
            errors["client"] = "Client does not belong to this user."

        if self.project:
            if self.project.client.user_id != self.user_id:
                errors["project"] = "Project does not belong to this user."
            # If both are set, they must match
            if self.client and self.project.client_id != self.client_id:
                errors["project"] = "Project does not belong to selected client."

        # --- Backfill client from project if missing ---
        if self.project and not self.client:
            self.client = self.project.client

        # --- Sprint must belong to project (or imply it) ---
        if self.sprint and not self.project:
            self.project = self.sprint.project
            if not self.client:
                self.client = self.project.client
        if self.sprint and self.project and self.sprint.project_id != self.project_id:
            errors["sprint"] = "Sprint does not belong to selected project."

        # --- Backfill / validate agile chain bottom-up (task -> story -> feature -> epic -> project) ---
        if self.task:
            if not self.story:
                self.story = self.task.story
            elif self.task.story_id != self.story_id:
                errors["task"] = "Task does not belong to selected story."

        if self.story:
            if not self.feature:
                self.feature = self.story.feature
            elif self.story.feature_id != self.feature_id:
                errors["story"] = "Story does not belong to selected feature."

        if self.feature:
            if not self.epic:
                self.epic = self.feature.epic
            elif self.feature.epic_id != self.epic_id:
                errors["feature"] = "Feature does not belong to selected epic."

        if self.epic:
            # Epic implies project
            if not self.project:
                self.project = self.epic.project
                if not self.client:
                    self.client = self.project.client
            elif self.epic.project_id != self.project_id:
                errors["epic"] = "Epic does not belong to selected project."

        # If project is set, ensure any agile refs ultimately align to it (after backfills)
        if self.project:
            if self.epic and self.epic.project_id != self.project_id:
                errors["epic"] = "Epic does not belong to selected project."
            if self.feature and self.feature.epic.project_id != self.project_id:
                errors["feature"] = "Feature does not belong to selected project."
            if self.story and self.story.feature.epic.project_id != self.project_id:
                errors["story"] = "Story does not belong to selected project."
            if self.task and self.task.story.feature.epic.project_id != self.project_id:
                errors["task"] = "Task does not belong to selected project."

        if errors:
            raise ValidationError(errors)

        super().clean()

    def save(self, *args, **kwargs):
        """
        Default to validating on save (handy for scripts/admin).
        Pass validate=False to skip if you're bulk-loading.
        """
        validate = kwargs.pop("validate", True)
        if validate:
            self.full_clean()
        return super().save(*args, **kwargs)


# ----------------------------
# Enrichment artifacts (skills + bullets)
# ----------------------------

class SignalSource(models.TextChoices):
    AI = "ai", "AI"
    MANUAL = "manual", "Manual"
    IMPORT = "import", "Import"


class SignalStatus(models.TextChoices):
    SUGGESTED = "suggested", "Suggested"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"


class SkillKind(models.TextChoices):
    SKILL = "skill", "Skill"
    TECHNOLOGY = "technology", "Technology"
    TOOL = "tool", "Tool"
    METHOD = "method", "Method"
    DOMAIN = "domain", "Domain"


class WorkLogSkillSignal(models.Model):
    """
    Lightweight skill/keyword signals extracted from a WorkLog.
    Canonical Skill objects can live in a separate skills app; this keeps worklog decoupled.
    """
    worklog = models.ForeignKey(WorkLog, on_delete=models.CASCADE, related_name="skill_signals")
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=SkillKind.choices, default=SkillKind.SKILL)

    confidence = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="0.0–1.0 confidence (primarily for AI-suggested signals).",
    )
    source = models.CharField(max_length=20, choices=SignalSource.choices, default=SignalSource.AI)
    status = models.CharField(max_length=20, choices=SignalStatus.choices, default=SignalStatus.SUGGESTED)

    evidence = models.TextField(blank=True, help_text="Optional snippet/justification for why this was suggested.")
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-confidence", "name"]
        indexes = [
            models.Index(fields=["worklog"]),
            models.Index(fields=["name"]),
            models.Index(fields=["kind"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["worklog", "name", "kind"], name="uq_worklog_skill_signal"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.kind})"


class BulletKind(models.TextChoices):
    NOTE = "note", "Note"
    STATUS_HIGHLIGHT = "status", "Status highlight"
    RESUME_BULLET = "resume", "Resume bullet"


class WorkLogBullet(models.Model):
    """
    Bullets derived from a WorkLog.
    Use RESUME_BULLET to feed the Live Resume builder.
    """
    worklog = models.ForeignKey(WorkLog, on_delete=models.CASCADE, related_name="bullets")
    kind = models.CharField(max_length=20, choices=BulletKind.choices, default=BulletKind.NOTE)

    text = models.TextField()
    is_ai_generated = models.BooleanField(default=False)
    is_selected = models.BooleanField(default=False, help_text="Selected for use in a report/resume/etc.")
    order = models.PositiveIntegerField(default=0)

    metrics = models.JSONField(default=dict, blank=True, help_text="Optional structured metrics (%, $, latency, etc.).")
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]
        indexes = [
            models.Index(fields=["worklog", "kind"]),
            models.Index(fields=["kind", "is_selected"]),
        ]

    def __str__(self) -> str:
        return f"Bullet {self.kind} ({self.id})"


# ----------------------------
# Presets / templates for faster capture (assistant-friendly)
# ----------------------------

class WorkLogPreset(models.Model):
    """
    User-defined preset used by the assistant or the UI to reduce friction:
      - default work type
      - default tags
      - optional scoped client/project
      - a prompt/outline for the assistant intake
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="worklog_presets")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name="presets")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="presets")

    default_work_type = models.CharField(max_length=50, choices=WorkType.choices, default=WorkType.DELIVERY)
    default_tags = models.JSONField(default=list, blank=True)

    intake_prompt = models.TextField(
        blank=True,
        help_text="Optional prompt/outline the assistant uses to ask questions or structure the entry.",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "name"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["user", "name"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="uq_worklog_preset_user_name"),
        ]

    def clean(self) -> None:
        errors = {}

        if self.client and self.client.user_id != self.user_id:
            errors["client"] = "Client does not belong to this user."

        if self.project:
            if self.project.client.user_id != self.user_id:
                errors["project"] = "Project does not belong to this user."
            if self.client and self.project.client_id != self.client_id:
                errors["project"] = "Project does not belong to selected client."

        if errors:
            raise ValidationError(errors)
        super().clean()

    def __str__(self) -> str:
        return self.name


# ----------------------------
# Reports generated from work logs (optional persistence)
# ----------------------------

class ReportKind(models.TextChoices):
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    SPRINT = "sprint", "Sprint"
    CUSTOM = "custom", "Custom"


class CreatedVia(models.TextChoices):
    MANUAL = "manual", "Manual"
    ASSISTANT = "assistant", "AI Assistant"
    SCHEDULED = "scheduled", "Scheduled"


class WorkLogReport(models.Model):
    """
    Stored output for status reports (so users can re-open/share/export).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="worklog_reports")

    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")

    kind = models.CharField(max_length=20, choices=ReportKind.choices, default=ReportKind.WEEKLY)
    created_via = models.CharField(max_length=20, choices=CreatedVia.choices, default=CreatedVia.ASSISTANT)

    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    title = models.CharField(max_length=240, blank=True)
    content_md = models.TextField(help_text="Markdown content of the report.")
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["kind", "-created_at"]),
            models.Index(fields=["client", "-created_at"]),
            models.Index(fields=["project", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(period_end__isnull=True) | Q(period_start__isnull=True) | Q(period_end__gte=models.F("period_start")),
                name="ck_worklog_report_dates",
            ),
        ]

    def clean(self) -> None:
        errors = {}
        if self.client and self.client.user_id != self.user_id:
            errors["client"] = "Client does not belong to this user."

        if self.project:
            if self.project.client.user_id != self.user_id:
                errors["project"] = "Project does not belong to this user."
            if self.client and self.project.client_id != self.client_id:
                errors["project"] = "Project does not belong to selected client."

        if self.sprint:
            if self.sprint.project.client.user_id != self.user_id:
                errors["sprint"] = "Sprint does not belong to this user."
            if self.project and self.sprint.project_id != self.project_id:
                errors["sprint"] = "Sprint does not belong to selected project."

        if errors:
            raise ValidationError(errors)

        super().clean()

    def __str__(self) -> str:
        return self.title or f"{self.kind} report ({self.id})"


# ----------------------------
# Attachments / evidence
# ----------------------------

class AttachmentKind(models.TextChoices):
    IMAGE = "image", "Image"
    DOCUMENT = "document", "Document"
    CODE = "code", "Code"
    AUDIO = "audio", "Audio"
    VIDEO = "video", "Video"
    OTHER = "other", "Other"


class StorageProvider(models.TextChoices):
    MINIO = "minio", "MinIO/S3"
    LOCAL = "local", "Local"
    OTHER = "other", "Other"


class Attachment(models.Model):
    """Attachment linked to a work log (stored in MinIO/S3 or similar)."""
    worklog = models.ForeignKey(WorkLog, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="uploaded_worklog_attachments")

    kind = models.CharField(max_length=20, choices=AttachmentKind.choices, default=AttachmentKind.DOCUMENT)
    storage_provider = models.CharField(max_length=20, choices=StorageProvider.choices, default=StorageProvider.MINIO)

    object_key = models.CharField(max_length=500, help_text="Object key/path in the storage backend.")
    filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=120, blank=True)

    description = models.TextField(blank=True, help_text="Short description of attachment")
    size_bytes = models.BigIntegerField(default=0, validators=[MinValueValidator(0)])

    checksum_sha256 = models.CharField(max_length=64, blank=True, help_text="Optional SHA-256 checksum hex.")

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["worklog", "-created_at"]),
            models.Index(fields=["kind"]),
        ]

    def __str__(self) -> str:
        return f"Attachment {self.filename} ({self.id})"


# ----------------------------
# Optional: external links (tickets/PRs/etc.) tied to a WorkLog
# ----------------------------

class ExternalSystem(models.TextChoices):
    JIRA = "jira", "Jira"
    GITHUB = "github", "GitHub"
    GITLAB = "gitlab", "GitLab"
    LINEAR = "linear", "Linear"
    ASANA = "asana", "Asana"
    OTHER = "other", "Other"


class WorkLogExternalLink(models.Model):
    worklog = models.ForeignKey(WorkLog, on_delete=models.CASCADE, related_name="external_links")
    system = models.CharField(max_length=20, choices=ExternalSystem.choices, default=ExternalSystem.OTHER)
    key = models.CharField(max_length=120, blank=True, help_text="Ticket/issue/PR key (optional).")
    url = models.URLField()
    title = models.CharField(max_length=240, blank=True)

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["worklog", "-created_at"]),
            models.Index(fields=["system"]),
            models.Index(fields=["key"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["worklog", "url"], name="uq_worklog_external_link_url"),
        ]

    def __str__(self) -> str:
        return self.title or self.url

