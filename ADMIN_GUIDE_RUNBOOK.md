# AfterResume Admin Guide & Runbook

**Version**: 2.0  
**Last Updated**: 2025-12-31  
**Status**: Production-Ready MVP

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [System Architecture](#system-architecture)
3. [Initial Setup](#initial-setup)
4. [User Management](#user-management)
5. [Authentication & Security](#authentication--security)
6. [Billing & Reserve Management](#billing--reserve-management)
7. [System Monitoring](#system-monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Backup & Recovery](#backup--recovery)
10. [Production Deployment](#production-deployment)
11. [API Reference](#api-reference)

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Task CLI (optional but recommended: https://taskfile.dev)
- curl & jq for testing
- Git for version control

### Start System
```bash
# Clone repository (if not already)
git clone <repository-url>
cd afterresume

# Copy environment template
cp .env.example .env

# Edit .env with your settings
vim .env

# Start all services
task up

# Run migrations and bootstrap
task bootstrap
```

### Verify System Health
```bash
# Check all services
task status

# Test backend API
curl http://localhost:8000/api/healthz/

# Test frontend
curl http://localhost:3000/health/

# Test frontend → backend connectivity
docker exec afterresume-frontend curl -s http://backend-api:8000/api/healthz/
```

### Access Points
- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Django Admin**: http://localhost:8000/admin/
- **MinIO Console**: http://localhost:9001

### Default Credentials
- **Admin Username**: `admin`
- **Admin Password**: `admin123`  
  ⚠️ **CRITICAL**: Change immediately in production!

---

## System Architecture

### Service Topology
```
┌─────────────────────────────────────────────────────────┐
│                  AfterResume System                     │
│                                                         │
│  Frontend (Port 3000)          Backend (Port 8000)     │
│  ├─ Django + HTMX UI           ├─ Django + DRF API     │
│  ├─ Valkey Cache (6380)        ├─ Postgres Database    │
│  ├─ Sessions & UI state        ├─ Valkey Queue (6379)  │
│  └─ Calls Backend via HTTP     ├─ MinIO Storage        │
│                                 ├─ Huey Workers         │
│                                 └─ AI Agents + LLM      │
└─────────────────────────────────────────────────────────┘
```

### Key Design Principles
1. **Frontend** is presentation-only (no direct DB/storage access)
2. **Backend** owns all persistence and orchestration
3. **Multi-tenant** by default (data isolated per tenant)
4. **Job-driven** for async/AI work
5. **Event timeline** for observability

### Network Configuration
- Both frontend and backend use shared Docker network: `afterresume-net`
- Frontend calls backend via `http://backend-api:8000`
- All services use internal networking except published ports

---

## Initial Setup

### Environment Configuration

Critical `.env` variables:

```bash
# Django Core
SECRET_KEY=<generate-strong-key>  # python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=0  # MUST be 0 in production
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
POSTGRES_DB=afterresume
POSTGRES_USER=afterresume
POSTGRES_PASSWORD=<strong-password>
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Backend API URL (for frontend)
BACKEND_BASE_URL=http://backend-api:8000  # Internal Docker network

# Session Security (production)
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Stripe (get from https://dashboard.stripe.com/)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# MinIO/S3
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=<strong-password>
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=afterresume-artifacts

# Email (optional for MVP, required for password reset)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<sendgrid-api-key>
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# LLM Provider
LLM_PROVIDER=local  # or 'openai', 'anthropic', etc.
OPENAI_API_KEY=<api-key-if-using-openai>
```

### Bootstrap Process

The bootstrap script creates:
- Default admin user
- Default tenant
- User profile linked to tenant
- Reserve account for billing

```bash
# Run bootstrap
task bootstrap

# Or manually:
docker compose -f backend/docker-compose.yml exec backend-api python manage.py migrate
docker compose -f backend/docker-compose.yml exec backend-api python scripts/bootstrap.py
```

### Verify Bootstrap
```bash
# Check admin user exists
docker compose -f backend/docker-compose.yml exec backend-api python manage.py shell <<EOF
from django.contrib.auth.models import User
admin = User.objects.filter(username='admin').first()
print(f"Admin: {admin}")
print(f"Profile: {admin.profile if hasattr(admin, 'profile') else 'NO PROFILE'}")
print(f"Tenant: {admin.profile.tenant if hasattr(admin, 'profile') else 'N/A'}")
EOF
```

---

## User Management

### Invite-Only Signup System

AfterResume uses **passkey-gated signup** for controlled user onboarding.

### Creating Invite Passkeys

**Method 1: Django Admin** (Recommended)
1. Log into Django admin: http://localhost:8000/admin/
2. Navigate to "Invitations" → "Invite Passkeys"
3. Click "Add Invite Passkey"
4. Fill in:
   - Created by: (auto-filled)
   - Expires at: (future date/time)
   - Notes: "Invite for [person/reason]"
5. Save
6. Copy the displayed passkey and send to user

**Method 2: Django Shell**
```bash
docker compose -f backend/docker-compose.yml exec backend-api python manage.py shell
```

```python
from apps.invitations.models import InvitePasskey
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

# Get admin user (or another staff member)
admin = User.objects.filter(username='admin').first()

# Generate passkey
raw_key = InvitePasskey.generate_key()
hashed = InvitePasskey.hash_key(raw_key)

# Create passkey record
passkey = InvitePasskey.objects.create(
    key=hashed,
    raw_key=raw_key,
    created_by=admin,
    expires_at=timezone.now() + timedelta(days=7),
    notes="Invite for John Doe - john@example.com"
)

print(f"PASSKEY: {raw_key}")
print(f"Expires: {passkey.expires_at}")
```

**Method 3: Backend API** (requires staff auth)
```bash
curl -X POST http://localhost:8000/api/admin/passkeys/ \
  -H "Authorization: Token <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "expires_days": 7,
    "notes": "Invite for Jane Smith"
  }'
```

### Passkey Properties
- **Single-use**: Automatically invalidated after successful signup
- **Expiration**: Must be used before expiry date
- **Audit trail**: Tracks who created it, when used, by whom
- **Hashed storage**: Raw passkey never stored in DB

### Managing Users

**List All Users:**
```bash
# Via Django Admin
http://localhost:8000/admin/auth/user/

# Via API
curl -H "Authorization: Token <admin-token>" \
  http://localhost:8000/api/admin/users/
```

**Disable/Enable User:**
```bash
curl -X PATCH http://localhost:8000/api/admin/users/<user_id>/ \
  -H "Authorization: Token <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

**Reset User Password (Admin):**
```bash
curl -X POST http://localhost:8000/api/admin/users/<user_id>/reset-password/ \
  -H "Authorization: Token <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"new_password": "TemporaryPassword123!"}'
```

**View User Activity:**
```bash
# Audit events for specific user
curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/api/admin/audit-events/?user_id=<user_id>"
```

---

## Authentication & Security

### Authentication Flow

1. **User logs into Frontend** (Django + allauth)
2. **Frontend obtains Backend token** (automatic via custom login form)
3. **Frontend stores token in session**
4. **All backend API calls use token** (Authorization: Token <key>)

### Getting an API Token

Users don't need to manually get tokens (handled automatically), but for API/script access:

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your-username",
    "password": "your-password"
  }'
```

Response:
```json
{
  "token": "f0cf61f42b3456a22f8a2b93caaf984ff0e338a3",
  "user": {...}
}
```

### Session Configuration

**Frontend Sessions:**
- Engine: Valkey cache backend
- Expiry: 2 weeks (configurable)
- Remember me: Optional (checkbox on login)
- Secure cookies: Enabled in production

**Backend Sessions:**
- DRF Token Authentication (persistent)
- Session Authentication (for Django admin)

### Password Policy

Current requirements:
- Minimum 8 characters
- Django default validators (not too common, not entirely numeric, not too similar to username)

To strengthen:
```python
# backend/config/settings/base.py
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
```

### Rate Limiting

**Status**: Backend configured, middleware TODO

To enable rate limiting:
1. Add `django-ratelimit` to backend dependencies
2. Apply decorators to auth endpoints
3. Configure in settings

Example:
```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST')
def login_view(request):
    ...
```

### Security Audit Log

All authentication events are logged to `AuthEvent` model:
- Login success/failure
- Signup
- Password changes/resets
- Passkey usage
- Admin actions

Query audit log:
```bash
curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/api/admin/audit-events/?event_type=login&limit=50"
```

---

## Billing & Reserve Management

### Reserve Account System

Each tenant has a **prepaid reserve balance** for usage-based billing.

### Check Reserve Balance

**Via Frontend UI:**
- Log in → Top status bar shows current balance
- Navigate to Billing settings page

**Via API:**
```bash
curl -H "Authorization: Token <user-token>" \
  http://localhost:8000/api/billing/reserve/balance/

# Response:
{
  "balance_cents": 5000,
  "balance_dollars": 50.0,
  "currency": "USD",
  "is_low": false,
  "policy": "warn"
}
```

### Top-Up Reserve (User)

**Via Stripe Checkout:**
```bash
# Create checkout session
curl -X POST http://localhost:8000/api/billing/topup/session/ \
  -H "Authorization: Token <user-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_dollars": 50
  }'

# Response includes checkout URL:
{
  "session_id": "cs_test_...",
  "checkout_url": "https://checkout.stripe.com/..."
}
```

User visits checkout URL, completes payment, and webhook credits their reserve.

### Manual Credit (Admin Only)

For promotional credits, refunds, or corrections:

```bash
curl -X POST http://localhost:8000/api/billing/admin/reserve/adjust/ \
  -H "Authorization: Token <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "amount_cents": 10000,
    "reason": "Promotional credit for early adopter"
  }'
```

**All manual adjustments are audited** with admin username, reason, and timestamp.

### Reserve Ledger

View transaction history:
```bash
curl -H "Authorization: Token <user-token>" \
  "http://localhost:8000/api/billing/reserve/ledger/?limit=50"
```

Export ledger (admin):
```bash
curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/api/billing/admin/ledger/export.csv" \
  > ledger_export.csv
```

### Low Balance Policies

Configurable per tenant:
- **BLOCK**: Prevent job execution when reserve insufficient
- **WARN**: Allow execution but show warnings
- **LIMITED**: Allow some operations, block expensive ones

Set policy:
```bash
curl -X PATCH http://localhost:8000/api/billing/profile/ \
  -H "Authorization: Token <user-token>" \
  -H "Content-Type: application/json" \
  -d '{"low_balance_policy": "block"}'
```

### Stripe Webhook Setup (Production)

1. **Create webhook endpoint in Stripe dashboard:**
   - URL: `https://yourdomain.com/api/billing/webhook/`
   - Events to send:
     - `checkout.session.completed`
     - `payment_intent.succeeded`
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_failed`

2. **Copy webhook signing secret** → `.env`:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

3. **Test webhook**:
   ```bash
   stripe trigger checkout.session.completed
   ```

### Cost Tracking

Usage costs are computed per job execution:
- LLM token costs (per model/provider)
- Non-LLM costs (storage, API calls, compute)
- Costs deducted automatically after job completion

View usage costs (admin):
```bash
curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/api/billing/admin/usage/costs/?start_date=2025-12-01&end_date=2025-12-31"
```

---

## System Monitoring

### Health Checks

**Basic Health:**
```bash
# Backend API
curl http://localhost:8000/api/healthz/

# Frontend
curl http://localhost:3000/health/

# Backend readiness (checks DB, cache, storage)
curl http://localhost:8000/api/readyz/
```

**Deep Health (staff only):**
```bash
curl -H "Authorization: Token <admin-token>" \
  http://localhost:8000/system/health/
```

Returns:
- Database connectivity
- Valkey connectivity
- MinIO connectivity
- Job queue health
- Worker status

### Job Monitoring

**List Recent Jobs:**
```bash
curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/system/jobs/?limit=20&status=running"
```

**Job Detail + Events:**
```bash
curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/api/jobs/<job-id>/"

curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/api/jobs/<job-id>/events/"
```

**Job Statuses:**
- `queued` - Waiting to run
- `running` - Currently executing
- `success` - Completed successfully
- `failed` - Execution failed
- `cancelled` - Manually cancelled

### Observability Events

Every job emits structured events:
- Job start/end
- Agent execution
- LLM calls (model, tokens, latency, cost)
- Errors and retries
- State transitions

Query events:
```bash
docker compose -f backend/docker-compose.yml exec backend-api python manage.py shell
```

```python
from apps.observability.models import EventRecord
from apps.jobs.models import Job

# Get all events for a job
job = Job.objects.filter(name='worklog_analysis').first()
events = EventRecord.objects.filter(job_run_id=job.current_run_id).order_by('timestamp')

for event in events:
    print(f"{event.timestamp} | {event.event_type} | {event.message}")
```

### Log Files

**Container Logs:**
```bash
# All services
task logs

# Specific service
task logs-backend
task logs-frontend
task logs-worker

# Or directly with Docker
docker logs afterresume-backend-api --tail=100 -f
```

**Application Logs** (inside containers):
- Backend: `/app/logs/` (if configured)
- Frontend: `/app/logs/`

Configure structured logging in production with:
- JSON formatting
- Log aggregation (e.g., Datadog, CloudWatch, ELK)
- Error tracking (e.g., Sentry)

### Performance Metrics

**Built-in:**
- Request latency (via DRF)
- Job execution time (via event timeline)
- LLM call latency (via observability)

**TODO (Production):**
- APM integration (e.g., New Relic, Datadog APM)
- Database query performance
- Cache hit rates
- Worker queue depth

---

## Troubleshooting

### Common Issues

#### 1. Frontend Can't Reach Backend

**Symptoms:**
- Status bar shows "—" or "offline"
- API calls fail in browser console
- Network errors in logs

**Diagnosis:**
```bash
# Check Docker network
docker network inspect afterresume-net

# Test connectivity from frontend container
docker exec afterresume-frontend curl -s http://backend-api:8000/api/healthz/

# Check backend is running
docker ps | grep backend-api
```

**Fix:**
- Ensure both services use same Docker network (`afterresume-net`)
- Verify `BACKEND_BASE_URL=http://backend-api:8000` in frontend `.env`
- Restart services: `task restart`

#### 2. Jobs Not Executing

**Symptoms:**
- Jobs stuck in `queued` status
- Worker container not running
- No job events

**Diagnosis:**
```bash
# Check worker is running
docker ps | grep worker

# Check worker logs
docker logs afterresume-backend-worker --tail=50

# Check Valkey connectivity
docker exec afterresume-backend-api python -c "import redis; r = redis.from_url('redis://valkey:6379/0'); print(r.ping())"
```

**Fix:**
```bash
# Restart worker
docker compose -f backend/docker-compose.yml restart backend-worker

# Clear stale queue (if needed)
docker exec afterresume-backend-api python manage.py shell
>>> from huey.contrib.djhuey import HUEY
>>> HUEY.storage.flush_queue()
```

#### 3. Database Connection Errors

**Symptoms:**
- `OperationalError: could not connect to server`
- Backend won't start
- Migrations fail

**Diagnosis:**
```bash
# Check Postgres is running
docker ps | grep postgres

# Check logs
docker logs afterresume-postgres --tail=50

# Test connection
docker exec afterresume-postgres psql -U afterresume -d afterresume -c "SELECT 1;"
```

**Fix:**
```bash
# Restart Postgres
docker compose -f backend/docker-compose.yml restart postgres

# If data corrupted, reset (⚠️ destroys data)
docker compose -f backend/docker-compose.yml down -v
task up
task bootstrap
```

#### 4. Static Files Not Loading

**Symptoms:**
- Frontend UI broken/unstyled
- 404 errors for CSS/JS
- White page

**Diagnosis:**
```bash
# Check static files exist
docker exec afterresume-frontend ls -la /app/static/

# Test static file access
curl -I http://localhost:3000/static/css/app.min.css
```

**Fix:**
```bash
# Collect static files
docker exec afterresume-frontend python manage.py collectstatic --noinput

# Verify static files mounted
docker inspect afterresume-frontend | grep -A 10 Mounts
```

#### 5. Stripe Webhook Failures

**Symptoms:**
- Top-ups complete in Stripe but balance not credited
- Webhook events show failures in Stripe dashboard

**Diagnosis:**
```bash
# Check webhook logs
docker logs afterresume-backend-api | grep webhook

# Test webhook endpoint
curl -X POST http://localhost:8000/api/billing/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"type":"test"}'
```

**Fix:**
- Verify `STRIPE_WEBHOOK_SECRET` is set
- Ensure webhook URL is publicly accessible
- Check StripeEvent table for duplicate events
- Review backend logs for errors

#### 6. Sessions Expiring Prematurely

**Symptoms:**
- Users logged out unexpectedly
- "Authentication credentials not provided" errors

**Diagnosis:**
```bash
# Check session settings
docker exec afterresume-frontend python manage.py shell
>>> from django.conf import settings
>>> print(settings.SESSION_COOKIE_AGE)
>>> print(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)
```

**Fix:**
- Adjust `SESSION_COOKIE_AGE` in settings
- Ensure Valkey (session backend) is healthy
- Check for cookie domain/secure flag issues

---

## Backup & Recovery

### Database Backup

**Manual Backup:**
```bash
# Full database dump
docker exec afterresume-postgres pg_dump -U afterresume afterresume > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker exec afterresume-postgres pg_dump -U afterresume afterresume | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Schema only
docker exec afterresume-postgres pg_dump -U afterresume afterresume --schema-only > schema_$(date +%Y%m%d).sql
```

**Automated Backups:**
```bash
# Add to crontab on host
0 2 * * * docker exec afterresume-postgres pg_dump -U afterresume afterresume | gzip > /backups/afterresume_$(date +\%Y\%m\%d_\%H\%M\%S).sql.gz

# Rotate old backups (keep last 30 days)
0 3 * * * find /backups -name "afterresume_*.sql.gz" -mtime +30 -delete
```

### MinIO/Object Storage Backup

**Using MinIO Client (mc):**
```bash
# Install mc
docker exec afterresume-minio mc alias set local http://localhost:9000 minioadmin <password>

# Backup bucket
docker exec afterresume-minio mc mirror local/afterresume-artifacts /backup/minio/
```

**Backup to S3:**
```bash
mc mirror local/afterresume-artifacts s3/your-s3-bucket/afterresume-backups/
```

### Restore Database

```bash
# Stop backend services first
docker compose -f backend/docker-compose.yml stop backend-api backend-worker

# Restore from backup
docker exec -i afterresume-postgres psql -U afterresume afterresume < backup_20251231_120000.sql

# Or from gzipped backup
gunzip -c backup_20251231_120000.sql.gz | docker exec -i afterresume-postgres psql -U afterresume afterresume

# Restart services
docker compose -f backend/docker-compose.yml start backend-api backend-worker
```

### Disaster Recovery Plan

1. **Daily automated database backups** → offsite storage (S3, etc.)
2. **Weekly full system backups** (DB + MinIO + configs)
3. **Monthly backup restoration tests**
4. **Document restore procedures** and test them

**Recovery Time Objective (RTO):** < 4 hours  
**Recovery Point Objective (RPO):** < 24 hours

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Change default admin password
- [ ] Generate strong `SECRET_KEY` (both frontend and backend)
- [ ] Set `DEBUG=0`
- [ ] Configure `ALLOWED_HOSTS` correctly
- [ ] Enable HTTPS/TLS
- [ ] Set `SESSION_COOKIE_SECURE=True` and `CSRF_COOKIE_SECURE=True`
- [ ] Configure real Stripe keys (live mode)
- [ ] Set up Stripe webhook endpoint
- [ ] Configure email provider (SendGrid, AWS SES, etc.)
- [ ] Set up DNS records
- [ ] Configure firewall (only 80/443 public)
- [ ] Set up monitoring and alerts
- [ ] Configure log aggregation
- [ ] Set up error tracking (Sentry)
- [ ] Configure automated backups
- [ ] Test backup restoration
- [ ] Load test system
- [ ] Run security audit
- [ ] Document incident response procedures

### Recommended Production Stack

**Hosting:**
- Dokploy (recommended for MVP)
- AWS ECS/Fargate
- Google Cloud Run
- DigitalOcean App Platform

**Database:**
- Managed Postgres (AWS RDS, GCP Cloud SQL, DO Managed DB)
- Enable automated backups
- Multi-AZ deployment for HA

**Object Storage:**
- AWS S3
- GCP Cloud Storage
- MinIO (self-hosted)

**Cache/Queue:**
- Managed Redis (AWS ElastiCache, Redis Labs)
- Valkey (Redis fork, self-hosted)

**Monitoring:**
- Datadog
- New Relic
- Grafana + Prometheus

**Error Tracking:**
- Sentry
- Rollbar

**Email:**
- SendGrid
- AWS SES
- Postmark

### Environment Variables (Production)

```bash
# CRITICAL: Never commit these to git
SECRET_KEY=<64-char-random-string>
DEBUG=0
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com

# Database (managed service)
POSTGRES_HOST=your-db.region.rds.amazonaws.com
POSTGRES_DB=afterresume_prod
POSTGRES_USER=afterresume
POSTGRES_PASSWORD=<strong-password>

# Stripe (live keys)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<sendgrid-api-key>
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# S3/MinIO
AWS_STORAGE_BUCKET_NAME=afterresume-prod
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
AWS_S3_REGION_NAME=us-east-1

# Redis/Valkey (managed)
REDIS_URL=rediss://:<password>@your-redis.cloud.provider:6380/0

# Session/Cookie Security
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_DOMAIN=.yourdomain.com

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
```

### Scaling Considerations

**Horizontal Scaling:**
- Run multiple backend API containers behind load balancer
- Run multiple frontend containers
- Run multiple worker containers for job processing
- Use managed/clustered database
- Use Redis Sentinel or Redis Cluster for cache/queue

**Vertical Scaling:**
- Increase container resources (CPU/memory)
- Optimize database queries
- Add database read replicas
- Use CDN for static assets

**Performance Tuning:**
- Enable query caching
- Add database indexes
- Use connection pooling (pgbouncer)
- Optimize LLM calls (batching, caching)
- Add rate limiting
- Implement request throttling

---

## API Reference

### Authentication Endpoints

**Get Token:**
```
POST /api/auth/token/
Body: {"username": "user", "password": "pass"}
Returns: {"token": "...", "user": {...}}
```

**Login (session):**
```
POST /api/auth/login/
Body: {"username": "user", "password": "pass", "remember_me": true}
Returns: {"message": "Login successful", "user": {...}}
```

**Logout:**
```
POST /api/auth/logout/
Headers: Authorization: Token <token>
Returns: {"message": "Logout successful"}
```

**Get Current User:**
```
GET /api/me/
Headers: Authorization: Token <token>
Returns: {"id": 1, "username": "user", "profile": {...}}
```

### Billing Endpoints

**Reserve Balance:**
```
GET /api/billing/reserve/balance/
Headers: Authorization: Token <token>
Returns: {"balance_cents": 5000, "balance_dollars": 50.0, ...}
```

**Reserve Ledger:**
```
GET /api/billing/reserve/ledger/?limit=50
Headers: Authorization: Token <token>
Returns: [{"id": 1, "type": "credit", "amount_cents": 5000, ...}, ...]
```

**Create Top-Up Session:**
```
POST /api/billing/topup/session/
Headers: Authorization: Token <token>
Body: {"amount_dollars": 50}
Returns: {"session_id": "cs_test_...", "checkout_url": "https://..."}
```

### Admin Endpoints

**Create Passkey:**
```
POST /api/admin/passkeys/
Headers: Authorization: Token <admin-token>
Body: {"expires_days": 7, "notes": "Invite for user"}
Returns: {"passkey": "...", "expires_at": "..."}
```

**List Users:**
```
GET /api/admin/users/?limit=50
Headers: Authorization: Token <admin-token>
Returns: [{"id": 1, "username": "user", ...}, ...]
```

**Adjust Reserve (Admin):**
```
POST /api/billing/admin/reserve/adjust/
Headers: Authorization: Token <admin-token>
Body: {"tenant_id": 1, "amount_cents": 10000, "reason": "Credit"}
Returns: {"message": "Reserve adjusted", "new_balance_cents": 10000}
```

**Audit Events:**
```
GET /api/admin/audit-events/?user_id=1&limit=50
Headers: Authorization: Token <admin-token>
Returns: [{"id": 1, "event_type": "login", "timestamp": "...", ...}, ...]
```

### System Endpoints (Staff Only)

**System Metrics Summary:**
```
GET /api/system/metrics/summary/?start_date=2025-12-01&end_date=2025-12-31
Headers: Authorization: Token <admin-token>
Returns: {"mrr": 10000, "arr": 120000, "churn_rate": 0.05, ...}
```

**Jobs List:**
```
GET /system/jobs/?status=running&limit=20
Headers: Authorization: Token <admin-token>
Returns: [{"id": "uuid", "name": "worklog_analysis", "status": "running", ...}, ...]
```

---

## Appendix

### Quick Reference Commands

```bash
# Start/Stop
task up / down / restart

# Health Checks
task health

# Logs
task logs
task logs-backend
task logs-frontend
task logs-worker

# Database
task migrate
task makemigrations
task dbshell

# Shell Access
task shell-backend
task bash-backend
task bash-frontend

# Testing
task test-backend

# Status
task status
```

### Support & Documentation

- **System Design**: `backend/SYSTEM_DESIGN.md`
- **Architecture Review**: `backend/ARCHITECTURE_REVIEW.md`
- **AI Agent Spec**: `backend/tool_context.md`
- **Implementation Progress**: `IMPLEMENTATION_PROGRESS.md`
- **Change Log**: `CHANGE_LOG.md`

### Contact

For production issues:
1. Check logs first
2. Review troubleshooting section
3. Check `IMPLEMENTATION_PROGRESS.md` for known limitations
4. Contact system administrator

---

**End of Admin Guide**