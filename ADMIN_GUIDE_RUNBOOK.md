# AfterResume Admin Guide & Runbook

**Version**: 3.0  
**Last Updated**: 2025-12-31 (Session 10+)  
**Status**: Production-Ready (75% Feature Complete)  
**Maintainer**: System Administrator  
**Emergency Contact**: [Configure your on-call details]

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [System Architecture](#system-architecture)
3. [Initial Setup](#initial-setup)
4. [User Management](#user-management)
5. [Authentication & Security](#authentication--security)
6. [Billing & Reserve Management](#billing--reserve-management)
7. [Worklog Management](#worklog-management)
8. [Admin Panel Operations](#admin-panel-operations)
9. [System Monitoring](#system-monitoring)
10. [Troubleshooting](#troubleshooting)
11. [Backup & Recovery](#backup--recovery)
12. [Production Deployment](#production-deployment)
13. [API Reference](#api-reference)
14. [Emergency Procedures](#emergency-procedures)
15. [Operational Metrics](#operational-metrics)

---

## Quick Start

### Prerequisites

**Required:**
- Docker Engine 20.10+ & Docker Compose 2.0+
- At least 4GB RAM available to Docker
- At least 20GB disk space
- Internet connection for pulling images

**Recommended:**
- Task CLI 3.0+ (https://taskfile.dev)
- curl & jq for testing and troubleshooting
- Git 2.30+ for version control
- psql client for database operations
- Basic understanding of Django, Docker, and REST APIs

### First-Time System Start

```bash
# 1. Clone repository (if not already cloned)
git clone <repository-url>
cd afterresume

# 2. Copy environment template and configure
cp .env.example .env

# 3. CRITICAL: Edit .env with production-appropriate settings
#    - Generate strong SECRET_KEY values
#    - Set DEBUG=0 for production
#    - Configure database credentials
#    - Add Stripe keys
#    - Configure email provider
vim .env

# 4. Start all services
task up

# This will start:
#  - frontend (port 3000)
#  - backend-api (port 8000)
#  - postgres (port 5432)
#  - valkey (redis-compatible) for backend queue (port 6379)
#  - valkey-frontend for sessions/cache (port 6380)
#  - minio for object storage (ports 9000-9001)
#  - backend-worker for async job processing

# 5. Wait for all services to be healthy (30-60 seconds)
watch -n 2 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# 6. Run database migrations and bootstrap
task bootstrap

# This will:
#  - Apply all Django migrations
#  - Create default admin user
#  - Create default tenant
#  - Create user profile
#  - Initialize reserve account
#  - Create MinIO buckets

# 7. Verify bootstrap completed successfully
docker logs afterresume-backend-api | grep "Bootstrap complete"
```

### Daily Start (After First Setup)

```bash
# Start all services
task up

# Check health
task health

# View logs (optional)
task logs
```

### Verify System Health

```bash
# 1. Check all services are running and healthy
task status
# Expected: All containers show "Up (healthy)"

# 2. Test backend API health
curl http://localhost:8000/api/healthz/
# Expected: {"status":"ok"}

# 3. Test backend readiness (checks DB, cache, storage)
curl http://localhost:8000/api/readyz/
# Expected: {"status":"ready", "db":"ok", "cache":"ok", "storage":"ok"}

# 4. Test frontend health
curl http://localhost:3000/health/
# Expected: HTTP 200 with HTML page

# 5. Test frontend → backend connectivity (critical)
docker exec afterresume-frontend curl -s http://backend-api:8000/api/healthz/
# Expected: {"status":"ok"}
# If this fails, check Docker network configuration

# 6. Test authentication system
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.token')
echo "Token received: ${TOKEN:0:20}..."
# Expected: Token string (40 characters)

# 7. Test authenticated endpoint
curl -H "Authorization: Token $TOKEN" \
  http://localhost:8000/api/status/bar/ | jq .
# Expected: JSON with reserve_balance, tokens_in, tokens_out, jobs_running
```

### Access Points

| Service | URL | Purpose | Auth Required |
|---------|-----|---------|---------------|
| **Frontend UI** | http://localhost:3000 | Main user interface | Session (login) |
| **Backend API** | http://localhost:8000 | REST API | Token |
| **Django Admin** | http://localhost:8000/django-admin/ | Model management | Session (staff) |
| **API Documentation** | http://localhost:8000/api/docs/ | Auto-generated API docs | Public |
| **MinIO Console** | http://localhost:9001 | Object storage admin | MinIO credentials |
| **Postgres** | localhost:5432 | Database | DB credentials |
| **Valkey (Backend)** | localhost:6379 | Job queue | No auth (internal) |
| **Valkey (Frontend)** | localhost:6380 | Session cache | No auth (internal) |

### Default Credentials

⚠️ **CRITICAL SECURITY WARNING**: These default credentials MUST be changed immediately in production!

**Admin Account:**
- **Username**: `admin`
- **Password**: `admin123`
- **Change Command**: See [Change Admin Password](#change-admin-password)

**MinIO:**
- **Username**: `minioadmin`
- **Password**: `minioadmin`
- **Change**: Update `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` in `.env`

**Database:**
- **User**: `afterresume`
- **Password**: `afterresume`
- **Change**: Update `POSTGRES_PASSWORD` in `.env` before first start

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

## Worklog Management

### Overview

The worklog system allows users to track their daily work activities with rich metadata for resume generation and reporting. As an administrator, you can monitor usage, troubleshoot issues, and assist users.

### User Worklog Operations

**Create Entry (Quick-Add)**:
```bash
# Via API
curl -X POST http://localhost:8000/api/worklogs/ \
  -H "Authorization: Token <user-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-12-31",
    "content": "Completed system architecture review and updated documentation for production deployment procedures.",
    "source": "manual",
    "metadata": {
      "employer": "AfterResume Inc",
      "project": "Core Platform",
      "tags": ["architecture", "documentation", "devops"],
      "work_type": "Technical Writing",
      "outcome": "Completed"
    }
  }'
```

**List Entries**:
```bash
# Get paginated list
curl -H "Authorization: Token <user-token>" \
  "http://localhost:8000/api/worklogs/?limit=20&offset=0"

# Filter by date range
curl -H "Authorization: Token <user-token>" \
  "http://localhost:8000/api/worklogs/?start_date=2025-12-01&end_date=2025-12-31"

# Search by keyword
curl -H "Authorization: Token <user-token>" \
  "http://localhost:8000/api/worklogs/?search=architecture"
```

**Get Entry Detail**:
```bash
curl -H "Authorization: Token <user-token>" \
  "http://localhost:8000/api/worklogs/<worklog-id>/"
```

**Update Entry**:
```bash
curl -X PATCH http://localhost:8000/api/worklogs/<worklog-id>/ \
  -H "Authorization: Token <user-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Updated description with additional details...",
    "metadata": {
      "employer": "AfterResume Inc",
      "project": "Core Platform - Phase 2",
      "tags": ["architecture", "documentation", "devops", "security"]
    }
  }'
```

**Delete Entry**:
```bash
curl -X DELETE http://localhost:8000/api/worklogs/<worklog-id>/ \
  -H "Authorization: Token <user-token>"
```

### Frontend Worklog UI Features

**Quick-Add Modal (<60 seconds)**:
- Pre-filled with today's date
- Smart suggestions from recent entries (last 10)
- Auto-suggests employer/project based on user history
- Metadata stored in JSON field
- HTMX-powered (no page reload)

**Timeline View**:
- Chronological display with cards
- Color-coded by date proximity
- Metadata badges (employer, project, tags)
- Dropdown actions: View Details, Edit, Delete

**Detail/Edit Page**:
- Full entry display with sidebar metadata
- Edit inline
- Attachment list (when evidence feature complete)
- Related entries suggestions

### Admin Worklog Operations

**View All Worklogs (Cross-Tenant)**:
```bash
curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/api/admin/worklogs/?limit=50"
```

**View User's Worklogs**:
```bash
curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/api/admin/worklogs/?user_id=<user-id>&limit=50"
```

**View Tenant's Worklogs**:
```bash
curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/api/admin/worklogs/?tenant_id=<tenant-id>&limit=50"
```

**Worklog Statistics**:
```bash
# Get system-wide stats
curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/api/admin/worklogs/stats/"

# Response:
# {
#   "total_entries": 1234,
#   "total_users_with_entries": 45,
#   "avg_entries_per_user": 27.4,
#   "entries_last_7_days": 156,
#   "entries_last_30_days": 678,
#   "top_employers": [...],
#   "top_projects": [...],
#   "top_tags": [...]
# }
```

### Worklog Data Integrity

**Check for Orphaned Entries**:
```bash
docker exec afterresume-backend-api python manage.py shell <<EOF
from apps.worklog.models import WorkLog
from django.contrib.auth.models import User

# Find worklogs with deleted users
orphaned = WorkLog.objects.filter(user__isnull=True)
print(f"Orphaned worklogs: {orphaned.count()}")

# Find worklogs with no tenant
no_tenant = WorkLog.objects.filter(user__profile__tenant__isnull=True)
print(f"Worklogs with no tenant: {no_tenant.count()}")
EOF
```

**Bulk Operations (Use with Caution)**:
```python
# Django shell
from apps.worklog.models import WorkLog
from django.utils import timezone
from datetime import timedelta

# Delete old test entries
test_entries = WorkLog.objects.filter(
    content__icontains='test',
    created_at__lt=timezone.now() - timedelta(days=30)
)
print(f"Found {test_entries.count()} test entries")
# test_entries.delete()  # Uncomment to execute

# Fix metadata for entries missing structure
worklogs = WorkLog.objects.filter(metadata__isnull=True)
for wl in worklogs:
    wl.metadata = {"tags": [], "source": "manual"}
    wl.save()
```

### Worklog Troubleshooting

**Issue: User can't create entries**
```bash
# 1. Check user has valid token
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"<username>","password":"<password>"}'

# 2. Verify user has profile and tenant
docker exec afterresume-backend-api python manage.py shell <<EOF
from django.contrib.auth.models import User
user = User.objects.get(username='<username>')
print(f"Has profile: {hasattr(user, 'profile')}")
if hasattr(user, 'profile'):
    print(f"Tenant: {user.profile.tenant}")
EOF

# 3. Check API logs for errors
docker logs afterresume-backend-api | grep worklog | tail -20
```

**Issue: Entries not showing in list**
- Verify tenant isolation working (user only sees their tenant's data)
- Check pagination parameters
- Verify date range filters
- Check for JavaScript errors in browser console

---

## Admin Panel Operations

### Overview

The admin panel provides comprehensive management tools for staff users. Access requires `is_staff=True` permission.

**Admin Panel Access**:
- **URL**: http://localhost:3000/admin-panel/
- **Navigation**: Sidebar menu → "Administration" section (visible to staff only)
- **Sections**: 
  - Passkey Management
  - User Management
  - Billing Administration
  - Executive Metrics Dashboard

### Passkey Management UI

**Access**: http://localhost:3000/admin-panel/passkeys/

**Features**:
- List all passkeys with status (Active/Used/Expired)
- Create new passkeys with configurable expiration (1-365 days)
- View usage history (who used it, when, to create which account)
- Search and filter passkeys
- Audit trail display

**Creating a Passkey via UI**:
1. Navigate to Admin Panel → Passkey Management
2. Click "Create New Passkey" button
3. Fill form:
   - **Expiration Days**: 1-365 (default 7)
   - **Notes**: Description (e.g., "Invite for John Doe - john@example.com")
4. Click "Create"
5. ⚠️ **IMPORTANT**: Copy passkey immediately (shown once only)
6. Send passkey to recipient securely
7. Passkey will appear in list with status "Active"

**Passkey States**:
- **Active**: Not yet used, not expired
- **Used**: Successfully consumed during signup (shows user created)
- **Expired**: Past expiration date, cannot be used

**Monitoring Passkey Usage**:
```bash
# Via API
curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/api/admin/passkeys/list/?status=used&limit=50"

# Via database
docker exec afterresume-backend-api python manage.py shell <<EOF
from apps.invitations.models import InvitePasskey
from django.utils import timezone

active = InvitePasskey.objects.filter(
    used_at__isnull=True,
    expires_at__gt=timezone.now()
).count()
print(f"Active passkeys: {active}")

used = InvitePasskey.objects.filter(
    used_at__isnull=False
).count()
print(f"Used passkeys: {used}")

expired = InvitePasskey.objects.filter(
    expires_at__lt=timezone.now(),
    used_at__isnull=True
).count()
print(f"Expired passkeys: {expired}")
EOF
```

### User Management UI

**Access**: http://localhost:3000/admin-panel/users/

**Features**:
- List all users with status indicators
- Search by username/email
- Filter: All | Active | Inactive
- View user details (tenant, creation date, last login)
- Enable/Disable accounts
- Reset passwords (admin-initiated)
- Edit user profiles
- View reserve balance and activity

**User List Columns**:
- **Username** + **Email**
- **Status**: Active/Inactive badge
- **Role**: Superuser/Staff/User badge
- **Tenant**: Organization assignment
- **Created**: Account creation date
- **Last Login**: Recent activity
- **Actions**: Dropdown with Edit, Enable/Disable, Reset Password, View Profile

**Disabling a User Account**:
1. Navigate to Admin Panel → User Management
2. Find user in list (use search if needed)
3. Click Actions dropdown → "Disable Account"
4. Confirm action
5. User's `is_active` flag set to False
6. User cannot log in (existing sessions terminated)
7. Audit event logged

**Resetting User Password (Admin)**:
1. Navigate to Admin Panel → User Management
2. Find user → Actions → "Reset Password"
3. Enter new temporary password
4. Click "Reset Password"
5. Password changed immediately (no email sent)
6. Provide temporary password to user securely
7. Audit event logged

**Editing User Profile/Billing**:
1. Find user → Actions → "Edit User"
2. Modal opens with fields:
   - **Username** (read-only after creation)
   - **Email**
   - **First Name** / **Last Name**
   - **Is Active**
   - **Is Staff**
   - **Tenant** (dropdown)
   - **Stripe Customer ID** (read-only, auto-managed)
   - **Settings** (JSON editor for feature flags)
   - **Notes** (internal admin notes)
3. Make changes
4. Click "Save"
5. Audit event logged

**Assigning User to Different Tenant**:
⚠️ **CAUTION**: This moves ALL user data to new tenant. Irreversible without backup.

1. Edit User (as above)
2. Change "Tenant" dropdown selection
3. Click "Save"
4. Backend moves:
   - User profile
   - Reserve account
   - All worklogs
   - All artifacts
   - All generated reports
5. Audit event logged with before/after tenant IDs

### Billing Administration UI

**Access**: http://localhost:3000/admin-panel/billing/

**Overview Cards**:
- **Total Accounts**: Count of all reserve accounts
- **Total Reserves**: Sum of all balances ($)
- **Low Balance**: Count of accounts below threshold
- **Delinquent**: Count of accounts with negative balance or failed payments

**Account Table**:
- Filterable by date range, sort by spend/balance/activity
- Columns:
  - Username
  - Balance (color-coded: green/yellow/red)
  - Spend (last 30 days)
  - Jobs Run (last 30 days)
  - Status (Active/Low Balance/Delinquent)
  - Last Activity
  - Actions dropdown

**Actions Available**:
- **View Ledger**: Opens modal with transaction history
- **Adjust Balance**: Manual credit/debit (requires reason)
- **View Profile**: Links to user management

**Manual Balance Adjustment**:
1. Find account → Actions → "Adjust Balance"
2. Modal opens:
   - **Amount**: Can be positive (credit) or negative (debit)
   - **Reason**: REQUIRED (e.g., "Promotional credit for early adopter")
3. Click "Adjust"
4. Ledger entry created immediately
5. Audit log entry created with:
   - Admin username
   - Timestamp
   - Amount
   - Reason
   - Balance before/after

**Viewing Transaction Ledger**:
1. Find account → Actions → "View Ledger"
2. Modal shows paginated transaction history:
   - **Date/Time**
   - **Type**: Credit (green) / Debit (red) / Adjustment (blue)
   - **Amount**
   - **Balance After**
   - **Related**: Job ID or Stripe event ID
   - **Notes**: Reason for adjustments
3. Can export to CSV

**CSV Export**:
1. Click "Export CSV" button (top right)
2. Downloads file: `billing_admin_export_<date>.csv`
3. Contains:
   - All visible accounts (respects current filters)
   - Columns: username, email, tenant, balance, spend_30d, jobs_30d, status, last_activity

**Monitoring Reserve Health**:
```bash
# System-wide summary
curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/api/billing/admin/reserve/summary/"

# Response:
# {
#   "total_accounts": 45,
#   "total_balance_cents": 125000,
#   "total_balance_dollars": 1250.0,
#   "low_balance_count": 3,
#   "negative_balance_count": 1,
#   "avg_balance_cents": 2777,
#   "median_balance_cents": 5000
# }
```

### Executive Metrics Dashboard

**Access**: http://localhost:3000/admin-panel/metrics/

**Key Metrics Displayed**:

**Financial Metrics**:
- **MRR** (Monthly Recurring Revenue)
- **ARR** (Annual Recurring Revenue)
- **ARPA** (Average Revenue Per Account)
- **New Customers** (current month)
- **Churn Rate** (customer % + revenue %)
- **NRR** (Net Revenue Retention)
- **GRR** (Gross Revenue Retention)

**User Engagement**:
- **DAU** (Daily Active Users)
- **WAU** (Weekly Active Users)
- **MAU** (Monthly Active Users)
- **Activation Rate**: % of users who uploaded file / created worklog / generated report

**System Health**:
- **API Latency** (P50, P95, P99)
- **Error Rate** (last 24h)
- **Queue Depth** (pending jobs)
- **Worker Health** (active workers)

**AI/LLM Metrics**:
- **Jobs Run** (last 24h / 7d / 30d)
- **Avg Job Duration**
- **Job Failure Rate**
- **Token Usage** (in/out)
- **Estimated Cost** (token cost)

**Operational Metrics**:
- **Active Subscriptions** (Stripe)
- **Past Due** (payment failures)
- **Canceled** (churn)
- **Failed Payments** (last 30d)

**Features**:
- **Auto-Refresh**: Updates every 60 seconds via HTMX
- **Last Updated**: Timestamp display
- **Alerts**: Highlighted warnings for:
  - Churn rate spike (>5% from baseline)
  - High error rate (>1%)
  - Payment failures spike
  - Job queue backup (>100 pending)
- **Filters**: (Frontend ready, backend TODO)
  - Tenant (for multi-org deployments)
  - Date Range (default: last 30 days)
  - Plan/Tier
- **Cohort Retention Table**: Shows week 1/4/12 retention percentages
- **Metric Definitions**: Link to documentation explaining calculations

**Current Status**: ✅ Frontend 100% complete | ⚠️ Backend data aggregation TODO

**Metrics Computation (TODO)**:
The metrics dashboard currently shows placeholder data. To populate with real data:

```bash
# Schedule metrics computation job (add to backend/apps/system/tasks.py)
from huey.contrib.djhuey import db_periodic_task
from datetime import timedelta

@db_periodic_task(crontab(hour='*/1'))  # Run hourly
def compute_metrics_snapshots():
    from apps.system.services import compute_and_store_metrics
    compute_and_store_metrics()
```

Then implement `compute_and_store_metrics()` service to:
1. Aggregate billing data (MRR/ARR from subscription records)
2. Aggregate user activity (DAU/WAU/MAU from login events)
3. Aggregate job data (run counts, durations, failures)
4. Aggregate LLM usage (token counts from UsageEvent)
5. Store in MetricsSnapshot model with timestamp
6. Dashboard fetches latest snapshot

**Manual Metrics Refresh** (for testing):
```python
docker exec afterresume-backend-api python manage.py shell <<EOF
from apps.system.services import compute_and_store_metrics
compute_and_store_metrics()
print("Metrics updated")
EOF
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

---

## Emergency Procedures

### Overview

This section provides step-by-step procedures for handling critical production incidents. All procedures assume you have SSH/terminal access to the production environment and appropriate credentials.

### Severity Levels

- **P0 (Critical)**: System down, data loss risk, security breach
  - Response Time: Immediate
  - Escalation: Page on-call immediately
  
- **P1 (High)**: Major feature broken, significant user impact
  - Response Time: Within 15 minutes
  - Escalation: Notify on-call within 30 minutes
  
- **P2 (Medium)**: Minor feature broken, workaround available
  - Response Time: Within 2 hours
  - Escalation: Create ticket, address in next business day
  
- **P3 (Low)**: Cosmetic issue, no functional impact
  - Response Time: Within 1 week
  - Escalation: Backlog

### P0: Complete System Outage

**Symptoms**:
- Frontend unreachable (HTTP 502/503/504)
- Backend API unreachable
- Database connection failures
- All users affected

**Response Procedure**:

1. **Confirm Outage** (30 seconds):
   ```bash
   # From external network
   curl -I https://yourdomain.com
   curl -I https://api.yourdomain.com/api/healthz/
   
   # Expected: Connection refused or 50x errors
   ```

2. **Check Infrastructure** (1 minute):
   ```bash
   # Check all containers
   docker ps -a --format "table {{.Names}}\t{{.Status}}"
   
   # Check Docker daemon
   sudo systemctl status docker
   
   # Check disk space (common cause)
   df -h
   
   # Check memory
   free -h
   
   # Check system load
   uptime
   ```

3. **Restart Failed Services** (2 minutes):
   ```bash
   # If specific container down
   docker restart afterresume-<service-name>
   
   # If all containers down
   cd /path/to/afterresume
   task restart
   
   # Wait for health checks
   watch -n 2 'docker ps --format "table {{.Names}}\t{{.Status}}"'
   ```

4. **Check Application Logs** (3 minutes):
   ```bash
   # Backend
   docker logs afterresume-backend-api --tail=100
   
   # Frontend
   docker logs afterresume-frontend --tail=100
   
   # Database
   docker logs afterresume-postgres --tail=100
   
   # Look for: OOM kills, disk full, connection errors
   ```

5. **If Restart Fails**:
   ```bash
   # Check for port conflicts
   sudo lsof -i :3000
   sudo lsof -i :8000
   sudo lsof -i :5432
   
   # Check Docker network
   docker network inspect afterresume-net
   
   # Nuclear option: Full restart
   task down
   task up
   task health
   ```

6. **Verify Recovery**:
   ```bash
   task health
   curl http://localhost:8000/api/healthz/
   curl http://localhost:3000/health/
   
   # Test login
   curl -X POST http://localhost:8000/api/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"<password>"}'
   ```

7. **Post-Incident** (After recovery):
   - Review logs for root cause
   - Document in incident report
   - Create tickets for preventive measures
   - Update monitoring/alerting

### P0: Database Corruption or Data Loss

**Symptoms**:
- Postgres container crashes repeatedly
- "relation does not exist" errors
- Data inconsistency reports from users

**Response Procedure**:

1. **Stop Writing Immediately**:
   ```bash
   # Stop all services that write to DB
   docker stop afterresume-backend-api
   docker stop afterresume-backend-worker
   docker stop afterresume-frontend
   ```

2. **Assess Damage**:
   ```bash
   # Connect to database
   docker exec -it afterresume-postgres psql -U afterresume -d afterresume
   
   # Check tables exist
   \dt
   
   # Check row counts
   SELECT 'users' AS table, COUNT(*) FROM auth_user
   UNION ALL
   SELECT 'worklogs', COUNT(*) FROM worklog_worklog
   UNION ALL
   SELECT 'tenants', COUNT(*) FROM tenants_tenant;
   
   # Check for corruption
   SELECT pg_database.datname, pg_database_size(pg_database.datname)
   FROM pg_database;
   ```

3. **If Corruption Detected**:
   ```bash
   # Attempt DB recovery
   docker exec afterresume-postgres pg_resetwal -f /var/lib/postgresql/data
   
   # Or restore from most recent backup
   # (See Backup & Recovery section)
   ```

4. **Restore from Backup** (if corruption severe):
   ```bash
   # Stop database
   docker stop afterresume-postgres
   
   # Restore from backup file
   gunzip -c /backups/afterresume_<date>.sql.gz | \
     docker exec -i afterresume-postgres psql -U afterresume afterresume
   
   # Restart services
   task restart
   ```

5. **Verify Data Integrity**:
   ```python
   docker exec afterresume-backend-api python manage.py shell <<EOF
   from django.contrib.auth.models import User
   from apps.worklog.models import WorkLog
   from apps.tenants.models import Tenant
   
   print(f"Users: {User.objects.count()}")
   print(f"Tenants: {Tenant.objects.count()}")
   print(f"Worklogs: {WorkLog.objects.count()}")
   
   # Check referential integrity
   orphaned_worklogs = WorkLog.objects.filter(user__isnull=True).count()
   print(f"Orphaned worklogs: {orphaned_worklogs}")
   EOF
   ```

### P0: Security Breach Detected

**Symptoms**:
- Unauthorized admin access
- Unexpected data modifications
- Suspicious API requests in logs
- Alert from security monitoring tool

**Response Procedure**:

1. **Contain Immediately** (30 seconds):
   ```bash
   # Block external access (if using nginx)
   sudo systemctl stop nginx
   
   # Or stop frontend (breaks UI but protects data)
   docker stop afterresume-frontend
   ```

2. **Revoke All API Tokens**:
   ```python
   docker exec afterresume-backend-api python manage.py shell <<EOF
   from rest_framework.authtoken.models import Token
   Token.objects.all().delete()
   print("All API tokens revoked")
   EOF
   ```

3. **Reset Admin Password**:
   ```python
   docker exec afterresume-backend-api python manage.py shell <<EOF
   from django.contrib.auth.models import User
   admin = User.objects.get(username='admin')
   admin.set_password('<strong-new-password>')
   admin.save()
   print("Admin password reset")
   EOF
   ```

4. **Audit Log Analysis**:
   ```python
   docker exec afterresume-backend-api python manage.py shell <<EOF
   from apps.auditing.models import AuthEvent
   from django.utils import timezone
   from datetime import timedelta
   
   # Recent auth events
   recent = AuthEvent.objects.filter(
       timestamp__gte=timezone.now() - timedelta(hours=24)
   ).order_by('-timestamp')
   
   for event in recent[:50]:
       print(f"{event.timestamp} | {event.event_type} | {event.user} | {event.ip_address}")
   EOF
   ```

5. **Check for Backdoors**:
   ```bash
   # Check for unauthorized users
   docker exec afterresume-backend-api python manage.py shell <<EOF
   from django.contrib.auth.models import User
   suspicious = User.objects.filter(is_superuser=True)
   for user in suspicious:
       print(f"{user.username} | Created: {user.date_joined} | Last login: {user.last_login}")
   EOF
   
   # Check for modified code
   git status
   git diff
   ```

6. **Restore Service** (only after confirmed safe):
   ```bash
   # Restart with new credentials
   sudo systemctl start nginx
   docker start afterresume-frontend
   
   # Force all users to re-login
   docker exec afterresume-frontend python manage.py shell <<EOF
   from django.contrib.sessions.models import Session
   Session.objects.all().delete()
   EOF
   ```

7. **Post-Incident**:
   - Full security audit
   - Review access logs
   - Update all credentials
   - Enable 2FA for admin accounts
   - Review firewall rules
   - Document attack vector
   - Notify affected users (if data exposed)

### P1: Backend API Unresponsive (Workers Failing)

**Symptoms**:
- Jobs stuck in "queued" status
- Worker container crashed or not processing
- Queue depth growing
- "Task timeout" errors

**Response Procedure**:

1. **Check Worker Status**:
   ```bash
   docker ps | grep worker
   docker logs afterresume-backend-worker --tail=100
   ```

2. **Check Queue Health**:
   ```bash
   # Connect to Valkey
   docker exec -it afterresume-valkey redis-cli
   
   # Check queue depth
   LLEN huey.queue
   
   # Check for stuck tasks
   LRANGE huey.queue 0 10
   ```

3. **Restart Worker**:
   ```bash
   docker restart afterresume-backend-worker
   
   # Monitor logs
   docker logs -f afterresume-backend-worker
   ```

4. **If Queue Backed Up** (>1000 tasks):
   ```bash
   # Drain queue (CAREFUL: loses pending jobs)
   docker exec afterresume-valkey redis-cli FLUSHDB
   
   # Or selectively clear old tasks (safer)
   docker exec afterresume-backend-api python manage.py shell <<EOF
   from huey.contrib.djhuey import HUEY
   # Implement selective queue cleanup
   EOF
   ```

5. **Scale Workers** (if load too high):
   ```bash
   # Start additional worker container
   docker compose -f backend/docker-compose.yml up -d --scale backend-worker=3
   ```

### P1: Stripe Webhook Failures

**Symptoms**:
- Payments complete but balance not credited
- Webhook events showing failures in Stripe dashboard
- Users report top-up not working

**Response Procedure**:

1. **Check Webhook Logs**:
   ```bash
   docker logs afterresume-backend-api | grep webhook | tail -50
   ```

2. **Test Webhook Endpoint**:
   ```bash
   curl -X POST http://localhost:8000/api/billing/webhook/ \
     -H "Content-Type: application/json" \
     -d '{"type":"checkout.session.completed","id":"evt_test"}'
   ```

3. **Verify Webhook Secret**:
   ```bash
   docker exec afterresume-backend-api python manage.py shell <<EOF
   import os
   print(f"STRIPE_WEBHOOK_SECRET set: {bool(os.environ.get('STRIPE_WEBHOOK_SECRET'))}")
   EOF
   ```

4. **Manually Process Failed Webhook**:
   ```python
   docker exec afterresume-backend-api python manage.py shell <<EOF
   from apps.billing.services import process_checkout_completed
   
   # Get session ID from Stripe dashboard
   session_id = "cs_test_..."
   
   # Manually process
   try:
       process_checkout_completed(session_id)
       print("Webhook processed successfully")
   except Exception as e:
       print(f"Error: {e}")
   EOF
   ```

5. **Retry Failed Webhooks** (from Stripe dashboard):
   - Go to Stripe Dashboard → Webhooks
   - Find failed events
   - Click "Resend" for each failed event

### Quick Reference: Common Fix Commands

```bash
# Restart everything
task restart

# Clear Redis cache
docker exec afterresume-valkey redis-cli FLUSHALL

# Clear frontend sessions
docker exec afterresume-frontend python manage.py shell -c "from django.contrib.sessions.models import Session; Session.objects.all().delete()"

# Run migrations
task migrate

# Rebuild containers (after code changes)
task down && docker compose -f frontend/docker-compose.yml build && docker compose -f backend/docker-compose.yml build && task up

# Reset database (DESTROYS ALL DATA)
docker stop afterresume-backend-api afterresume-backend-worker
docker exec afterresume-postgres psql -U postgres -c "DROP DATABASE afterresume;"
docker exec afterresume-postgres psql -U postgres -c "CREATE DATABASE afterresume OWNER afterresume;"
task migrate
task bootstrap

# Check disk space
df -h

# Check memory
docker stats --no-stream

# Export all data (emergency backup)
docker exec afterresume-postgres pg_dump -U afterresume afterresume | gzip > emergency_backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

---

## Operational Metrics

### Performance Baselines

Establish baselines for your environment. These are example targets for a standard deployment:

**Response Times** (P95):
- Frontend page load: < 500ms
- Backend API calls: < 200ms
- Database queries: < 50ms
- Job execution: Varies by type

**Resource Usage** (Normal Load):
- Backend API CPU: < 50%
- Backend API Memory: < 1GB
- Worker CPU: < 80% (spikes during jobs normal)
- Worker Memory: < 2GB
- Postgres CPU: < 30%
- Postgres Memory: < 2GB
- Disk I/O: < 50 MB/s

**Availability Targets**:
- System uptime: 99.9% (8.76 hours downtime/year)
- API availability: 99.95%
- Database availability: 99.99%

### Key Performance Indicators (KPIs)

**System Health**:
- API error rate: < 0.1%
- Job failure rate: < 2%
- Database connection pool utilization: < 80%
- Queue depth: < 100 pending jobs
- Average queue wait time: < 30 seconds

**User Engagement**:
- Daily active users (DAU): Track trend
- Weekly active users (WAU): Track trend
- Average worklogs per user per week: Track trend
- Report generation success rate: > 95%

**Business Metrics**:
- Monthly Recurring Revenue (MRR): Track growth
- Customer churn rate: < 5% monthly
- Average Revenue Per Account (ARPA): Track trend
- Customer Acquisition Cost (CAC): Monitor vs LTV
- Net Revenue Retention (NRR): Target > 100%

### Monitoring Checklist (Daily)

```bash
# 1. System health
task health

# 2. Check for errors
docker logs afterresume-backend-api --since 24h | grep ERROR | wc -l

# 3. Check job processing
docker exec afterresume-backend-api python manage.py shell <<EOF
from apps.jobs.models import Job
from django.utils import timezone
from datetime import timedelta

running = Job.objects.filter(status='running').count()
failed_24h = Job.objects.filter(
    status='failed',
    updated_at__gte=timezone.now() - timedelta(hours=24)
).count()

print(f"Running jobs: {running}")
print(f"Failed jobs (24h): {failed_24h}")
EOF

# 4. Check queue depth
docker exec afterresume-valkey redis-cli LLEN huey.queue

# 5. Check disk space
df -h | grep -E '(Filesystem|docker|afterresume)'

# 6. Check database size
docker exec afterresume-postgres psql -U afterresume -d afterresume -c "SELECT pg_size_pretty(pg_database_size('afterresume'));"

# 7. Recent auth failures
docker exec afterresume-backend-api python manage.py shell <<EOF
from apps.auditing.models import AuthEvent
from django.utils import timezone
from datetime import timedelta

failed = AuthEvent.objects.filter(
    event_type='login_failed',
    timestamp__gte=timezone.now() - timedelta(hours=24)
).count()

print(f"Failed logins (24h): {failed}")
EOF
```

### Monitoring Checklist (Weekly)

```bash
# 1. Review backup status
ls -lh /backups/*.sql.gz | tail -7

# 2. Test backup restoration (on dev/staging)
# (See Backup & Recovery section)

# 3. Review slow queries
docker logs afterresume-backend-api --since 168h | grep "Slow query" | tail -20

# 4. Check for security updates
docker images | grep afterresume
# Compare with latest base image versions

# 5. Review audit logs
docker exec afterresume-backend-api python manage.py shell <<EOF
from apps.auditing.models import AuthEvent
from django.utils import timezone
from datetime import timedelta

admin_actions = AuthEvent.objects.filter(
    event_type__in=['user_created', 'user_disabled', 'password_reset'],
    timestamp__gte=timezone.now() - timedelta(days=7)
).count()

print(f"Admin actions (7d): {admin_actions}")
EOF

# 6. Review billing health
curl -H "Authorization: Token <admin-token>" \
  "http://localhost:8000/api/billing/admin/reserve/summary/" | jq .

# 7. Review user growth
docker exec afterresume-backend-api python manage.py shell <<EOF
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

new_users_7d = User.objects.filter(
    date_joined__gte=timezone.now() - timedelta(days=7)
).count()

print(f"New users (7d): {new_users_7d}")
EOF
```

### Capacity Planning

**When to Scale**:
- CPU > 70% sustained for 1 hour
- Memory > 80% sustained
- Disk > 85% full
- API response time > 500ms P95
- Queue depth > 500 for > 15 minutes

**Scaling Options**:

1. **Horizontal (Add more containers)**:
   ```bash
   # Add more API containers
   docker compose -f backend/docker-compose.yml up -d --scale backend-api=3
   
   # Add more workers
   docker compose -f backend/docker-compose.yml up -d --scale backend-worker=3
   ```

2. **Vertical (Increase resources)**:
   ```bash
   # Edit docker-compose.yml
   services:
     backend-api:
       deploy:
         resources:
           limits:
             cpus: '2.0'
             memory: 4G
   
   # Restart to apply
   task restart
   ```

3. **Database**:
   - Add read replicas
   - Enable connection pooling (pgbouncer)
   - Optimize queries with indexes
   - Archive old data

4. **Storage**:
   - Upgrade MinIO instance size
   - Enable object lifecycle policies
   - Move to S3 if MinIO hitting limits

---

## Change Management

### Making Configuration Changes

Always follow this process:

1. **Document Change**:
   - What: Describe the change
   - Why: Business justification
   - Risk: Potential impact
   - Rollback: How to undo

2. **Test in Staging** (if available):
   ```bash
   # Apply to staging first
   ssh staging-server
   cd /path/to/afterresume
   # Make changes
   task restart
   # Verify
   task health
   ```

3. **Create Backup**:
   ```bash
   # Database backup
   docker exec afterresume-postgres pg_dump -U afterresume afterresume | \
     gzip > backup_before_change_$(date +%Y%m%d_%H%M%S).sql.gz
   
   # Config backup
   cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
   ```

4. **Apply Change**:
   ```bash
   # Edit configuration
   vim .env
   
   # Or update code
   git pull origin main
   
   # Rebuild if needed
   docker compose -f backend/docker-compose.yml build
   ```

5. **Deploy**:
   ```bash
   task restart
   
   # Monitor logs during restart
   task logs
   ```

6. **Verify**:
   ```bash
   task health
   # Run smoke tests
   # Check key functionality
   ```

7. **Document Result**:
   - Update CHANGE_LOG.md
   - Note any issues encountered
   - Update runbook if new procedures learned

### Rollback Procedure

If change causes issues:

```bash
# 1. Revert code
git reset --hard <previous-commit-hash>

# 2. Revert config
cp .env.backup.<timestamp> .env

# 3. Rebuild
docker compose -f backend/docker-compose.yml build

# 4. Restart
task restart

# 5. Verify
task health

# 6. If database schema changed
gunzip -c backup_before_change_<timestamp>.sql.gz | \
  docker exec -i afterresume-postgres psql -U afterresume afterresume
```

---

### Support & Documentation

- **System Design**: `backend/SYSTEM_DESIGN.md`
- **Architecture Review**: `backend/ARCHITECTURE_REVIEW.md`
- **AI Agent Spec**: `backend/tool_context.md`
- **Implementation Progress**: `IMPLEMENTATION_PROGRESS.md`
- **Change Log**: `CHANGE_LOG.md`

### Contact & Escalation

**For Production Issues**:
1. Check logs first
2. Review this troubleshooting section
3. Check `IMPLEMENTATION_PROGRESS.md` for known limitations
4. Follow emergency procedures above
5. Contact system administrator

**On-Call Escalation Path**:
1. Primary: [Configure] - Response: Immediate (P0), 15min (P1)
2. Secondary: [Configure] - Response: If primary unavailable
3. Engineering Lead: [Configure] - Response: P0 only, or if on-call unavailable

**External Dependencies**:
- **Stripe Support**: https://support.stripe.com (for payment issues)
- **SendGrid Support**: https://support.sendgrid.com (for email delivery)
- **AWS Support**: [If using AWS services]
- **Hosting Provider**: [Dokploy, DigitalOcean, etc.]

---

**Document Version**: 3.0  
**Last Updated**: 2025-12-31  
**Next Review**: 2026-01-31  
**Maintained By**: DevOps Team  

**End of Admin Guide**