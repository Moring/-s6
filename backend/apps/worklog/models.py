from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Client(models.Model):
    """Client/Employer organization."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_active', 'name']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
        unique_together = [['user', 'name']]

    def __str__(self):
        return f"{self.name}"


class Project(models.Model):
    """Project under a Client."""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_active', 'name']
        indexes = [
            models.Index(fields=['client', 'is_active']),
        ]
        unique_together = [['client', 'name']]

    def __str__(self):
        return f"{self.client.name} - {self.name}"


class Epic(models.Model):
    """Agile Epic (optional, project-scoped)."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='epics')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.project.name} - Epic: {self.name}"


class Feature(models.Model):
    """Agile Feature under an Epic (optional)."""
    epic = models.ForeignKey(Epic, on_delete=models.CASCADE, related_name='features')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.epic.name} - Feature: {self.name}"


class Story(models.Model):
    """Agile Story under a Feature (optional)."""
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name='stories')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Stories'

    def __str__(self):
        return f"{self.feature.name} - Story: {self.name}"


class Task(models.Model):
    """Agile Task under a Story (optional)."""
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='tasks')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.story.name} - Task: {self.name}"


class Sprint(models.Model):
    """Sprint/Iteration (optional, project-scoped)."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sprints')
    name = models.CharField(max_length=200)
    goal = models.TextField(blank=True, help_text="Sprint goal/objective")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.project.name} - {self.name}"


class WorkLog(models.Model):
    """User work log entry with optional organizational context."""
    
    WORK_TYPE_CHOICES = [
        ('delivery', 'Delivery'),
        ('planning', 'Planning'),
        ('incident', 'Incident Response'),
        ('support', 'Support'),
        ('learning', 'Learning/Training'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='worklogs')
    date = models.DateField()
    
    # Organizational hierarchy (all optional)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='worklogs')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='worklogs')
    
    # Agile hierarchy (all optional)
    epic = models.ForeignKey(Epic, on_delete=models.SET_NULL, null=True, blank=True, related_name='worklogs')
    feature = models.ForeignKey(Feature, on_delete=models.SET_NULL, null=True, blank=True, related_name='worklogs')
    story = models.ForeignKey(Story, on_delete=models.SET_NULL, null=True, blank=True, related_name='worklogs')
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name='worklogs')
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name='worklogs')
    
    # Core content
    content = models.TextField(help_text="Work description")
    outcome = models.TextField(blank=True, help_text="What was accomplished")
    work_type = models.CharField(max_length=50, choices=WORK_TYPE_CHOICES, default='delivery')
    
    # Time tracking (optional)
    hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Hours spent")
    
    # Tags and skills
    tags = models.JSONField(default=list, blank=True, help_text="Skills, technologies, keywords")
    
    # Source and enrichment
    source = models.CharField(max_length=50, default='manual')  # manual, email, slack, etc
    metadata = models.JSONField(default=dict, blank=True)
    enrichment_status = models.CharField(max_length=50, default='pending', 
                                        help_text="pending, enriched, reviewed")
    enrichment_suggestions = models.JSONField(default=dict, blank=True)
    
    # Draft support
    is_draft = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', '-date']),
            models.Index(fields=['date']),
            models.Index(fields=['client', '-date']),
            models.Index(fields=['project', '-date']),
            models.Index(fields=['is_draft']),
        ]

    def __str__(self):
        return f"WorkLog {self.date} ({self.id})"


class Attachment(models.Model):
    """Attachment linked to a work log."""
    worklog = models.ForeignKey(WorkLog, on_delete=models.CASCADE, related_name='attachments')
    kind = models.CharField(max_length=50)  # image, document, code, etc
    object_key = models.CharField(max_length=500)  # MinIO object key
    filename = models.CharField(max_length=255)
    description = models.TextField(blank=True, help_text="Short description of attachment")
    size_bytes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Attachment {self.filename} ({self.id})"
