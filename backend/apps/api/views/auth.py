"""
API views for authentication endpoints.
Thin controllers - delegate to services.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout, authenticate
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.contrib.auth.models import User
from django_ratelimit.decorators import ratelimit

from apps.accounts import services as account_services
from apps.accounts.serializers import UserSerializer
from apps.invitations import services as invite_services
from apps.invitations.serializers import InvitePasskeySerializer, PasskeyCreateSerializer
from apps.auditing.serializers import AuthEventSerializer
from apps.auditing.models import AuthEvent


def get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Extract user agent from request."""
    return request.META.get('HTTP_USER_AGENT', '')


@ratelimit(key='ip', rate='5/m', method='POST')
@api_view(['POST'])
@parser_classes([JSONParser, FormParser])
@permission_classes([AllowAny])
def signup(request):
    """
    Create a new user account with invite passkey.
    Rate limited to 5 requests per minute per IP.
    
    POST /api/auth/signup/
    Body: {username, email, password, passkey}
    """
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Signup request.data: {request.data}")
    logger.info(f"Signup request.POST: {request.POST}")
    
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    passkey = request.data.get('passkey')
    
    if not all([username, email, password, passkey]):
        return Response({
            'error': 'Missing required fields: username, email, password, passkey'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    success, result = account_services.signup_with_passkey(
        username=username,
        email=email,
        password=password,
        passkey_raw=passkey,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if success:
        user = result
        # Auto-login after signup
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        serializer = UserSerializer(user)
        return Response({
            'message': 'Signup successful',
            'user': serializer.data
        }, status=status.HTTP_201_CREATED)
    else:
        error_message = result
        return Response({
            'error': error_message
        }, status=status.HTTP_400_BAD_REQUEST)


@ratelimit(key='ip', rate='10/m', method='POST')
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Authenticate user and create session.
    Rate limited to 10 requests per minute per IP.
    
    POST /api/auth/login/
    Body: {username, password, remember_me}
    """
    username = request.data.get('username')
    password = request.data.get('password')
    remember_me = request.data.get('remember_me', False)
    
    if not username or not password:
        return Response({
            'error': 'Username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    success, result = account_services.authenticate_user(
        username=username,
        password=password,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if success:
        user = result
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        # Handle remember me
        if not remember_me:
            request.session.set_expiry(0)  # Session expires on browser close
        
        serializer = UserSerializer(user)
        return Response({
            'message': 'Login successful',
            'user': serializer.data
        })
    else:
        error_message = result
        return Response({
            'error': error_message
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout user and destroy session.
    
    POST /api/auth/logout/
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    account_services.log_logout(request.user, ip_address, user_agent)
    logout(request)
    
    return Response({'message': 'Logout successful'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Get current user information including profile and tenant.
    
    GET /api/me/
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@ratelimit(key='ip', rate='10/m', method='POST')
@api_view(['POST'])
@permission_classes([AllowAny])
def get_token(request):
    """
    Get or create auth token for username/password.
    Used by frontend to obtain token for API calls.
    Rate limited to 10 requests per minute per IP.
    
    POST /api/auth/token/
    Body: {username, password}
    
    Returns: {token, user}
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({
            'error': 'Username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(username=username, password=password)
    if not user:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Get or create token
    token, created = Token.objects.get_or_create(user=user)
    serializer = UserSerializer(user)
    
    return Response({
        'token': token.key,
        'user': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def password_change(request):
    """
    Change user password.
    
    POST /api/auth/password/change/
    Body: {old_password, new_password}
    """
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not old_password or not new_password:
        return Response({
            'error': 'Both old_password and new_password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not request.user.check_password(old_password):
        return Response({
            'error': 'Current password is incorrect'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    request.user.set_password(new_password)
    request.user.save()
    
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    account_services.log_password_change(request.user, ip_address, user_agent)
    
    return Response({'message': 'Password changed successfully'})


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    """
    Request password reset (sends email if configured).
    
    POST /api/auth/password/reset/
    Body: {email}
    """
    email = request.data.get('email')
    if not email:
        return Response({
            'error': 'Email is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    account_services.log_password_reset_request(email, ip_address, user_agent)
    
    # Always return success to prevent email enumeration
    return Response({
        'message': 'If an account exists with this email, a password reset link will be sent'
    })
