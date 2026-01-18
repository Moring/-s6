"""
Comprehensive tests for updated worklog models, serializers, views, and services.
"""
import pytest
from datetime import date, datetime, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status

from apps.worklog.models import (
    Client, Project, Epic, Feature, Story, Task, Sprint,
    WorkLog, WorkLogSkillSignal, WorkLogBullet, WorkLogPreset, WorkLogReport,
    Attachment, WorkLogExternalLink,
    WorkLogStatus, WorkType, EnrichmentStatus, SignalStatus, BulletKind
)
from apps.worklog import services, selectors

User = get_user_model()


@pytest.mark.django_db
class TestWorklogModels:
    """Test worklog domain models."""
    
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
            description='Test client'
        )
    
    @pytest.fixture
    def project(self, client_obj):
        return Project.objects.create(
            client=client_obj,
            name='Test Project',
            description='Test project',
            role='Senior Developer'
        )
    
    @pytest.fixture
    def epic(self, project):
        return Epic.objects.create(
            project=project,
            name='User Management',
            description='Complete user management system'
        )
    
    @pytest.fixture
    def feature(self, epic):
        return Feature.objects.create(
            epic=epic,
            name='Authentication',
            description='User login and registration'
        )
    
    @pytest.fixture
    def story(self, feature):
        return Story.objects.create(
            feature=feature,
            name='Login Flow',
            description='Implement login functionality'
        )
    
    @pytest.fixture
    def task(self, story):
        return Task.objects.create(
            story=story,
            name='Create login form',
            description='Design and implement login form UI'
        )
    
    @pytest.fixture
    def sprint(self, project):
        return Sprint.objects.create(
            project=project,
            name='Sprint 1',
            goal='Foundation',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=14)
        )
    
    @pytest.fixture
    def worklog(self, user, client_obj, project):
        return WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            title='Implemented login',
            client=client_obj,
            project=project,
            work_type=WorkType.DELIVERY,
            status=WorkLogStatus.READY,
            content='Worked on user authentication',
            outcome='Login feature complete',
            effort_minutes=240,
            tags=['python', 'django']
        )
    
    def test_client_creation(self, user):
        """Test client creation with all fields."""
        client = Client.objects.create(
            user=user,
            name='Acme Corp',
            description='Test client',
            website='https://acme.com',
            notes='Important client'
        )
        assert client.name == 'Acme Corp'
        assert client.user == user
        assert client.is_active
        assert client.website == 'https://acme.com'
    
    def test_project_with_dates(self, client_obj):
        """Test project with start and end dates."""
        project = Project.objects.create(
            client=client_obj,
            name='Q1 Project',
            started_on=date(2024, 1, 1),
            ended_on=date(2024, 3, 31),
            role='Tech Lead'
        )
        assert project.started_on == date(2024, 1, 1)
        assert project.ended_on == date(2024, 3, 31)
        assert project.role == 'Tech Lead'
    
    def test_project_date_validation(self, client_obj):
        """Test that end date cannot be before start date."""
        with pytest.raises(ValidationError):
            project = Project(
                client=client_obj,
                name='Invalid Project',
                started_on=date(2024, 3, 31),
                ended_on=date(2024, 1, 1)
            )
            project.full_clean()
    
    def test_agile_hierarchy(self, project, epic, feature, story, task):
        """Test complete agile hierarchy."""
        assert epic.project == project
        assert feature.epic == epic
        assert story.feature == feature
        assert task.story == story
        
        # Test string representations
        assert 'User Management' in str(epic)
        assert 'Authentication' in str(feature)
        assert 'Login Flow' in str(story)
        assert 'Create login form' in str(task)
    
    def test_worklog_with_hierarchy(self, user, client_obj, project, task):
        """Test worklog with full agile hierarchy."""
        worklog = WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            title='Completed login form',
            client=client_obj,
            project=project,
            task=task,
            content='Built the UI and validation',
            outcome='Form ready for testing',
            impact='Users can now log in',
            next_steps='Add password reset',
            effort_minutes=180,
            tags=['ui', 'forms']
        )
        
        # Test backfilling - should automatically set epic, feature, story
        assert worklog.epic == task.story.feature.epic
        assert worklog.feature == task.story.feature
        assert worklog.story == task.story
        assert worklog.task == task
    
    def test_worklog_status_and_types(self, user):
        """Test worklog status and work types."""
        draft = WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            content='Draft entry',
            status=WorkLogStatus.DRAFT
        )
        assert draft.status == WorkLogStatus.DRAFT
        
        incident = WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            content='Fixed production issue',
            work_type=WorkType.INCIDENT,
            status=WorkLogStatus.FINAL
        )
        assert incident.work_type == WorkType.INCIDENT
        assert incident.status == WorkLogStatus.FINAL
    
    def test_worklog_hours_property(self, user):
        """Test hours calculation from effort_minutes."""
        worklog = WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            content='Test',
            effort_minutes=150
        )
        assert worklog.hours == 2.5
        
        # Test None case
        worklog2 = WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            content='Test 2'
        )
        assert worklog2.hours is None
    
    def test_skill_signal(self, worklog):
        """Test skill signal creation."""
        signal = WorkLogSkillSignal.objects.create(
            worklog=worklog,
            name='Django',
            kind='technology',
            confidence=0.95,
            source='ai',
            status=SignalStatus.SUGGESTED,
            evidence='Used Django ORM and views'
        )
        assert signal.name == 'Django'
        assert signal.confidence == 0.95
        assert signal.status == SignalStatus.SUGGESTED
    
    def test_worklog_bullet(self, worklog):
        """Test bullet creation."""
        bullet = WorkLogBullet.objects.create(
            worklog=worklog,
            kind=BulletKind.RESUME_BULLET,
            text='Implemented secure authentication system',
            is_ai_generated=True,
            is_selected=True,
            metrics={'users': 1000, 'reduction': '50%'}
        )
        assert bullet.kind == BulletKind.RESUME_BULLET
        assert bullet.is_ai_generated
        assert bullet.metrics['users'] == 1000
    
    def test_worklog_preset(self, user, client_obj, project):
        """Test preset creation."""
        preset = WorkLogPreset.objects.create(
            user=user,
            name='Daily Standup',
            description='Quick daily update',
            client=client_obj,
            project=project,
            default_work_type=WorkType.DELIVERY,
            default_tags=['daily', 'standup'],
            intake_prompt='What did you work on today?'
        )
        assert preset.name == 'Daily Standup'
        assert preset.default_work_type == WorkType.DELIVERY
        assert 'daily' in preset.default_tags
    
    def test_worklog_report(self, user, client_obj, project):
        """Test report creation."""
        report = WorkLogReport.objects.create(
            user=user,
            client=client_obj,
            project=project,
            kind='weekly',
            created_via='assistant',
            period_start=date.today() - timedelta(days=7),
            period_end=date.today(),
            title='Weekly Report',
            content_md='# This week\n- Completed login\n- Started dashboard'
        )
        assert report.kind == 'weekly'
        assert report.title == 'Weekly Report'
        assert '# This week' in report.content_md
    
    def test_attachment(self, worklog, user):
        """Test attachment creation."""
        attachment = Attachment.objects.create(
            worklog=worklog,
            uploaded_by=user,
            kind='document',
            storage_provider='minio',
            object_key='uploads/doc.pdf',
            filename='requirements.pdf',
            mime_type='application/pdf',
            size_bytes=102400,
            description='Project requirements',
            checksum_sha256='abc123'
        )
        assert attachment.filename == 'requirements.pdf'
        assert attachment.size_bytes == 102400
    
    def test_external_link(self, worklog):
        """Test external link creation."""
        link = WorkLogExternalLink.objects.create(
            worklog=worklog,
            system='jira',
            key='PROJ-123',
            url='https://jira.example.com/PROJ-123',
            title='User authentication epic'
        )
        assert link.system == 'jira'
        assert link.key == 'PROJ-123'


@pytest.mark.django_db
class TestWorklogServices:
    """Test worklog service layer."""
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def client_obj(self, user):
        return services.create_client(
            user=user,
            name='Test Client',
            description='Test'
        )
    
    @pytest.fixture
    def project(self, client_obj, user):
        return services.create_project(
            client_id=client_obj.id,
            user=user,
            name='Test Project',
            description='Test'
        )
    
    def test_create_worklog_service(self, user, client_obj, project):
        """Test creating worklog via service."""
        worklog = services.create_worklog(
            user=user,
            occurred_on=date.today(),
            content='Test work',
            title='Test entry',
            client_id=client_obj.id,
            project_id=project.id,
            work_type='delivery',
            effort_minutes=120,
            tags=['test']
        )
        assert worklog.user == user
        assert worklog.client == client_obj
        assert worklog.project == project
        assert worklog.effort_minutes == 120
    
    def test_update_worklog_service(self, user, client_obj, project):
        """Test updating worklog via service."""
        worklog = services.create_worklog(
            user=user,
            occurred_on=date.today(),
            content='Original',
            client_id=client_obj.id
        )
        
        updated = services.update_worklog(
            worklog_id=worklog.id,
            user=user,
            content='Updated',
            status=WorkLogStatus.FINAL
        )
        assert updated.content == 'Updated'
        assert updated.status == WorkLogStatus.FINAL
    
    def test_create_client_service(self, user):
        """Test creating client via service."""
        client = services.create_client(
            user=user,
            name='New Client',
            description='Description',
            website='https://example.com'
        )
        assert client.name == 'New Client'
        assert client.website == 'https://example.com'
    
    def test_create_epic_service(self, user, client_obj, project):
        """Test creating epic via service."""
        epic = services.create_epic(
            project_id=project.id,
            user=user,
            name='Test Epic',
            description='Epic description'
        )
        assert epic.name == 'Test Epic'
        assert epic.project == project


@pytest.mark.django_db
class TestWorklogSelectors:
    """Test worklog selector/query layer."""
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def setup_data(self, user):
        """Create test data."""
        client = Client.objects.create(user=user, name='Client 1')
        project = Project.objects.create(client=client, name='Project 1')
        
        # Create worklogs
        for i in range(5):
            WorkLog.objects.create(
                user=user,
                occurred_on=date.today() - timedelta(days=i),
                content=f'Work {i}',
                client=client,
                project=project
            )
        return {'user': user, 'client': client, 'project': project}
    
    def test_list_worklogs(self, setup_data):
        """Test listing worklogs."""
        worklogs = selectors.list_worklogs(user=setup_data['user'])
        assert len(worklogs) >= 5
    
    def test_list_worklogs_with_filters(self, setup_data):
        """Test listing worklogs with filters."""
        worklogs = selectors.list_worklogs(
            user=setup_data['user'],
            client_id=setup_data['client'].id,
            start_date=date.today() - timedelta(days=2),
            end_date=date.today()
        )
        assert len(worklogs) == 3
    
    def test_get_worklog(self, setup_data):
        """Test getting single worklog."""
        worklog = WorkLog.objects.filter(user=setup_data['user']).first()
        result = selectors.get_worklog(worklog.id, user=setup_data['user'])
        assert result.id == worklog.id
    
    def test_list_clients(self, setup_data):
        """Test listing clients."""
        clients = selectors.list_clients(setup_data['user'])
        assert len(clients) >= 1
    
    def test_list_projects(self, setup_data):
        """Test listing projects."""
        projects = selectors.list_projects(
            user=setup_data['user'],
            client_id=setup_data['client'].id
        )
        assert len(projects) >= 1


@pytest.mark.django_db
class TestWorklogAPI:
    """Test worklog API endpoints."""
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def api_client(self, user):
        """Authenticated API client."""
        client = APIClient()
        client.force_authenticate(user=user)
        return client
    
    @pytest.fixture
    def client_obj(self, user):
        return Client.objects.create(user=user, name='Test Client')
    
    @pytest.fixture
    def project(self, client_obj):
        return Project.objects.create(client=client_obj, name='Test Project')
    
    def test_list_worklogs_api(self, api_client, user, client_obj, project):
        """Test GET /api/worklogs/"""
        # Create test data
        WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            content='Test work',
            client=client_obj,
            project=project
        )
        
        response = api_client.get('/api/worklogs/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) >= 1
    
    def test_create_worklog_api(self, api_client, client_obj, project):
        """Test POST /api/worklogs/"""
        data = {
            'occurred_on': date.today().isoformat(),
            'content': 'New worklog entry',
            'title': 'Test Entry',
            'client': client_obj.id,
            'project': project.id,
            'work_type': 'delivery',
            'status': 'draft',
            'effort_minutes': 120,
            'tags': ['test', 'api']
        }
        
        response = api_client.post('/api/worklogs/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        
        # Verify created
        worklog = WorkLog.objects.get(id=response.data['id'])
        assert worklog.content == 'New worklog entry'
        assert worklog.effort_minutes == 120
    
    def test_update_worklog_api(self, api_client, user, client_obj):
        """Test PATCH /api/worklogs/{id}/"""
        worklog = WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            content='Original content',
            client=client_obj
        )
        
        data = {
            'content': 'Updated content',
            'status': 'ready'
        }
        
        response = api_client.patch(f'/api/worklogs/{worklog.id}/', data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        worklog.refresh_from_db()
        assert worklog.content == 'Updated content'
        assert worklog.status == 'ready'
    
    def test_delete_worklog_api(self, api_client, user, client_obj):
        """Test DELETE /api/worklogs/{id}/"""
        worklog = WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            content='To be deleted',
            client=client_obj
        )
        
        response = api_client.delete(f'/api/worklogs/{worklog.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deleted
        assert not WorkLog.objects.filter(id=worklog.id).exists()
    
    def test_list_clients_api(self, api_client, client_obj):
        """Test GET /api/clients/"""
        response = api_client.get('/api/clients/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
    
    def test_create_client_api(self, api_client):
        """Test POST /api/clients/"""
        data = {
            'name': 'New Client',
            'description': 'Client description',
            'website': 'https://example.com'
        }
        
        response = api_client.post('/api/clients/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Client'
    
    def test_list_projects_api(self, api_client, project):
        """Test GET /api/projects/"""
        response = api_client.get('/api/projects/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
    
    def test_create_project_api(self, api_client, client_obj):
        """Test POST /api/projects/"""
        data = {
            'client': client_obj.id,
            'name': 'New Project',
            'description': 'Project description',
            'role': 'Developer'
        }
        
        response = api_client.post('/api/projects/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Project'
    
    def test_worklog_filtering(self, api_client, user, client_obj, project):
        """Test worklog filtering."""
        # Create worklogs
        WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            content='Today',
            client=client_obj,
            work_type='delivery'
        )
        WorkLog.objects.create(
            user=user,
            occurred_on=date.today() - timedelta(days=5),
            content='Last week',
            client=client_obj,
            work_type='planning'
        )
        
        # Filter by date
        response = api_client.get(f'/api/worklogs/?start_date={date.today().isoformat()}')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        
        # Filter by work type
        response = api_client.get('/api/worklogs/?work_type=delivery')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_worklog_search(self, api_client, user, client_obj):
        """Test worklog search."""
        WorkLog.objects.create(
            user=user,
            occurred_on=date.today(),
            content='Implemented authentication with Django',
            client=client_obj
        )
        
        response = api_client.get('/api/worklogs/?search=Django')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_unauthorized_access(self):
        """Test that unauthenticated requests are rejected."""
        client = APIClient()
        response = client.get('/api/worklogs/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestWorklogHierarchyValidation:
    """Test hierarchy validation and backfilling."""
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(username='testuser', password='pass')
    
    @pytest.fixture
    def setup_hierarchy(self, user):
        """Create full hierarchy."""
        client = Client.objects.create(user=user, name='Client')
        project = Project.objects.create(client=client, name='Project')
        epic = Epic.objects.create(project=project, name='Epic')
        feature = Feature.objects.create(epic=epic, name='Feature')
        story = Story.objects.create(feature=feature, name='Story')
        task = Task.objects.create(story=story, name='Task')
        return {
            'user': user,
            'client': client,
            'project': project,
            'epic': epic,
            'feature': feature,
            'story': story,
            'task': task
        }
    
    def test_task_backfills_entire_hierarchy(self, setup_hierarchy):
        """Test that providing only task backfills the entire hierarchy."""
        task = setup_hierarchy['task']
        
        worklog = WorkLog(
            user=setup_hierarchy['user'],
            occurred_on=date.today(),
            content='Test',
            task=task
        )
        worklog.full_clean()
        worklog.save()
        
        # Should backfill all parents
        assert worklog.story == setup_hierarchy['story']
        assert worklog.feature == setup_hierarchy['feature']
        assert worklog.epic == setup_hierarchy['epic']
        assert worklog.project == setup_hierarchy['project']
        assert worklog.client == setup_hierarchy['client']
    
    def test_project_backfills_client(self, setup_hierarchy):
        """Test that providing project backfills client."""
        worklog = WorkLog(
            user=setup_hierarchy['user'],
            occurred_on=date.today(),
            content='Test',
            project=setup_hierarchy['project']
        )
        worklog.full_clean()
        worklog.save()
        
        assert worklog.client == setup_hierarchy['client']
    
    def test_mismatched_hierarchy_fails(self, user):
        """Test that mismatched hierarchy fails validation."""
        client1 = Client.objects.create(user=user, name='Client 1')
        client2 = Client.objects.create(user=user, name='Client 2')
        project1 = Project.objects.create(client=client1, name='Project 1')
        project2 = Project.objects.create(client=client2, name='Project 2')
        
        worklog = WorkLog(
            user=user,
            occurred_on=date.today(),
            content='Test',
            client=client1,
            project=project2  # Belongs to client2!
        )
        
        with pytest.raises(ValidationError):
            worklog.full_clean()
