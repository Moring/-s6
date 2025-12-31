"""
Views for user accounts and profile management.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from apps.api_proxy.client import get_backend_client


@login_required
@require_http_methods(["GET"])
def profile(request):
    """
    Display user profile page with information from backend.
    """
    client = get_backend_client()
    
    # Fetch user profile from backend
    profile_data = {}
    try:
        # Assuming backend has an endpoint to get current user's profile
        response = client.get(f'/api/users/{request.user.id}/')
        if response:
            profile_data = response
    except Exception as e:
        # If backend unavailable, show basic info from session
        profile_data = {
            'username': request.user.username,
            'email': request.user.email,
            'error': str(e)
        }
    
    return render(request, 'auth/profile.html', {
        'profile': profile_data
    })
