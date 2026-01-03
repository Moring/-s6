"""
API views for authentication endpoints.
Thin controllers - delegate to services.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import TokenError

from apps.accounts import services as account_services
from apps.accounts.serializers import UserSerializer
from apps.invitations import services as invite_services
from apps.invitations.serializers import InvitePasskeySerializer, PasskeyCreateSerializer
from apps.auditing.serializers import AuthEventSerializer
from apps.auditing.models import AuthEvent
from apps.api.rate_limiting import rate_limit, AUTH_RATE_LIMITER, SIGNUP_RATE_LIMITER, PASSKEY_RATE_LIMITER


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


def issue_tokens_for_user(user):
    """Create access/refresh tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return refresh, refresh.access_token


def set_refresh_cookie(response, refresh_token):
    """Store refresh token in an HttpOnly cookie for SPA refresh."""
    max_age = int(refresh_token.lifetime.total_seconds())
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        str(refresh_token),
        max_age=max_age,
        httponly=True,
        secure=getattr(settings, 'SESSION_COOKIE_SECURE', False),
        samesite='Lax',
        path=settings.JWT_REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response):
    """Clear refresh token cookie."""
    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        path=settings.JWT_REFRESH_COOKIE_PATH,
    )


def get_refresh_from_request(request):
    """Read refresh token from request body or cookie."""
    return request.data.get('refresh') or request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)


@rate_limit(SIGNUP_RATE_LIMITER)
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
        refresh, access = issue_tokens_for_user(user)
        serializer = UserSerializer(user)
        response = Response({
            'message': 'Signup successful',
            'user': serializer.data,
            'access': str(access),
        }, status=status.HTTP_201_CREATED)
        set_refresh_cookie(response, refresh)
        return response
    else:
        error_message = result
        return Response({
            'error': error_message
        }, status=status.HTTP_400_BAD_REQUEST)


@rate_limit(AUTH_RATE_LIMITER)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Authenticate user and issue JWT access token + refresh cookie.
    Rate limited to 10 requests per minute per IP.
    
    POST /api/auth/login/
    Body: {username, password}
    """
    username = request.data.get('username')
    password = request.data.get('password')
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
        refresh, access = issue_tokens_for_user(user)
        serializer = UserSerializer(user)
        response = Response({
            'message': 'Login successful',
            'user': serializer.data,
            'access': str(access),
        })
        set_refresh_cookie(response, refresh)
        return response
    else:
        error_message = result
        return Response({
            'error': error_message
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    """
    Logout user by blacklisting refresh token and clearing cookie.
    
    POST /api/auth/logout/
    Body: {refresh} (optional)
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    refresh_token = get_refresh_from_request(request)
    user = None

    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            user_id = token.get('user_id')
            user = User.objects.filter(id=user_id).first()
            try:
                token.blacklist()
            except AttributeError:
                pass
        except TokenError:
            pass

    if user:
        account_services.log_logout(user, ip_address, user_agent)

    response = Response({'message': 'Logout successful'})
    clear_refresh_cookie(response)
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Get current user information including profile and tenant.
    
    GET /api/me/
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@rate_limit(AUTH_RATE_LIMITER)
@api_view(['POST'])
@permission_classes([AllowAny])
def get_token(request):
    """
    Get JWT tokens for username/password.
    Used by scripts or non-SPA clients.
    Rate limited to 10 requests per minute per IP.
    
    POST /api/auth/token/
    Body: {username, password}
    
    Returns: {access, refresh, user}
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
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
    if not success:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)

    user = result
    refresh, access = issue_tokens_for_user(user)
    serializer = UserSerializer(user)
    response = Response({
        'access': str(access),
        'refresh': str(refresh),
        'user': serializer.data,
    })
    set_refresh_cookie(response, refresh)
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Refresh access token using refresh token from body or cookie.
    
    POST /api/auth/token/refresh/
    Body: {refresh} (optional)
    Returns: {access}
    """
    refresh_token = get_refresh_from_request(request)
    if not refresh_token:
        return Response({
            'error': 'Refresh token is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
    try:
        serializer.is_valid(raise_exception=True)
    except TokenError:
        response = Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)
        clear_refresh_cookie(response)
        return response

    data = serializer.validated_data
    response = Response({'access': data['access']})
    if 'refresh' in data:
        set_refresh_cookie(response, RefreshToken(data['refresh']))
    return response


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
