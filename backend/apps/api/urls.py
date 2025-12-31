"""
API URL configuration.
"""
from django.urls import path
from .views import worklog, skills, reports, jobs, health, artifacts, auth, admin

urlpatterns = [
    # Health
    path('healthz/', health.healthz, name='api-healthz'),
    path('readyz/', health.readyz, name='api-readyz'),
    
    # Auth
    path('auth/signup/', auth.signup, name='auth-signup'),
    path('auth/login/', auth.login_view, name='auth-login'),
    path('auth/logout/', auth.logout_view, name='auth-logout'),
    path('auth/password/change/', auth.password_change, name='auth-password-change'),
    path('auth/password/reset/', auth.password_reset_request, name='auth-password-reset'),
    path('me/', auth.me, name='auth-me'),
    
    # Admin - Passkeys
    path('admin/passkeys/', admin.create_passkey, name='admin-passkey-create'),
    path('admin/passkeys/', admin.list_passkeys, name='admin-passkey-list'),
    
    # Admin - Users
    path('admin/users/', admin.list_users, name='admin-user-list'),
    path('admin/users/<int:user_id>/', admin.update_user, name='admin-user-update'),
    path('admin/users/<int:user_id>/reset-password/', admin.admin_reset_password, name='admin-user-reset-password'),
    
    # Admin - Audit
    path('admin/audit-events/', admin.list_audit_events, name='admin-audit-events'),
    
    # Artifacts (file uploads)
    path('artifacts/upload/', artifacts.upload_file, name='artifact-upload'),
    path('artifacts/', artifacts.list_files, name='artifact-list'),
    
    # Worklogs
    path('worklogs/', worklog.WorkLogListCreateView.as_view(), name='worklog-list'),
    path('worklogs/<int:pk>/', worklog.WorkLogDetailView.as_view(), name='worklog-detail'),
    path('worklogs/<int:pk>/analyze/', worklog.analyze_worklog, name='worklog-analyze'),
    
    # Skills
    path('skills/', skills.SkillListView.as_view(), name='skill-list'),
    path('skills/<int:pk>/evidence/', skills.SkillEvidenceView.as_view(), name='skill-evidence'),
    path('skills/recompute/', skills.recompute_skills, name='skills-recompute'),
    
    # Reports
    path('reports/', reports.ReportListView.as_view(), name='report-list'),
    path('reports/generate/', reports.generate_report_view, name='report-generate'),
    path('resume/refresh/', reports.refresh_resume_view, name='resume-refresh'),
    
    # Jobs
    path('jobs/<uuid:job_id>/', jobs.job_detail, name='job-detail'),
    path('jobs/<uuid:job_id>/events/', jobs.job_events, name='job-events'),
]
