from django.urls import path
from . import views

app_name = 'worklog'

urlpatterns = [
    path('', views.index, name='index'),
    path('quick-add/', views.quick_add, name='quick_add'),
    path('<int:entry_id>/', views.detail, name='detail'),
]
