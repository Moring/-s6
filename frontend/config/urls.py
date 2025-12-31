"""
Root URL configuration for frontend.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('django-admin/', admin.site.urls),  # Renamed to avoid namespace conflict
    path('accounts/', include('allauth.urls')),
    path('profile/', include('apps.accounts.urls', namespace='accounts')),
    path('worklog/', include('apps.worklog.urls', namespace='worklog')),
    path('skills/', include('apps.skills.urls', namespace='skills')),
    path('reporting/', include('apps.reporting.urls', namespace='reporting')),
    path('billing/', include('apps.billing.urls', namespace='billing')),
    path('admin-panel/', include('apps.admin_panel.urls', namespace='admin_panel')),
    path('system/', include('apps.system.urls', namespace='system')),
    path('gamification/', include('apps.gamification.urls', namespace='gamification')),
    path('api-proxy/', include('apps.api_proxy.urls', namespace='api_proxy')),
    path('', include('apps.ui.urls', namespace='ui')),
]
