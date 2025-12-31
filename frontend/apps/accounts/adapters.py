"""
Custom allauth adapters for AfterResume.
"""
from allauth.account.adapter import DefaultAccountAdapter
from apps.api_proxy.client import get_backend_client
import logging

logger = logging.getLogger(__name__)


class AfterResumeAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter to handle backend token retrieval on login.
    """
    
    def login(self, request, user):
        """
        Override login to fetch backend API token.
        """
        # Call parent login
        ret = super().login(request, user)
        
        # Try to get backend token
        # Note: At this point, we don't have the plaintext password
        # So we'll need to handle this differently
        # For now, just log that login happened
        logger.info(f"User {user.username} logged in to frontend")
        
        return ret
