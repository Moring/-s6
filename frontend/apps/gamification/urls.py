"""Gamification URLs."""
from django.urls import path
from . import views

app_name = 'gamification'

urlpatterns = [
    path('achievements/', views.achievements, name='achievements'),
    path('challenges/', views.challenges, name='challenges'),
    path('summary/', views.summary_partial, name='summary-partial'),
]
