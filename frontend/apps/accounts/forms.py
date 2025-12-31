"""
Custom authentication forms for AfterResume.
"""
from allauth.account.forms import LoginForm as AllauthLoginForm
from apps.api_proxy.client import get_backend_client
import logging

logger = logging.getLogger(__name__)


class LoginForm(AllauthLoginForm):
    """
    Custom login form that fetches backend API token on successful authentication.
    """
    
    def login(self, request, redirect_url=None):
        """
        Override login to fetch and store backend API token.
        """
        # Get credentials before parent processes them
        username = self.cleaned_data.get('login')
        password = self.cleaned_data.get('password')
        
        # Call parent login (performs authentication)
        ret = super().login(request, redirect_url)
        
        # After successful login, get backend token
        if username and password:
            try:
                client = get_backend_client()
                token_data = client.get_token(username, password)
                
                if token_data and 'token' in token_data:
                    request.session['backend_token'] = token_data['token']
                    logger.info(f"Backend token obtained and stored for user {username}")
                else:
                    logger.warning(f"Failed to get backend token for user {username}")
            except Exception as e:
                logger.error(f"Error getting backend token: {e}")
        
        return ret
