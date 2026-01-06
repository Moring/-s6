# AfterResume Architecture

## Overview
AfterResume is a multi-tenant SaaS platform for managing work logs, skills tracking, and automated resume/report generation using AI workflows.

## Service Architecture

### Service Boundaries
- **Frontend**: Vue SPA served by Caddy in production, with a Node proxy sidecar for `/api/*` (service-token injection)
- **Backend**: Django + DRF orchestration service (AI workflows, persistence, storage, jobs, observability)
- **Manager**: Dokploy (deployment control plane)

Frontend never directly accesses Postgres, MinIO, Valkey, or workers. All persistence and authorization are owned by the backend.
The frontend is a client-only SPA (no server-rendered HTML) and communicates with the backend exclusively over HTTP APIs.

## Layering Rules

### Backend Applications (19 apps)
- **api/**: DRF boundary - thin controllers only (validate → call services/dispatch job → return)
- **Domain apps** (`worklog/`, `skills/`, `reporting/`): Models + deterministic business logic only. No LLM calls, no queue calls, no orchestration logic
- **jobs/**: Persistent execution intent + status + schedules + retry/idempotency policy
- **workers/**: Huey integration and job execution entrypoints
- **orchestration/**: Workflow composition (job → steps → agents → persistence)
- **agents/**: AI logic only; no HTTP; no direct DB writes; operate through context
- **llm/**: Provider abstraction; cost/usage accounting hooks
- **observability/**: Structured event timeline + trace context for every job/LLM call
- **system/**: Operator dashboard (read-only aggregates of jobs/events/schedules/health)
- **tenants/**: Multi-tenancy model, roles, permissions, quotas
- **accounts/**: User profiles and authentication
- **invitations/**: Invite-only signup via single-use passkeys
- **auditing/**: Authentication and authorization event logs
- **artifacts/**: File storage abstraction over MinIO
- **billing/**: Reserve-based billing and Stripe integration
- **storage/**: MinIO client and bucket management
- **gamification/**: User engagement system (streaks, XP, badges, challenges)

## Multi-Tenancy

### Tenant Model
- One tenant per user (1:1 mapping for MVP)
- Supports multi-user via TenantMembership model with roles
- Everything user-facing is tenant-scoped
- Tenant resolution derived from authenticated user/session, not request payload

### Role-Based Access Control
Roles: **owner**, **admin**, **member**, **read_only**

Permissions enforced across:
- UI views
- API endpoints
- Job execution
- Share links

## Security & Access Control

### Service-to-Service Authentication
- Frontend → Backend calls require signed internal token (`X-Service-Token` header)
- Token format: `timestamp:hmac_signature`
- Tokens expire after 5 minutes
- Validation rejects expired, malformed, or invalid signatures
- Public endpoints excluded: `/api/auth/`, `/api/healthz`, `/api/share/`

### Web Hardening
Security headers applied to all responses:
- **Content-Security-Policy**: Strict CSP with self-only defaults
- **Strict-Transport-Security**: HTTPS-only in production (HSTS with preload)
- **X-Frame-Options**: DENY
- **X-Content-Type-Options**: nosniff
- **X-XSS-Protection**: 1; mode=block
- **Referrer-Policy**: strict-origin-when-cross-origin
- **Permissions-Policy**: Denies geolocation, camera, microphone, etc.

### Token & Session Security
- Backend issues short-lived JWT access tokens to the SPA and stores refresh tokens in HttpOnly cookies
- SPA sends `Authorization: Bearer <access>` on API calls and refreshes via `/api/auth/token/refresh/`
- Session cookies remain for Django admin and staff-only server routes
- HttpOnly cookies, Secure in production, SameSite: Lax
- CSRF protection applies to session-authenticated endpoints

### SPA CORS/CSRF Considerations
- Prefer serving the SPA and API on the same origin via the frontend proxy
- If cross-origin, configure `CSRF_TRUSTED_ORIGINS` (backend) and CORS allowlists

### Optional Admin Controls
- IP allowlist for admin endpoints (`ADMIN_IP_ALLOWLIST` env var)
- MFA support (Human TODO: configure MFA provider)

## Configuration Management

### Environment Variables
All configuration via environment variables. See `.env.example` for reference.

**Required:**
- `SECRET_KEY`: Django secret for cryptographic signing

**Core Services:**
- `DATABASE_URL` or `POSTGRES_*` variables
- `REDIS_URL`: Valkey/Redis for caching and Huey queue
- `MINIO_*`: Object storage configuration

**Security:**
- `SERVICE_TO_SERVICE_SECRET`: Shared secret for frontend↔backend auth (falls back to SECRET_KEY)
- `CSRF_TRUSTED_ORIGINS`: Comma-separated trusted origins for CSRF
- `ADMIN_IP_ALLOWLIST`: Comma-separated IPs allowed for admin access

**Feature Flags:**
- `MAINTENANCE_MODE`: Enable maintenance mode (True/False)
- `DISABLE_SHARING`: Disable share link creation (True/False)
- `SKIP_SERVICE_AUTH`: Skip service auth in dev (True/False)

**LLM Provider:**
- `LLM_PROVIDER`: `local` (fake) or `vllm`
- `LLM_VLLM_ENDPOINT`: vLLM endpoint (required if provider=vllm)
- `LLM_MODEL_NAME`: Model name

**Email (optional):**
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`

**Stripe (optional):**
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`

### Startup Validation
Environment validation runs on Django startup:
```bash
python manage.py validate_env
python manage.py validate_env --print-status
```

Fails fast with actionable errors if required variables missing.

## Observability & Tracing

### Correlation IDs
Every request receives a correlation ID (from `X-Correlation-ID` header or generated):
- Propagated to all logs
- Added to response headers
- Flows through jobs, workers, agents, and DAG runs
- Format: UUID v4

### Structured Logging
All logs include:
- Timestamp
- Log level
- Module name
- **Correlation ID**
- Message

### Event Timeline
`observability.models.Event` captures:
- Job lifecycle events (start/end/error)
- LLM calls (model, latency, tokens, errors)
- System events
- Linked to jobs and correlation IDs

## Asynchronous Execution

### Job System
All AI work runs as jobs:
- **Queued** → **Running** → **Success/Failed**
- Persistent state in Postgres
- Retry logic with exponential backoff (3 attempts)
- Huey consumer processes jobs asynchronously

### Workflows
6 registered workflows:
1. `worklog.analyze` - Analyze worklog content
2. `skills.extract` - Extract skills from worklogs
3. `report.generate` - Generate status/standup reports
4. `resume.refresh` - Generate resume from all data
5. `system.compute_metrics` - Compute platform metrics
6. `gamification.reward_evaluate` - Evaluate rewards on worklog changes

### DAG Execution Flow
```
API Request → Dispatcher → Job (queued)
    ↓
Worker (Huey) → Workflow → Agent → LLM
    ↓
Result → Persistence → Events → Job (success)
```

## Data Model

### Core Models
- **Tenant**: Organization/workspace
- **TenantMembership**: User-to-tenant relationship with role
- **UserProfile**: Extended user metadata
- **WorkLog**: Daily work entries
- **Skill**: Extracted skills with evidence
- **Report**: Generated reports/resumes
- **Job**: Async execution intent and status
- **Event**: Observability event timeline
- **InvitePasskey**: Single-use invite codes
- **AuthEvent**: Authentication/authorization audit log
- **Gamification Models**: User engagement tracking
  - **UserStreak**: Daily streak with freeze support
  - **UserXP**: Total XP, level, daily XP tracking
  - **XPEvent**: Immutable ledger of XP grants
  - **BadgeDefinition/UserBadge**: Achievement system
  - **ChallengeTemplate/UserChallenge**: Weekly challenges
  - **RewardConfig**: Versioned reward rules
  - **GamificationSettings**: User preferences (quiet mode)

### Storage
- **Postgres**: All structured data
- **MinIO**: Artifact storage (documents, generated files)
- **Valkey/Redis**: Caching and job queue

## Gamification System

### Overview
"Duolingo-style" engagement system to encourage consistent logging, higher-quality entries, and evidence attachment. All reward logic runs asynchronously via DAG workflows with full audit logging and idempotency.

### Core Features

**Streaks**
- Daily streak tracking (>= 1 meaningful entry/day)
- Streak freeze system (3 uses) to preserve streaks
- Anti-gaming rules: minimum content, rate limiting, duplicate detection
- Shows current and longest streak on dashboard

**XP (Experience Points)**
- Quality-weighted scoring:
  - Base entry: 10 XP
  - Per attachment: 5 XP (capped)
  - Per tag: 3 XP (capped)
  - Length bonus: 10 XP (200+ chars)
  - Outcome/impact bonus: 15 XP
- Daily XP cap: 200 XP (prevents grinding)
- Levels increase with total XP (100 XP/level)

**Badges & Achievements**
- Milestone badges: first entry, 7/30/100-day streaks, 10/50/100 entries
- Quality badges: first attachment, first outcome
- Level badges: Level 5, 10
- Idempotent awarding (no duplicates on retries)

**Weekly Challenges**
- Active challenges with progress tracking
- Goal types: log X days, attach evidence Y times, write outcomes Z times
- XP rewards on completion
- Resets weekly (Monday)

**Privacy & Control**
- Quiet mode: user can hide gamification UI
- Tenant-scoped with strict isolation
- Admin can manually grant/revoke awards

### Reward Evaluation DAG

**Workflow**: `gamification.reward_evaluate`

**Trigger**: Automatically on worklog entry create/update and attachment upload

**Steps**:
1. Validate entry meaningfulness (content length, rate limits, duplicates)
2. Compute quality-weighted XP with daily caps
3. Update streak (with freeze logic if applicable)
4. Award relevant badges (idempotent check)
5. Update weekly challenge progress
6. Persist all events to ledger with provenance

**Tools**:
- `is_meaningful_entry()` - Validates quality, prevents spam
- `compute_xp()` - Calculates XP from entry attributes
- `update_streak()` - Increments streak with freeze handling
- `award_badges()` - Idempotent badge granting
- `update_challenges()` - Weekly progress tracking
- `persist_events()` - Ledger persistence with audit trail

### Configuration

**Reward Rules** (RewardConfig model, editable via Django admin):
- `min_entry_length`: 20 characters
- `max_entries_per_hour`: 10
- `max_daily_xp`: 200 XP
- XP multipliers for quality signals
- `max_freezes`: 3

**Initial Data**:
- 10 badge definitions (loaded via migration)
- 3 challenge templates (weekly)
- Default reward config (version 1)

### API Endpoints

**User Endpoints**:
- `GET /api/gamification/summary/` - Streak, XP, level, daily progress, active challenges
- `GET /api/gamification/badges/` - Earned and available badges
- `GET /api/gamification/challenges/` - Active and history
- `PATCH /api/gamification/settings/` - Toggle quiet mode

**Admin Endpoints**:
- `GET /api/admin/gamification/metrics/` - Engagement metrics
- `POST /api/admin/gamification/grant/` - Manual XP grant
- `POST /api/admin/gamification/revoke/` - Manual badge revoke

### Frontend Integration

**Dashboard Widget** (`/`)
- Current and longest streak
- Daily XP progress bar
- Level display
- Active challenges preview
- Respects quiet mode

**Achievements Page** (`/gamification/achievements/`)
- Badge collection (earned + locked)
- Stats cards (streak, level, total badges)
- Category grouping

**Challenges Page** (`/gamification/challenges/`)
- Active challenges with progress bars
- Days remaining
- Challenge history table

## Health & Readiness

### Health Checks
- **Frontend**: `GET /healthz/` - Basic health
- **Backend**: `GET /api/healthz/` - Returns `{"status": "ok"}`

### System Dashboard
Admin view at `/admin/` provides:
- Job statistics
- Failed job visibility
- Event timeline
- System metrics

## Production Deployment

### Required Steps
1. Set all required environment variables
2. Run migrations: `python manage.py migrate`
3. Create superuser: `python manage.py createsuperuser`
4. Collect static files: `python manage.py collectstatic`
5. Start services: `docker compose up -d`
6. Validate health: `curl http://localhost:8000/api/healthz/`

### Infrastructure Dependencies
- PostgreSQL 16+
- Valkey/Redis (for caching and queue)
- MinIO (for object storage)
- Optional: vLLM server for AI workflows
- Optional: SMTP server for email notifications
- Optional: Stripe account for billing

## Constraints & Boundaries

### Non-Negotiable Rules
1. Do not change service split (frontend/backend separation)
2. Do not introduce new top-level services
3. Do not restructure canonical backend layout
4. Frontend never accesses Postgres/MinIO directly
5. All AI work runs as async jobs
6. Multi-tenancy is mandatory for all user data
7. Observability events required for all jobs/LLM calls

### Adding New Features
When adding features:
- Domain logic goes in domain apps
- API endpoints go in `api/`
- Async work goes through `jobs/` + `orchestration/`
- AI logic goes in `agents/`
- Track everything in `observability/`
- Respect tenant scoping
- Add tests and update docs

## Testing

### Test Suite
Run tests:
```bash
pytest
pytest tests/test_system_capabilities.py -v
```

Current coverage:
- Tenant roles and permissions
- Service-to-service authentication
- Rate limiting
- Feature flags
- Quotas and concurrency
- Security middleware

### Test Categories
- **Unit tests**: Domain logic, permissions, helpers
- **Integration tests**: API endpoints, workflows, jobs
- **System tests**: Security, rate limiting, quotas

## References
- See `CC.md` for alignment boilerplate and constraints
- See `ADMIN_GUIDE.md` for operational procedures
- See `CHANGE_LOG.md` for change history
- See `tool_context.md` for DAG specifications
