"""
Views for user accounts and profile management.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.conf import settings
from apps.api_proxy.client import get_backend_client
import requests


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


@require_http_methods(["GET", "POST"])
def signup_with_passkey(request):
    """
    Custom signup view that requires an invite passkey.
    Calls backend API to validate passkey and create account.
    """
    if request.user.is_authenticated:
        return redirect('ui:dashboard')
    
    if request.method == 'GET':
        return render(request, 'account/signup_passkey.html')
    
    # POST: process signup
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password1 = request.POST.get('password1', '')
    password2 = request.POST.get('password2', '')
    passkey = request.POST.get('passkey', '').strip()
    
    # Client-side validation
    errors = []
    
    if not username:
        errors.append("Username is required")
    if not email:
        errors.append("Email is required")
    if not password1:
        errors.append("Password is required")
    if not password2:
        errors.append("Password confirmation is required")
    if password1 and password2 and password1 != password2:
        errors.append("Passwords do not match")
    if not passkey:
        errors.append("Invite passkey is required")
    
    if errors:
        for error in errors:
            messages.error(request, error)
        return render(request, 'account/signup_passkey.html', {
            'username': username,
            'email': email,
        })
    
    # Call backend signup API
    try:
        backend_url = settings.BACKEND_BASE_URL
        response = requests.post(
            f"{backend_url}/api/auth/signup/",
            json={
                'username': username,
                'email': email,
                'password': password1,
                'passkey': passkey,
            },
            timeout=10
        )
        
        if response.status_code == 201:
            # Signup successful
            data = response.json()
            messages.success(request, "Account created successfully! Please log in.")
            return redirect('account_login')
        else:
            # Signup failed
            error_data = response.json()
            error_message = error_data.get('error', 'Signup failed. Please try again.')
            messages.error(request, error_message)
            return render(request, 'account/signup_passkey.html', {
                'username': username,
                'email': email,
            })
    
    except requests.exceptions.Timeout:
        messages.error(request, 'Request timed out. Please try again.')
        return render(request, 'account/signup_passkey.html', {
            'username': username,
            'email': email,
        })
    except requests.exceptions.RequestException as e:
        messages.error(request, f'Could not connect to backend service.')
        return render(request, 'account/signup_passkey.html', {
            'username': username,
            'email': email,
        })
