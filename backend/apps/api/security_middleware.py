"""
Security middleware for web hardening.
Implements security headers, CSRF protection, and session security.
"""
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to all responses.
    """
    
    def process_response(self, request, response):
        # Content Security Policy
        # Build CSP allowing optional extra sources configured in settings.CSP_EXTRA_SRC
        extra_src = getattr(settings, 'CSP_EXTRA_SRC', []) or []
        # join any provided extra hosts into directives
        extra_script_src = ' '.join(extra_src) if extra_src else ''
        extra_style_src = ' '.join(extra_src) if extra_src else ''
        extra_connect_src = ' '.join(extra_src) if extra_src else ''
        extra_font_src = ' '.join(extra_src) if extra_src else ''

        if not settings.DEBUG:
            # Production CSP - strict, but include any configured extras
            csp = (
                "default-src 'self'; "
                f"script-src 'self' 'unsafe-inline' 'unsafe-eval' {extra_script_src}; "
                f"style-src 'self' 'unsafe-inline' {extra_style_src}; "
                "img-src 'self' data: https:; "
                f"font-src 'self' data: {extra_font_src}; "
                f"connect-src 'self' {extra_connect_src}; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
        else:
            # Development CSP - relaxed, include extras and ws
            csp = (
                "default-src 'self'; "
                f"script-src 'self' 'unsafe-inline' 'unsafe-eval' {extra_script_src}; "
                f"style-src 'self' 'unsafe-inline' {extra_style_src}; "
                "img-src 'self' data: https:; "
                f"font-src 'self' data: {extra_font_src}; "
                f"connect-src 'self' ws: wss: {extra_connect_src}; "
            )
        response['Content-Security-Policy'] = csp
        
        # Strict Transport Security (HTTPS only in production)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # X-Frame-Options
        response['X-Frame-Options'] = 'DENY'
        
        # X-Content-Type-Options
        response['X-Content-Type-Options'] = 'nosniff'
        
        # X-XSS-Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy
        response['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'accelerometer=()'
        )
        
        return response


class IPAllowlistMiddleware(MiddlewareMixin):
    """
    Optional IP allowlist for admin endpoints.
    """
    
    def process_request(self, request):
        from django.http import HttpResponseForbidden
        
        # Get IP allowlist from settings
        admin_ip_allowlist = getattr(settings, 'ADMIN_IP_ALLOWLIST', [])
        
        # Skip if no allowlist configured
        if not admin_ip_allowlist:
            return None
        
        # Only apply to admin paths
        if not (request.path.startswith('/admin/') or 
                request.path.startswith('/django-admin/')):
            return None
        
        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.META.get('REMOTE_ADDR')
        
        # Check if IP is allowed
        if client_ip not in admin_ip_allowlist:
            return HttpResponseForbidden(
                'Access denied: IP address not allowed for admin access'
            )
        
        return None


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Enable maintenance mode to block all requests.
    """
    
    def process_request(self, request):
        from django.http import JsonResponse, HttpResponse
        
        # Check if maintenance mode is enabled
        maintenance_mode = getattr(settings, 'MAINTENANCE_MODE', False)
        
        if not maintenance_mode:
            return None
        
        # Allow health checks
        if request.path in ['/healthz/', '/api/healthz/', '/health/']:
            return None
        
        # Allow staff access
        if request.user.is_authenticated and request.user.is_staff:
            return None
        
        # Return maintenance response
        if request.content_type == 'application/json' or request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Service temporarily unavailable',
                'maintenance': True
            }, status=503)
        
        return HttpResponse(
            '<h1>Maintenance Mode</h1>'
            '<p>We are performing scheduled maintenance. Please check back shortly.</p>',
            status=503,
            content_type='text/html'
        )
