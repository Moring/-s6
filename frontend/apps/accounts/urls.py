"""
URL configuration for accounts app.
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('signup-with-passkey/', views.signup_with_passkey, name='signup-passkey'),
]
