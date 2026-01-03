# AfterResume Admin Guide

Operational runbook for administrators and operators.

## Quick Start

### Local Development
```bash
# Start all services
task up

# Check health
curl http://localhost:8000/api/healthz/
curl http://localhost:3000/healthz/

# View logs
task logs

# Stop services
task down
```

### Production Deployment
```bash
# 1. Set environment variables (see .env.example)
cp .env.example .env
# Edit .env with production values

# 2. Validate environment
docker compose exec backend-api python manage.py validate_env

# 3. Run migrations
docker compose exec backend-api python manage.py migrate

# 4. Create superuser
docker compose exec backend-api python manage.py createsuperuser

# 5. Start services
docker compose up -d

# 6. Verify health
curl http://your-domain.com/api/healthz/
```

## Environment Configuration

### Required Variables
- `SECRET_KEY`: Django secret (generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- `POSTGRES_*` or `DATABASE_URL`: Database configuration
- `REDIS_URL`: Cache and queue backend

### Security Variables
- `SERVICE_TO_SERVICE_SECRET`: Shared secret for frontend→backend auth (generate strong random value)
- `CSRF_TRUSTED_ORIGINS`: e.g., `https://app.example.com,https://api.example.com`
- `ADMIN_IP_ALLOWLIST`: Comma-separated IPs for admin access (optional)

### Feature Flags
- `MAINTENANCE_MODE=True`: Enable maintenance mode (blocks all non-staff requests)
- `DISABLE_SHARING=True`: Disable share link creation
- `SKIP_SERVICE_AUTH=True`: Skip service-to-service auth (dev only)

### LLM Configuration
- `LLM_PROVIDER=local`: Use fake local provider (testing)
- `LLM_PROVIDER=vllm`: Use vLLM server
- `LLM_VLLM_ENDPOINT`: vLLM endpoint (required if provider=vllm)

### Email Configuration (optional)
- `EMAIL_HOST`, `EMAIL_PORT`: SMTP server
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`: SMTP credentials
- `EMAIL_USE_TLS=True`: Use TLS

### Stripe Configuration (optional)
- `STRIPE_SECRET_KEY`: Stripe secret key
- `STRIPE_PUBLISHABLE_KEY`: Stripe publishable key
- `STRIPE_WEBHOOK_SECRET`: Stripe webhook signing secret

## User Management

### Creating Users
Users must be invited via single-use passkeys:

```bash
# Create invite passkey
docker compose exec backend-api python manage.py shell
>>> from apps.invitations.models import InvitePasskey
>>> from django.contrib.auth.models import User
>>> from datetime import timedelta
>>> from django.utils import timezone
>>> 
>>> admin = User.objects.get(username='admin')
>>> passkey = InvitePasskey.objects.create(
...     code='UNIQUE-CODE-HERE',
...     created_by=admin,
...     expires_at=timezone.now() + timedelta(days=7),
...     max_uses=1
... )
>>> print(f"Passkey for SPA signup: {passkey.code}")
```

### Managing Roles
Roles: **owner**, **admin**, **member**, **read_only**

```python
# Add user to tenant with role
from apps.tenants.models import TenantMembership, Tenant
from django.contrib.auth.models import User

tenant = Tenant.objects.get(name='Example Tenant')
user = User.objects.get(username='newuser')

TenantMembership.objects.create(
    tenant=tenant,
    user=user,
    role='member',  # or 'admin', 'read_only'
    invited_by=request.user
)
```

### Permissions by Role

**Owner** (tenant.owner):
- All permissions
- Manage tenant settings
- Manage billing
- Manage users

**Admin** (TenantMembership role='admin'):
- Manage users
- All worklog/skill/report operations
- View billing
- View audit logs
- Cannot manage tenant or billing settings

**Member** (TenantMembership role='member'):
- Create/edit/delete own worklogs
- View own skills
- Generate reports
- Trigger jobs
- Create share links
- Export own data

**Read Only** (TenantMembership role='read_only'):
- View worklogs
- View skills
- View reports
- View jobs
- View share links

## Security Management

### Service-to-Service Authentication
Frontend→Backend calls require `X-Service-Token` header.

**Generate new token** (Python):
```python
from apps.api.service_auth import generate_service_token
token = generate_service_token()
print(token)
```

**Verify token**:
```python
from apps.api.service_auth import verify_service_token
is_valid, error = verify_service_token(token)
```

**Rotate secret**:
1. Generate new `SERVICE_TO_SERVICE_SECRET`
2. Update backend `.env`
3. Restart backend services
4. Update frontend configuration
5. Restart frontend services

### Admin IP Allowlist
Restrict admin access to specific IPs:

```bash
# In .env
ADMIN_IP_ALLOWLIST=192.168.1.10,10.0.0.5
```

Applies to:
- `/admin/`
- `/django-admin/`

### Token & Session Security
SPA authentication uses JWT access tokens with HttpOnly refresh cookies:
- Access tokens are short-lived and sent via `Authorization: Bearer <access>`
- Refresh tokens live in HttpOnly cookies (path `/api/auth/`) and rotate on refresh
- Session cookies remain for Django admin and staff-only server routes
- HttpOnly cookies, Secure in production, SameSite: Lax

## Operational Controls

### Maintenance Mode
Enable maintenance mode to block all requests (except staff):

```bash
# Enable
export MAINTENANCE_MODE=True
# Restart services

# Disable
unset MAINTENANCE_MODE
# Restart services
```

Maintenance mode returns:
- HTTP 503
- JSON: `{"error": "Service temporarily unavailable", "maintenance": true}`
- HTML: Maintenance message

### Disable Sharing Links
Emergency switch to disable share link creation:

```bash
# Disable
export DISABLE_SHARING=True
# Restart services

# Enable
unset DISABLE_SHARING
# Restart services
```

### Feature Flags
Manage features dynamically (requires cache access):

```python
from apps.api.feature_flags import SHARING_ENABLED, EXPORTS_ENABLED

# Disable sharing for 1 hour
SHARING_ENABLED.disable(ttl=3600)

# Enable exports
EXPORTS_ENABLED.enable()

# Check status
print(SHARING_ENABLED.is_enabled())
```

## Job Management

### View Job Status
```python
from apps.jobs.models import Job

# Recent jobs
recent_jobs = Job.objects.order_by('-created_at')[:10]
for job in recent_jobs:
    print(f"{job.type}: {job.status} - {job.created_at}")

# Failed jobs
failed = Job.objects.filter(status='failed')
print(f"Failed jobs: {failed.count()}")

# Jobs by type
worklog_jobs = Job.objects.filter(type='worklog.analyze')
print(f"Worklog analysis jobs: {worklog_jobs.count()}")
```

### Retry Failed Job
```python
from apps.jobs.dispatcher import enqueue

job = Job.objects.get(id='job-uuid')
new_job = enqueue(job.type, job.payload, user=job.user)
print(f"Retried as: {new_job.id}")
```

### Cancel Running Job
Jobs are processed asynchronously. To prevent reprocessing:

```python
job = Job.objects.get(id='job-uuid')
job.status = 'cancelled'
job.save()
```

## Gamification Management

### Overview
The gamification system encourages consistent logging and quality content through streaks, XP, badges, and weekly challenges. All reward logic runs asynchronously via DAG workflows with full audit logging.

### View Engagement Metrics
Admin endpoint for platform-wide gamification metrics:

```bash
curl -H "Authorization: Bearer ADMIN_TOKEN" \
  http://localhost:8000/api/admin/gamification/metrics/
```

Returns:
```json
{
  "summary": {
    "total_users_with_xp": 42,
    "avg_level": 3.2,
    "total_badges_awarded": 156,
    "active_streaks": 18
  },
  "streak_distribution": {
    "1-7": 25,
    "8-30": 12,
    "31-100": 3,
    "100+": 2
  },
  "daily_active_loggers": 15,
  "challenge_completion_rate": 0.68
}
```

### Configure Reward Rules
Edit reward configuration via Django admin:

```bash
# Access admin interface
open http://localhost:8000/admin/gamification/rewardconfig/
```

**Default Configuration**:
```python
{
    'min_entry_length': 20,           # Minimum characters for valid entry
    'max_entries_per_hour': 10,       # Spam prevention
    'duplicate_threshold_seconds': 60,  # Min seconds between entries
    'max_daily_xp': 200,              # Daily XP cap
    'xp_rules': {
        'base_entry': 10,
        'per_attachment': 5,          # Max 3 attachments count
        'per_tag': 3,                 # Max 5 tags count
        'length_bonus_threshold': 200,
        'length_bonus': 10,
        'outcome_bonus': 15,
        'metrics_bonus': 10
    },
    'max_freezes': 3                  # Streak freeze limit
}
```

To create new config version:
```python
from apps.gamification.models import RewardConfig

config = RewardConfig.objects.create(
    version=2,
    config={
        # your config
    },
    is_active=True  # Deactivates all others automatically
)
```

### Manage Badges
Add new badge definitions:

```python
from apps.gamification.models import BadgeDefinition

BadgeDefinition.objects.create(
    code='custom_badge',
    name='🎉 Custom Achievement',
    description='Your custom achievement description',
    category='special',
    icon='🎉',
    trigger_type='custom_trigger',
    trigger_threshold=0,
    is_active=True,
    order=100
)
```

Badge categories:
- `milestone`: Entry counts, levels
- `quality`: Attachments, outcomes
- `consistency`: Streaks
- `special`: Custom/seasonal badges

### Manage Challenges
Add or modify weekly challenges:

```python
from apps.gamification.models import ChallengeTemplate

ChallengeTemplate.objects.create(
    code='weekly_custom',
    name='Custom Weekly Challenge',
    description='Your challenge description',
    goal_type='log_days',  # or 'attach_evidence', 'write_outcomes'
    goal_target=5,
    xp_reward=50,
    recurrence='weekly',
    is_active=True,
    order=10
)
```

Challenges reset every Monday (week start).

### Manually Grant XP
Admin can manually grant XP to users:

```bash
curl -X POST \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/admin/gamification/grant/ \
  -d '{
    "user_id": 5,
    "amount": 50,
    "reason": "Exceptional contribution to project documentation"
  }'
```

Returns:
```json
{
  "success": true,
  "user_id": 5,
  "amount": 50,
  "new_total": 450,
  "new_level": 5,
  "event_id": "event-uuid"
}
```

### Manually Revoke Badge
Remove badge from user (use with caution):

```bash
curl -X POST \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/admin/gamification/revoke/ \
  -d '{
    "user_id": 5,
    "badge_code": "streak_30",
    "reason": "Badge awarded in error"
  }'
```

Returns:
```json
{
  "success": true,
  "user_id": 5,
  "badge_code": "streak_30",
  "revoked_at": "2025-12-31T15:30:00Z"
}
```

All manual actions are audited.

### Detect Abuse
Monitor XP events for suspicious patterns:

```python
from apps.gamification.models import XPEvent
from django.utils import timezone
from datetime import timedelta

# Check for XP spikes
recent = timezone.now() - timedelta(hours=1)
spike_users = (
    XPEvent.objects
    .filter(created_at__gte=recent)
    .values('user')
    .annotate(total=models.Sum('amount'))
    .filter(total__gt=100)  # > daily cap in 1 hour
)

# Check for rapid entry creation
from apps.worklog.models import WorkLog
rapid = (
    WorkLog.objects
    .filter(created_at__gte=recent)
    .values('user')
    .annotate(count=models.Count('id'))
    .filter(count__gt=10)  # > max_entries_per_hour
)
```

### Reset User Gamification Data
If a user requests reset (use with caution):

```python
from apps.gamification.models import UserStreak, UserXP, XPEvent, UserBadge, UserChallenge

user_id = 5

# Delete all gamification data
UserStreak.objects.filter(user_id=user_id).delete()
UserXP.objects.filter(user_id=user_id).delete()
XPEvent.objects.filter(user_id=user_id).delete()
UserBadge.objects.filter(user_id=user_id).delete()
UserChallenge.objects.filter(user_id=user_id).delete()

# New records will be created on next worklog entry
```

### Quiet Mode
Users can hide gamification UI via settings:

```python
from apps.gamification.models import GamificationSettings

settings, _ = GamificationSettings.objects.get_or_create(user_id=user_id)
settings.quiet_mode = True
settings.save()
```

Frontend respects `quiet_mode` and hides widgets, but reward evaluation still runs.

## Monitoring & Observability

### Health Checks
- Backend: `GET /api/healthz/` → `{"status": "ok"}`
- Frontend: `GET /healthz` → `200 OK`

### View Event Timeline
```python
from apps.observability.models import Event

# Recent events
events = Event.objects.order_by('-timestamp')[:20]
for event in events:
    print(f"[{event.level}] {event.source}: {event.message}")

# Events for a job
job_events = Event.objects.filter(job_id='job-uuid')
```

### Check System Metrics
```python
from apps.system.models import MetricsSnapshot

# Latest snapshot
snapshot = MetricsSnapshot.objects.latest('created_at')
print(f"Active users: {snapshot.metrics.get('active_users')}")
print(f"Total jobs: {snapshot.metrics.get('total_jobs')}")
```

### Correlation ID Tracing
All logs include correlation IDs. Search logs by correlation ID to trace a request through the entire system:

```bash
# Example: Find all logs for a request
docker compose logs backend-api | grep "correlation-id-here"
```

## Database Management

### Run Migrations
```bash
# Check migration status
docker compose exec backend-api python manage.py showmigrations

# Apply migrations
docker compose exec backend-api python manage.py migrate

# Create migration
docker compose exec backend-api python manage.py makemigrations
```

### Backup Database
```bash
# Dump database
docker compose exec postgres pg_dump -U afterresume afterresume > backup.sql

# Restore database
docker compose exec -T postgres psql -U afterresume afterresume < backup.sql
```

### Backup MinIO
```bash
# Use MinIO client (mc)
docker run --rm -it \
  --network afterresume-net \
  minio/mc:latest \
  mirror minio-alias/afterresume ./minio-backup/
```

## Troubleshooting

### Service Won't Start
1. Check environment variables: `docker compose exec backend-api python manage.py validate_env --print-status`
2. Check logs: `docker compose logs backend-api --tail=100`
3. Verify database connection: `docker compose exec backend-api python manage.py dbshell`
4. Check migrations: `docker compose exec backend-api python manage.py showmigrations`

### Jobs Not Processing
1. Check worker is running: `docker compose ps | grep worker`
2. Check worker logs: `docker compose logs backend-worker --tail=50`
3. Verify Valkey connection: `docker compose exec valkey valkey-cli ping`
4. Check job queue: Query `jobs_job` table for stuck jobs

### Rate Limiting Issues
Users experiencing 429 errors:

```python
from apps.api.rate_limiting import AUTH_RATE_LIMITER
# Reset rate limit for user
AUTH_RATE_LIMITER.reset('user-ip-address')
```

### Session Issues
Clear user sessions:

```python
from django.contrib.sessions.models import Session
Session.objects.all().delete()
```

## Audit & Compliance

### View Audit Logs
```python
from apps.auditing.models import AuthEvent

# Recent auth events
events = AuthEvent.objects.order_by('-timestamp')[:20]
for event in events:
    print(f"{event.event_type}: {event.user} from {event.ip_address}")

# Failed logins
failed = AuthEvent.objects.filter(event_type='login_failure', success=False)
```

### Export User Data
```python
from apps.accounts.models import UserProfile

user = User.objects.get(username='user@example.com')
profile = user.profile

# Export data (Human TODO: implement full export)
data = {
    'user': {
        'username': user.username,
        'email': user.email,
    },
    'tenant': profile.tenant.name,
    'created': profile.created_at.isoformat(),
}
```

## Human TODOs

### Production Setup
- [ ] Generate strong `SECRET_KEY` and `SERVICE_TO_SERVICE_SECRET`
- [ ] Configure DNS and SSL/TLS certificates
- [ ] Set up SMTP server for email notifications
- [ ] Configure vLLM endpoint for production AI workloads
- [ ] Set up Stripe account and configure webhooks
- [ ] Configure backup automation for Postgres and MinIO
- [ ] Set up monitoring/alerting (Prometheus, Grafana, or cloud provider)
- [ ] Configure log aggregation (ELK, CloudWatch, or similar)
- [ ] Set up MFA provider for admin accounts
- [ ] Configure malware scanning for file uploads
- [ ] Set up automatic backup verification
- [ ] Configure disaster recovery procedures
- [ ] Set up autoscaling for workers based on queue depth

### Operational
- [ ] Document runbook for common incidents
- [ ] Create alert rules for error rates, queue depth, payment failures
- [ ] Set up on-call rotation and escalation procedures
- [ ] Document rollback procedures for migrations
- [ ] Create backup and restore testing schedule
- [ ] Set up security scanning for dependencies
- [ ] Configure rate limit thresholds per environment
- [ ] Document quota adjustments for different plans

## Support

For issues or questions:
1. Check logs: `docker compose logs`
2. Review documentation: `README.md`, `ARCHITECTURE.md`, `CHANGE_LOG.md`
3. Run health checks
4. Verify environment configuration
5. Check system dashboard at `/admin/`
