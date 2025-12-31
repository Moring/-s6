"""
Middleware for handling backend API token management.
"""
from apps.api_proxy.client import get_backend_client
import logging

logger = logging.getLogger(__name__)


class BackendTokenMiddleware:
    """
    Middleware to manage backend API tokens for authenticated users.
    
    For authenticated users without a backend_token in session,
    attempts to generate one from stored credentials or prompts re-auth.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if user is authenticated and doesn't have a backend token
        if request.user.is_authenticated and not request.session.get('backend_token'):
            # Try to get token if we have credentials in the request (login form)
            if request.method == 'POST' and 'login' in request.path:
                username = request.POST.get('login')  # allauth uses 'login' field
                password = request.POST.get('password')
                
                if username and password:
                    try:
                        client = get_backend_client()
                        token_data = client.get_token(username, password)
                        
                        if token_data and 'token' in token_data:
                            # Store token for subsequent request
                            # (it will be available after this request completes)
                            request._backend_token = token_data['token']
                            logger.info(f"Backend token will be set for user {username}")
                    except Exception as e:
                        logger.error(f"Error getting backend token: {e}")
        
        response = self.response
        
        # If we got a token during this request, save it to session
        if hasattr(request, '_backend_token'):
            request.session['backend_token'] = request._backend_token
            logger.info("Backend token saved to session")
        
        return response
    
    def process_request(self, request):
        """Process the request."""
        pass
    
    def process_response(self, request, response):
        """Process the response."""
        self.response = response
        return self.__call__(request)
