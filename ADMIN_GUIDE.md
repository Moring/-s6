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
>>> print(f"Invite URL: /accounts/signup/?passkey={passkey.code}")
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

### Session Security
Sessions are configured for security:
- HttpOnly cookies (no JavaScript access)
- Secure cookies in production (HTTPS only)
- SameSite: Lax (CSRF protection)
- 2-week expiry with sliding window

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

## Monitoring & Observability

### Health Checks
- Backend: `GET /api/healthz/` → `{"status": "ok"}`
- Frontend: `GET /healthz/` → `200 OK`

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
