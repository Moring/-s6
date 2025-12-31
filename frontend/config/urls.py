"""
Root URL configuration for frontend.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('profile/', include('apps.accounts.urls', namespace='accounts')),
    path('', include('apps.ui.urls', namespace='ui')),
]
