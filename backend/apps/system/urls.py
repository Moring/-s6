"""
System dashboard URL configuration.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('overview/', views.overview, name='system-overview'),
    path('jobs/', views.jobs_list, name='system-jobs-list'),
    path('jobs/<uuid:job_id>/', views.job_detail, name='system-job-detail'),
    path('jobs/<uuid:job_id>/events/', views.job_events, name='system-job-events'),
    path('schedules/', views.schedules_list, name='system-schedules-list'),
    path('health/', views.health, name='system-health'),
]
