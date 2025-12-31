"""
API proxy URLs for HTMX partial updates.
"""
from django.urls import path
from . import views

app_name = 'api_proxy'

urlpatterns = [
    path('status-bar/', views.status_bar, name='status_bar'),
    path('reserve-balance/', views.reserve_balance, name='reserve_balance'),
]
