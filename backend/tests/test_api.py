"""
Test API endpoints.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from datetime import date
from apps.worklog.services import create_worklog

User = get_user_model()


@pytest.fixture
def api_client():
    """Create API client."""
    return APIClient()


@pytest.fixture
def test_user():
    """Create test user."""
    return User.objects.create_user(username='testuser', password='test123')


@pytest.mark.django_db
class TestWorklogAPI:
    """Test worklog API endpoints."""
    
    def test_create_worklog(self, api_client, test_user):
        """Test creating a worklog via API."""
        api_client.force_authenticate(user=test_user)
        
        response = api_client.post('/api/worklogs/', {
            'date': date.today().isoformat(),
            'content': 'Test worklog from API',
            'source': 'api'
        })
        
        assert response.status_code == 201
        assert 'id' in response.data
        assert response.data['content'] == 'Test worklog from API'
    
    def test_list_worklogs(self, api_client, test_user):
        """Test listing worklogs."""
        api_client.force_authenticate(user=test_user)
        
        # Create test worklog
        create_worklog(
            date=date.today(),
            content='Test worklog',
            user=test_user
        )
        
        response = api_client.get('/api/worklogs/')
        
        assert response.status_code == 200
        assert len(response.data['results']) > 0
    
    def test_analyze_worklog_endpoint(self, api_client, test_user, fake_llm):
        """Test worklog analysis endpoint."""
        api_client.force_authenticate(user=test_user)
        
        # Create worklog
        worklog = create_worklog(
            date=date.today(),
            content='Test content for analysis',
            user=test_user
        )
        
        response = api_client.post(f'/api/worklogs/{worklog.id}/analyze/')
        
        assert response.status_code == 202
        assert 'job_id' in response.data
        assert response.data['status'] == 'queued'


@pytest.mark.django_db
class TestSkillsAPI:
    """Test skills API endpoints."""
    
    def test_recompute_skills(self, api_client, test_user, fake_llm):
        """Test skills recompute endpoint."""
        api_client.force_authenticate(user=test_user)
        
        response = api_client.post('/api/skills/recompute/', {
            'window_days': 30
        })
        
        assert response.status_code == 202
        assert 'job_id' in response.data


@pytest.mark.django_db
class TestSystemDashboard:
    """Test system dashboard endpoints."""
    
    def test_system_overview(self, api_client, test_user):
        """Test system overview endpoint."""
        # Make user staff
        test_user.is_staff = True
        test_user.save()
        
        api_client.force_authenticate(user=test_user)
        
        response = api_client.get('/system/overview/')
        
        assert response.status_code == 200
        assert 'jobs' in response.data
        assert 'schedules' in response.data
    
    def test_system_health(self, api_client, test_user):
        """Test system health endpoint."""
        test_user.is_staff = True
        test_user.save()
        
        api_client.force_authenticate(user=test_user)
        
        response = api_client.get('/system/health/')
        
        assert response.status_code == 200
        assert 'status' in response.data
        assert 'checks' in response.data


@pytest.mark.django_db
class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_healthz(self, api_client):
        """Test basic health endpoint."""
        response = api_client.get('/api/healthz/')
        
        assert response.status_code == 200
        assert response.data['status'] == 'ok'
    
    def test_readyz(self, api_client):
        """Test readiness endpoint."""
        response = api_client.get('/api/readyz/')
        
        assert response.status_code == 200
        assert 'status' in response.data
        assert 'checks' in response.data
