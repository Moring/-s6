"""
Tests for worklog client/project hierarchy.
"""
import pytest
from django.contrib.auth import get_user_model
from apps.worklog.models import Client, Project, Sprint, WorkLog
from datetime import date

User = get_user_model()


@pytest.mark.django_db
class TestClientProjectHierarchy:
    """Test client and project management."""
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def client_obj(self, user):
        return Client.objects.create(
            user=user,
            name='Test Client Inc',
            description='Test client description'
        )
    
    @pytest.fixture
    def project(self, client_obj):
        return Project.objects.create(
            client=client_obj,
            name='Test Project',
            description='Test project description'
        )
    
    def test_create_client(self, user):
        """Test creating a client."""
        client = Client.objects.create(
            user=user,
            name='Acme Corp',
            description='Test client'
        )
        assert client.name == 'Acme Corp'
        assert client.user == user
        assert client.is_active
    
    def test_create_project(self, client_obj):
        """Test creating a project under a client."""
        project = Project.objects.create(
            client=client_obj,
            name='Website Redesign',
            description='Redesign company website'
        )
        assert project.name == 'Website Redesign'
        assert project.client == client_obj
        assert project.is_active
    
    def test_create_sprint(self, project):
        """Test creating a sprint under a project."""
        sprint = Sprint.objects.create(
            project=project,
            name='Sprint 1',
            goal='Complete user authentication'
        )
        assert sprint.name == 'Sprint 1'
        assert sprint.project == project
        assert sprint.goal == 'Complete user authentication'
    
    def test_worklog_with_client_project(self, user, client_obj, project):
        """Test creating a worklog entry with client and project."""
        worklog = WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            client=client_obj,
            project=project,
            content='Implemented user login feature',
            outcome='Users can now log in securely',
            work_type='delivery',
            effort_minutes=270,
            tags=['python', 'django', 'authentication']
        )
        assert worklog.client == client_obj
        assert worklog.project == project
        assert worklog.work_type == 'delivery'
        assert worklog.hours == 4.5
        assert 'python' in worklog.tags
    
    def test_worklog_without_hierarchy(self, user):
        """Test creating a minimal worklog entry without hierarchy."""
        worklog = WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            content='Fixed a bug in the API'
        )
        assert worklog.client is None
        assert worklog.project is None
        assert worklog.content == 'Fixed a bug in the API'
        assert worklog.work_type == 'delivery'  # default
    
    def test_client_project_relationships(self, client_obj, project):
        """Test that relationships are properly established."""
        assert project in client_obj.projects.all()
        
        # Create another project
        project2 = Project.objects.create(
            client=client_obj,
            name='Mobile App',
            description='New mobile app project'
        )
        assert client_obj.projects.count() == 2
        assert project2 in client_obj.projects.all()
    
    def test_worklog_query_by_client(self, user, client_obj, project):
        """Test querying worklogs by client."""
        WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            client=client_obj,
            project=project,
            content='Work on project 1'
        )
        WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            content='Personal work'
        )
        
        client_worklogs = WorkLog.objects.filter(client=client_obj)
        assert client_worklogs.count() == 1
        assert client_worklogs.first().content == 'Work on project 1'
    
    def test_worklog_query_by_project(self, user, client_obj, project):
        """Test querying worklogs by project."""
        WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            client=client_obj,
            project=project,
            content='Work on feature A'
        )
        
        # Create another project
        project2 = Project.objects.create(
            client=client_obj,
            name='Project 2'
        )
        WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            client=client_obj,
            project=project2,
            content='Work on feature B'
        )
        
        project_worklogs = WorkLog.objects.filter(project=project)
        assert project_worklogs.count() == 1
        assert project_worklogs.first().content == 'Work on feature A'
    
    def test_draft_worklog(self, user):
        """Test creating a draft worklog entry."""
        draft = WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            content='Work in progress',
            status="draft"
        )
        assert draft.is_draft
        
        # Query only published worklogs
        published = WorkLog.objects.filter(status="ready")
        assert draft not in published
