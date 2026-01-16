"""
Root URL configuration.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import IsAdminUser

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('api/', include('apps.api.urls')),
    path('system/', include('apps.system.urls')),
    # API schema and docs
    path('api/schema/', SpectacularAPIView.as_view(permission_classes=[IsAdminUser]), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[IsAdminUser]), name='swagger-ui'),
]
