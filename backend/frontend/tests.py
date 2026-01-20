"""
Tests for frontend views.
"""
import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.tenants.models import Tenant
from apps.accounts.models import UserProfile
from apps.invitations.models import InvitePasskey


@pytest.mark.django_db
class TestIndexView:
    """Test main index view."""
    
    def test_index_renders(self, client):
        """Test that index page renders successfully."""
        response = client.get(reverse('frontend:index'))
        assert response.status_code == 200
        assert 'AfterResume' in str(response.content)
    
    def test_index_shows_login_prompt_when_logged_out(self, client):
        """Test that logged out users see login prompt."""
        response = client.get(reverse('frontend:index'))
        assert 'login' in str(response.content).lower()
        assert 'signup' in str(response.content).lower()
    
    def test_index_shows_welcome_when_logged_in(self, client, user_with_profile):
        """Test that logged in users see welcome message."""
        client.force_login(user_with_profile)
        response = client.get(reverse('frontend:index'))
        assert user_with_profile.username in str(response.content)


@pytest.mark.django_db
class TestChatSendView:
    """Test chat send view."""
    
    def test_chat_login_command(self, client):
        """Test that 'login' command initiates login flow."""
        response = client.post(
            reverse('frontend:chat_send'),
            {'message': 'login'}
        )
        assert response.status_code == 200
        assert 'username' in str(response.content).lower()
    
    def test_chat_signup_command(self, client):
        """Test that 'signup' command initiates signup flow."""
        response = client.post(
            reverse('frontend:chat_send'),
            {'message': 'signup'}
        )
        assert response.status_code == 200
        assert 'username' in str(response.content).lower()
    
    def test_chat_help_command_logged_out(self, client):
        """Test help command when logged out."""
        response = client.post(
            reverse('frontend:chat_send'),
            {'message': 'help'}
        )
        assert response.status_code == 200
        assert 'login' in str(response.content).lower()
        assert 'signup' in str(response.content).lower()
    
    def test_chat_help_command_logged_in(self, client, user_with_profile):
        """Test help command when logged in."""
        client.force_login(user_with_profile)
        response = client.post(
            reverse('frontend:chat_send'),
            {'message': 'help'}
        )
        assert response.status_code == 200
        assert 'dashboard' in str(response.content).lower()
        assert 'logout' in str(response.content).lower()
    
    def test_chat_private_feature_requires_auth(self, client):
        """Test that private features require authentication."""
        response = client.post(
            reverse('frontend:chat_send'),
            {'message': 'dashboard'}
        )
        assert response.status_code == 200
        assert 'login' in str(response.content).lower() or 'signup' in str(response.content).lower()


@pytest.mark.django_db
class TestDashboardCardView:
    """Test dashboard card view."""
    
    def test_dashboard_requires_auth(self, client):
        """Test that dashboard requires authentication."""
        response = client.get(reverse('frontend:dashboard_card'))
        assert response.status_code == 302  # Redirect to login
    
    def test_dashboard_renders_for_logged_in_user(self, client, user_with_profile):
        """Test that dashboard renders for logged in users."""
        client.force_login(user_with_profile)
        response = client.get(reverse('frontend:dashboard_card'))
        assert response.status_code == 200
        assert user_with_profile.username in str(response.content)


@pytest.mark.django_db
class TestStatusBarView:
    """Test status bar view."""
    
    def test_status_bar_renders_logged_out(self, client):
        """Test that status bar renders when logged out."""
        response = client.get(reverse('frontend:status_bar'))
        assert response.status_code == 200
        assert 'Token' in str(response.content) or 'token' in str(response.content)
    
    def test_status_bar_renders_logged_in(self, client, user_with_profile):
        """Test that status bar renders when logged in."""
        client.force_login(user_with_profile)
        response = client.get(reverse('frontend:status_bar'))
        assert response.status_code == 200
        assert 'Reserve Balance' in str(response.content) or 'reserve' in str(response.content).lower()


# Fixtures
@pytest.fixture
def user_with_profile(db):
    """Create a user with tenant and profile."""
    import uuid
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    
    # Create user - signals will auto-create tenant AND user profile
    user = User.objects.create_user(
        username=username,
        password="testpass123"
    )
    
    # Everything is auto-created via signals
    return user


@pytest.fixture
def invite_passkey(db):
    """Create an active invite passkey."""
    import uuid
    return InvitePasskey.objects.create(
        key=f"TEST-PASSKEY-{uuid.uuid4().hex[:8]}",
        is_active=True,
        max_uses=1
    )
