"""
Frontend views for AfterResume chat interface with HTMX support.
"""
import json
import logging
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.generic import TemplateView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserProfile
from apps.invitations.models import InvitePasskey

logger = logging.getLogger(__name__)


class IndexView(TemplateView):
    """Main application view with chat and canvas."""
    template_name = 'frontend/index.html'
    
    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_authenticated'] = self.request.user.is_authenticated
        context['username'] = self.request.user.username if self.request.user.is_authenticated else None
        return context


class ChatSendView(View):
    """Handle chat message submissions via HTMX."""
    
    def post(self, request):
        message = request.POST.get('message', '').strip()
        
        if not message:
            return render(request, 'frontend/partials/chat_message.html', {
                'error': True,
                'message': 'Please enter a message.',
                'is_bot': True
            })
        
        # Check for auth flow continuation
        auth_flow = request.session.get('auth_flow')
        if auth_flow == 'login':
            return self._handle_login_flow(request, message)
        elif auth_flow == 'signup':
            return self._handle_signup_flow(request, message)
        
        # Check for special commands
        message_lower = message.lower()
        
        # Not authenticated - handle login/signup/public commands
        if not request.user.is_authenticated:
            if message_lower == 'login':
                return self._start_login(request)
            elif message_lower == 'signup':
                return self._start_signup(request)
            elif message_lower in ['help', 'commands']:
                return self._show_help(request, authenticated=False)
            else:
                # Check if user is trying to access private features
                private_keywords = ['worklog', 'skills', 'report', 'dashboard', 'profile', 'settings']
                if any(keyword in message_lower for keyword in private_keywords):
                    return render(request, 'frontend/partials/chat_message.html', {
                        'is_bot': True,
                        'message': 'Please login or signup to continue.',
                        'show_login_prompt': True
                    })
                else:
                    return render(request, 'frontend/partials/chat_message.html', {
                        'is_bot': True,
                        'message': 'Ask a question, or type "login" or "signup".',
                        'show_help': True
                    })
        
        # Authenticated - handle commands and chat
        if message_lower in ['help', 'commands']:
            return self._show_help(request, authenticated=True)
        elif message_lower == 'logout':
            return self._handle_logout(request)
        elif message_lower == 'dashboard':
            return self._show_dashboard(request)
        elif message_lower.startswith('reset password'):
            return self._handle_password_reset(request, message)
        elif request.user.is_staff and message_lower.startswith('admin '):
            return self._handle_admin_command(request, message)
        else:
            # Regular chat message - echo for now
            return render(request, 'frontend/partials/chat_response.html', {
                'user_message': message,
                'bot_message': f'You said: {message}. (AI integration coming soon)',
                'is_bot': True
            })
    
    def _start_login(self, request):
        """Initiate login flow."""
        # Store state in session
        request.session['auth_flow'] = 'login'
        request.session['auth_step'] = 'username'
        
        return render(request, 'frontend/partials/chat_message.html', {
            'is_bot': True,
            'message': 'Enter username:',
            'show_input': True,
            'input_type': 'text',
            'input_placeholder': 'Username'
        })
    
    def _start_signup(self, request):
        """Initiate signup flow."""
        request.session['auth_flow'] = 'signup'
        request.session['auth_step'] = 'username'
        request.session['signup_data'] = {}
        
        return render(request, 'frontend/partials/chat_message.html', {
            'is_bot': True,
            'message': 'Enter username:',
            'show_input': True,
            'input_type': 'text',
            'input_placeholder': 'Username'
        })
    
    def _handle_login_flow(self, request, value):
        """Handle multi-step login flow."""
        step = request.session.get('auth_step')
        
        if step == 'username':
            request.session['login_username'] = value
            request.session['auth_step'] = 'password'
            return render(request, 'frontend/partials/chat_message.html', {
                'is_bot': True,
                'message': 'Enter password:',
                'show_input': True,
                'input_type': 'password',
                'input_placeholder': 'Password'
            })
        
        elif step == 'password':
            username = request.session.get('login_username')
            password = value
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                # Clear auth flow
                request.session.pop('auth_flow', None)
                request.session.pop('auth_step', None)
                request.session.pop('login_username', None)
                
                return render(request, 'frontend/partials/chat_message.html', {
                    'is_bot': True,
                    'message': f'Welcome back, {user.username}!',
                    'redirect_to': 'dashboard',
                    'success': True
                })
            else:
                # Clear password step to try again
                request.session['auth_step'] = 'username'
                return render(request, 'frontend/partials/chat_message.html', {
                    'is_bot': True,
                    'error': True,
                    'message': 'We do not recognize that username and password. Please try again.',
                })
    
    def _handle_signup_flow(self, request, value):
        """Handle multi-step signup flow."""
        step = request.session.get('auth_step')
        signup_data = request.session.get('signup_data', {})
        
        if step == 'username':
            signup_data['username'] = value
            request.session['signup_data'] = signup_data
            request.session['auth_step'] = 'password'
            return render(request, 'frontend/partials/chat_message.html', {
                'is_bot': True,
                'message': 'Enter password:',
                'show_input': True,
                'input_type': 'password',
                'input_placeholder': 'Password',
                'show_password_stars': True
            })
        
        elif step == 'password':
            signup_data['password'] = value
            request.session['signup_data'] = signup_data
            request.session['auth_step'] = 'password_confirm'
            return render(request, 'frontend/partials/chat_message.html', {
                'is_bot': True,
                'message': 'Confirm password:',
                'show_input': True,
                'input_type': 'password',
                'input_placeholder': 'Confirm Password',
                'show_password_stars': True
            })
        
        elif step == 'password_confirm':
            if signup_data.get('password') != value:
                request.session['auth_step'] = 'password'
                return render(request, 'frontend/partials/chat_message.html', {
                    'is_bot': True,
                    'error': True,
                    'message': 'Passwords do not match. Please try again.',
                })
            
            request.session['auth_step'] = 'passkey'
            return render(request, 'frontend/partials/chat_message.html', {
                'is_bot': True,
                'message': 'Enter invite passkey:',
                'show_input': True,
                'input_type': 'password',
                'input_placeholder': 'Invite Passkey'
            })
        
        elif step == 'passkey':
            # Complete signup
            return self._complete_signup(request, value, signup_data)
    
    def _complete_signup(self, request, passkey, signup_data):
        """Complete the signup process."""
        from django.contrib.auth.models import User
        from django.db import transaction
        from apps.tenants.models import Tenant
        
        try:
            with transaction.atomic():
                # Validate passkey
                try:
                    invite = InvitePasskey.objects.get(
                        key=passkey,
                        is_active=True,
                        used_by__isnull=True
                    )
                    
                    # Check expiry
                    if invite.is_expired:
                        raise ValueError("Passkey has expired")
                    
                except InvitePasskey.DoesNotExist:
                    raise ValueError("Invalid passkey")
                
                # Create user
                user = User.objects.create_user(
                    username=signup_data['username'],
                    password=signup_data['password']
                )
                
                # Assign tenant
                if invite.tenant_scope:
                    tenant = invite.tenant_scope
                else:
                    # Create personal tenant
                    tenant = Tenant.objects.create(
                        name=f"{user.username}'s Workspace",
                        slug=user.username.lower()
                    )
                
                # Create user profile
                UserProfile.objects.create(
                    user=user,
                    tenant=tenant
                )
                
                # Mark passkey as used
                invite.used_by = user
                invite.is_active = False
                invite.save()
                
                # Log user in
                login(request, user)
                
                # Clear signup flow
                request.session.pop('auth_flow', None)
                request.session.pop('auth_step', None)
                request.session.pop('signup_data', None)
                
                return render(request, 'frontend/partials/chat_message.html', {
                    'is_bot': True,
                    'message': f'Welcome, {user.username}! Your account has been created.',
                    'redirect_to': 'dashboard',
                    'success': True
                })
                
        except ValueError as e:
            request.session['auth_step'] = 'username'
            request.session['signup_data'] = {}
            return render(request, 'frontend/partials/chat_message.html', {
                'is_bot': True,
                'error': True,
                'message': f'Signup could not be completed. {str(e)}. Please verify your invite passkey and credentials, or try "login".',
            })
        except Exception as e:
            logger.error(f"Signup error: {e}", exc_info=True)
            request.session['auth_step'] = 'username'
            request.session['signup_data'] = {}
            return render(request, 'frontend/partials/chat_message.html', {
                'is_bot': True,
                'error': True,
                'message': 'Signup could not be completed. Please try again or contact support.',
            })
    
    def _show_help(self, request, authenticated=False):
        """Show available commands."""
        if authenticated:
            commands = [
                'dashboard - View your dashboard',
                'worklogs - Manage work logs',
                'skills - View your skills',
                'reports - Generate reports',
                'settings - Account settings',
                'logout - Sign out',
                'help - Show this message'
            ]
        else:
            commands = [
                'login - Sign in to your account',
                'signup - Create a new account',
                'help - Show this message'
            ]
        
        return render(request, 'frontend/partials/chat_message.html', {
            'is_bot': True,
            'message': 'Available commands:',
            'commands': commands
        })
    
    def _handle_logout(self, request):
        """Handle user logout."""
        logout(request)
        return render(request, 'frontend/partials/chat_message.html', {
            'is_bot': True,
            'message': 'You have been logged out. Type "login" to sign in again.',
            'success': True,
            'reload_page': True
        })
    
    def _show_dashboard(self, request):
        """Show dashboard card in canvas."""
        return render(request, 'frontend/partials/chat_message.html', {
            'is_bot': True,
            'message': 'Loading your dashboard...',
            'trigger_canvas': 'dashboard'
        })
    
    def _handle_password_reset(self, request, message):
        """Handle password reset request."""
        return render(request, 'frontend/partials/chat_message.html', {
            'is_bot': True,
            'message': 'Password reset functionality is not yet implemented. Please contact your administrator.',
        })
    
    def _handle_admin_command(self, request, message):
        """Handle admin commands."""
        return render(request, 'frontend/partials/chat_message.html', {
            'is_bot': True,
            'message': 'Admin commands are not yet implemented in the chat interface. Please use the admin dashboard.',
        })


class ChatHistoryView(LoginRequiredMixin, View):
    """Return chat history for the current session."""
    
    def get(self, request):
        # TODO: Implement chat history from session or database
        return render(request, 'frontend/partials/chat_history.html', {
            'messages': []
        })


class DashboardCardView(LoginRequiredMixin, View):
    """Render dashboard card for canvas."""
    
    def get(self, request):
        # Get user stats
        from apps.worklog.models import WorkLog
        from apps.skills.models import Skill
        
        worklog_count = WorkLog.objects.filter(
            user=request.user
        ).count()
        
        skill_count = Skill.objects.filter(
            user=request.user
        ).count()
        
        # Get reserve balance
        try:
            profile = request.user.userprofile
            tenant = profile.tenant
            reserve_balance = getattr(tenant, 'reserve_balance_cents', 0) / 100
        except:
            reserve_balance = 0
        
        return render(request, 'frontend/partials/dashboard_card.html', {
            'username': request.user.username,
            'worklog_count': worklog_count,
            'skill_count': skill_count,
            'reserve_balance': reserve_balance
        })


class SettingsCardView(LoginRequiredMixin, View):
    """Render settings card for canvas."""
    
    def get(self, request):
        return render(request, 'frontend/partials/settings_card.html', {
            'user': request.user
        })


class ErrorCardView(View):
    """Render error card for canvas."""
    
    def get(self, request):
        error_message = request.GET.get('message', 'An error occurred.')
        return render(request, 'frontend/partials/error_card.html', {
            'error_message': error_message
        })


class LoginFormView(View):
    """Handle login form submission from canvas."""
    
    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me') == 'on'
        
        if not username or not password:
            return render(request, 'frontend/partials/login_form_card.html', {
                'error': 'Please enter both username and password.'
            })
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Set session expiry based on remember_me
            if not remember_me:
                # Session expires when browser closes
                request.session.set_expiry(0)
            else:
                # Session lasts 30 days
                request.session.set_expiry(2592000)  # 30 days in seconds
            
            # Return success message and trigger dashboard load
            return render(request, 'frontend/partials/login_success_card.html', {
                'username': user.username
            })
        else:
            # Generic error message to prevent user enumeration
            return render(request, 'frontend/partials/login_form_card.html', {
                'error': 'We do not recognize that username and password. Please try again.'
            })


class StatusBarView(View):
    """Return status bar information (for HTMX polling)."""
    
    def get(self, request):
        if not request.user.is_authenticated:
            return render(request, 'frontend/partials/status_bar.html', {
                'tokens_in': 0,
                'tokens_out': 0,
                'reserve_balance': 0,
                'is_authenticated': False
            })
        
        try:
            profile = request.user.userprofile
            tenant = profile.tenant
            reserve_balance_cents = getattr(tenant, 'reserve_balance_cents', 0)
            reserve_balance = reserve_balance_cents / 100
        except:
            reserve_balance = 0
        
        # TODO: Get actual token counts from jobs/observability
        tokens_in = 0
        tokens_out = 0
        
        return render(request, 'frontend/partials/status_bar.html', {
            'tokens_in': tokens_in,
            'tokens_out': tokens_out,
            'reserve_balance': reserve_balance,
            'is_authenticated': True
        })
