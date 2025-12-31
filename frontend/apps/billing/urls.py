from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('settings/', views.settings, name='settings'),
    path('topup/', views.topup, name='topup'),
    path('ledger/', views.ledger, name='ledger'),
]
