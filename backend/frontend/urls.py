"""
Frontend URL configuration.
"""
from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    # Main interface
    path('', views.IndexView.as_view(), name='index'),
    
    # Chat endpoints (HTMX)
    path('chat/send/', views.ChatSendView.as_view(), name='chat_send'),
    path('chat/history/', views.ChatHistoryView.as_view(), name='chat_history'),
    
    # Canvas endpoints (HTMX)
    path('canvas/dashboard/', views.DashboardCardView.as_view(), name='dashboard_card'),
    path('canvas/settings/', views.SettingsCardView.as_view(), name='settings_card'),
    path('canvas/error/', views.ErrorCardView.as_view(), name='error_card'),
    
    # Auth endpoints
    path('login/', views.LoginFormView.as_view(), name='login_form'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # Status bar (HTMX polling)
    path('status/', views.StatusBarView.as_view(), name='status_bar'),
]
