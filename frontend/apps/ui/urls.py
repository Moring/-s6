"""
URL configuration for UI app.
"""
from django.urls import path
from . import views

app_name = 'ui'

urlpatterns = [
    path('', views.index, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_file, name='upload_file'),
    path('health/', views.health, name='health'),
    path('jobs/', views.jobs_list, name='jobs_list'),
    path('jobs/<uuid:job_id>/', views.job_detail, name='job_detail'),
]
