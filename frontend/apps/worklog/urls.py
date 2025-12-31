from django.urls import path
from . import views

app_name = 'worklog'

urlpatterns = [
    path('', views.index, name='index'),
    path('quick-add-modal/', views.quick_add_modal, name='quick_add_modal'),
    path('quick-add-submit/', views.quick_add_submit, name='quick_add_submit'),
    path('list/', views.worklog_list_partial, name='list_partial'),
    path('<int:entry_id>/', views.detail, name='detail'),
    path('<int:entry_id>/edit/', views.edit_submit, name='edit'),
    path('<int:entry_id>/delete/', views.delete, name='delete'),
    path('<int:entry_id>/attachments/', views.upload_attachment, name='upload_attachment'),
    path('<int:entry_id>/attachments/<int:attachment_id>/', views.delete_attachment, name='delete_attachment'),
]
