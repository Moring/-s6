"""
Tests for worklog API endpoints with client/project hierarchy.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.worklog.models import Client, Project, WorkLog
from datetime import date

User = get_user_model()


@pytest.mark.django_db
class TestWorklogAPIHierarchy:
    """Test worklog API endpoints with organizational hierarchy."""
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def api_client(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client
    
    @pytest.fixture
    def client_obj(self, user):
        return Client.objects.create(
            user=user,
            name='Test Client Inc'
        )
    
    @pytest.fixture
    def project(self, client_obj):
        return Project.objects.create(
            client=client_obj,
            name='Test Project'
        )
    
    def test_create_client_api(self, api_client):
        """Test creating a client via API."""
        response = api_client.post('/api/clients/', {
            'name': 'Acme Corp',
            'description': 'Test client',
            'is_active': True
        })
        assert response.status_code == 201
        assert response.data['name'] == 'Acme Corp'
    
    def test_list_clients_api(self, api_client, client_obj):
        """Test listing clients via API."""
        response = api_client.get('/api/clients/')
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == 'Test Client Inc'
    
    def test_create_project_api(self, api_client, client_obj):
        """Test creating a project via API."""
        response = api_client.post('/api/projects/', {
            'client': client_obj.id,
            'name': 'New Project',
            'description': 'Project description',
            'is_active': True
        })
        assert response.status_code == 201
        assert response.data['name'] == 'New Project'
        assert response.data['client'] == client_obj.id
    
    def test_list_projects_api(self, api_client, project):
        """Test listing projects via API."""
        response = api_client.get('/api/projects/')
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == 'Test Project'
    
    def test_filter_projects_by_client(self, api_client, client_obj):
        """Test filtering projects by client."""
        # Create two clients with projects
        Project.objects.create(client=client_obj, name='Project 1')
        
        client2 = Client.objects.create(
            user=api_client.handler._force_user,
            name='Client 2'
        )
        Project.objects.create(client=client2, name='Project 2')
        
        response = api_client.get(f'/api/projects/?client={client_obj.id}')
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == 'Project 1'
    
    def test_create_worklog_with_hierarchy(self, api_client, client_obj, project):
        """Test creating a worklog entry with client and project."""
        response = api_client.post('/api/worklogs/', {
            'date': str(date.today()),
            'client': client_obj.id,
            'project': project.id,
            'content': 'Implemented feature X',
            'outcome': 'Feature X is complete',
            'work_type': 'delivery',
            'hours': 3.5,
            'tags': ['python', 'django']
        }, format='json')
        if response.status_code != 201:
            print(f"Response data: {response.data}")
        assert response.status_code == 201
        assert response.data['client'] == client_obj.id
        assert response.data['project'] == project.id
        assert response.data['work_type'] == 'delivery'
        # hours might be string or decimal
        assert float(response.data['hours']) == 3.5
    
    def test_create_minimal_worklog(self, api_client):
        """Test creating a minimal worklog without hierarchy."""
        response = api_client.post('/api/worklogs/', {
            'date': str(date.today()),
            'content': 'Fixed a bug'
        })
        assert response.status_code == 201
        assert response.data['client'] is None
        assert response.data['project'] is None
        assert response.data['content'] == 'Fixed a bug'
    
    def test_filter_worklogs_by_client(self, api_client, user, client_obj, project):
        """Test filtering worklogs by client."""
        # Create worklogs for different clients
        WorkLog.objects.create(
            user=user,
            date=date.today(),
            client=client_obj,
            project=project,
            content='Work for client 1'
        )
        WorkLog.objects.create(
            user=user,
            date=date.today(),
            content='Personal work'
        )
        
        response = api_client.get(f'/api/worklogs/?client={client_obj.id}')
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['content'] == 'Work for client 1'
    
    def test_filter_worklogs_by_project(self, api_client, user, client_obj, project):
        """Test filtering worklogs by project."""
        WorkLog.objects.create(
            user=user,
            date=date.today(),
            client=client_obj,
            project=project,
            content='Work on project 1'
        )
        
        project2 = Project.objects.create(client=client_obj, name='Project 2')
        WorkLog.objects.create(
            user=user,
            date=date.today(),
            client=client_obj,
            project=project2,
            content='Work on project 2'
        )
        
        response = api_client.get(f'/api/worklogs/?project={project.id}')
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['content'] == 'Work on project 1'
    
    def test_filter_worklogs_by_work_type(self, api_client, user):
        """Test filtering worklogs by work type."""
        WorkLog.objects.create(
            user=user,
            date=date.today(),
            content='Implemented feature',
            work_type='delivery'
        )
        WorkLog.objects.create(
            user=user,
            date=date.today(),
            content='Fixed production issue',
            work_type='incident'
        )
        
        response = api_client.get('/api/worklogs/?work_type=delivery')
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['work_type'] == 'delivery'
    
    def test_filter_worklogs_by_date_range(self, api_client, user):
        """Test filtering worklogs by date range."""
        from datetime import timedelta
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        WorkLog.objects.create(user=user, date=yesterday, content='Yesterday work')
        WorkLog.objects.create(user=user, date=today, content='Today work')
        
        response = api_client.get(f'/api/worklogs/?start_date={today}')
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['content'] == 'Today work'
    
    def test_search_worklogs(self, api_client, user):
        """Test searching worklogs by content."""
        WorkLog.objects.create(
            user=user,
            date=date.today(),
            content='Implemented authentication feature'
        )
        WorkLog.objects.create(
            user=user,
            date=date.today(),
            content='Fixed database bug'
        )
        
        response = api_client.get('/api/worklogs/?search=authentication')
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert 'authentication' in response.data['results'][0]['content']
    
    def test_create_draft_worklog(self, api_client):
        """Test creating a draft worklog."""
        response = api_client.post('/api/worklogs/', {
            'date': str(date.today()),
            'content': 'Work in progress',
            'is_draft': True
        })
        assert response.status_code == 201
        assert response.data['is_draft'] is True
    
    def test_filter_draft_worklogs(self, api_client, user):
        """Test filtering draft worklogs."""
        WorkLog.objects.create(
            user=user,
            date=date.today(),
            content='Published work',
            is_draft=False
        )
        WorkLog.objects.create(
            user=user,
            date=date.today(),
            content='Draft work',
            is_draft=True
        )
        
        response = api_client.get('/api/worklogs/?is_draft=true')
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['content'] == 'Draft work'
