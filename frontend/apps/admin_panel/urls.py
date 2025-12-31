from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('metrics/', views.metrics_dashboard, name='metrics_dashboard'),
    path('billing/', views.billing_admin, name='billing_admin'),
    path('passkeys/', views.passkeys, name='passkeys'),
    path('users/', views.users, name='users'),
]
