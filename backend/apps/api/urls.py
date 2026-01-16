"""
API URL configuration.
"""
from django.urls import path
from .views import worklog, skills, reports, jobs, health, artifacts, auth, admin, system_metrics, billing, status, attachments, system_controls, gamification

urlpatterns = [
    # Health
    path('healthz/', health.healthz, name='api-healthz'),
    path('readyz/', health.readyz, name='api-readyz'),
    
    # Status Bar
    path('status/bar/', status.status_bar, name='status-bar'),
    
    # Auth
    path('auth/signup/', auth.signup, name='auth-signup'),
    path('auth/login/', auth.login_view, name='auth-login'),
    path('auth/logout/', auth.logout_view, name='auth-logout'),
    path('auth/token/', auth.get_token, name='auth-token'),
    path('auth/token/refresh/', auth.refresh_token, name='auth-token-refresh'),
    path('auth/password/change/', auth.password_change, name='auth-password-change'),
    path('auth/password/reset/', auth.password_reset_request, name='auth-password-reset'),
    path('me/', auth.me, name='auth-me'),
    
    # Admin - Passkeys
    path('admin/passkeys/', admin.create_passkey, name='admin-passkey-create'),
    path('admin/passkeys/list/', admin.list_passkeys, name='admin-passkey-list'),
    
    # Admin - Users
    path('admin/users/', admin.list_users, name='admin-user-list'),
    path('admin/users/<int:user_id>/', admin.update_user, name='admin-user-update'),
    path('admin/users/<int:user_id>/reset-password/', admin.admin_reset_password, name='admin-user-reset-password'),
    
    # Admin - Audit
    path('admin/audit-events/', admin.list_audit_events, name='admin-audit-events'),
    
    # System Controls (Phase 2)
    path('admin/system-controls/', system_controls.system_controls_view, name='system-controls'),
    path('admin/system-controls/feature-flag/', system_controls.toggle_feature_flag, name='toggle-feature-flag'),
    path('admin/failed-jobs/', system_controls.failed_jobs_view, name='failed-jobs'),
    path('admin/failed-jobs/<uuid:job_id>/retry/', system_controls.retry_failed_job, name='retry-failed-job'),
    path('admin/rate-limits/', system_controls.rate_limit_status_view, name='rate-limits'),
    path('admin/rate-limits/reset/', system_controls.reset_rate_limit, name='reset-rate-limit'),
    
    # System Metrics (Admin only)
    path('system/metrics/summary/', system_metrics.metrics_summary, name='system-metrics-summary'),
    path('system/metrics/timeseries/', system_metrics.metrics_timeseries, name='system-metrics-timeseries'),
    path('system/metrics/cohorts/', system_metrics.metrics_cohorts, name='system-metrics-cohorts'),
    path('system/metrics/export.csv', system_metrics.metrics_export_csv, name='system-metrics-export-csv'),
    path('system/metrics/config/', system_metrics.metrics_config, name='system-metrics-config'),
    
    # Artifacts (file uploads)
    path('artifacts/upload/', artifacts.upload_file, name='artifact-upload'),
    path('artifacts/', artifacts.list_files, name='artifact-list'),
    
    # Worklogs
    path('worklogs/', worklog.WorkLogListCreateView.as_view(), name='worklog-list'),
    path('worklogs/<int:pk>/', worklog.WorkLogDetailView.as_view(), name='worklog-detail'),
    path('worklogs/<int:pk>/analyze/', worklog.analyze_worklog, name='worklog-analyze'),
    
    # Clients
    path('clients/', worklog.ClientListCreateView.as_view(), name='client-list'),
    path('clients/<int:pk>/', worklog.ClientDetailView.as_view(), name='client-detail'),
    
    # Projects
    path('projects/', worklog.ProjectListCreateView.as_view(), name='project-list'),
    path('projects/<int:pk>/', worklog.ProjectDetailView.as_view(), name='project-detail'),
    
    # Sprints
    path('sprints/', worklog.SprintListCreateView.as_view(), name='sprint-list'),
    path('sprints/<int:pk>/', worklog.SprintDetailView.as_view(), name='sprint-detail'),
    
    # Worklog Attachments
    path('worklogs/<int:worklog_id>/attachments/', attachments.upload_attachment, name='attachment-upload'),
    path('worklogs/<int:worklog_id>/attachments/<int:attachment_id>/', attachments.delete_attachment, name='attachment-delete'),
    path('worklogs/<int:worklog_id>/attachments-list/', attachments.list_attachments, name='attachment-list'),
    
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
    
    # Billing - User endpoints
    path('billing/reserve/balance/', billing.reserve_balance, name='billing-reserve-balance'),
    path('billing/reserve/ledger/', billing.reserve_ledger, name='billing-reserve-ledger'),
    path('billing/topup/session/', billing.create_topup_session, name='billing-topup-session'),
    path('billing/portal/session/', billing.create_portal_session, name='billing-portal-session'),
    path('billing/profile/', billing.billing_profile, name='billing-profile'),
    path('billing/webhook/', billing.stripe_webhook, name='billing-webhook'),
    
    # Billing - Admin endpoints
    path('billing/admin/reserve/summary/', billing.admin_reserve_summary, name='billing-admin-reserve-summary'),
    path('billing/admin/usage/costs/', billing.admin_usage_costs, name='billing-admin-usage-costs'),
    path('billing/admin/reserve/adjust/', billing.admin_adjust_reserve, name='billing-admin-adjust-reserve'),
    path('billing/admin/ledger/export.csv', billing.admin_export_ledger_csv, name='billing-admin-export-csv'),
    
    # Gamification - User endpoints
    path('gamification/summary/', gamification.GamificationSummaryView.as_view(), name='gamification-summary'),
    path('gamification/badges/', gamification.BadgesView.as_view(), name='gamification-badges'),
    path('gamification/challenges/', gamification.ChallengesView.as_view(), name='gamification-challenges'),
    path('gamification/settings/', gamification.GamificationSettingsView.as_view(), name='gamification-settings'),
    
    # Gamification - Admin endpoints
    path('admin/gamification/metrics/', gamification.AdminGamificationMetricsView.as_view(), name='admin-gamification-metrics'),
    path('admin/gamification/grant/', gamification.AdminManualXPGrantView.as_view(), name='admin-gamification-grant'),
    path('admin/gamification/revoke/', gamification.AdminManualBadgeRevokeView.as_view(), name='admin-gamification-revoke'),
]
