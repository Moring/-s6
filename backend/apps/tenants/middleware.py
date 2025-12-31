"""
Tenant resolution middleware.
Attaches tenant to request based on authenticated user.
"""


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        
        if request.user.is_authenticated:
            try:
                request.tenant = request.user.tenant
            except AttributeError:
                # User has no tenant yet (shouldn't happen after signup)
                pass
        
        response = self.get_response(request)
        return response
