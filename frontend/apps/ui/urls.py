"""
URL configuration for UI app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('health/', views.health, name='health'),
    path('jobs/', views.jobs_list, name='jobs_list'),
    path('jobs/<uuid:job_id>/', views.job_detail, name='job_detail'),
]
