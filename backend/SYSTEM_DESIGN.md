# AfterResume Backend — System Design

**Version**: 0.1.0  
**Last Updated**: 2025-12-31  
**Status**: MVP Implementation Complete

---

## Table of Contents

1. [Purpose & Scope](#purpose--scope)
2. [System Topology](#system-topology)
3. [Core Architecture](#core-architecture)
4. [Execution Model](#execution-model)
5. [Observability Model](#observability-model)
6. [API Surfaces](#api-surfaces)
7. [Job Types & Workflow Mapping](#job-types--workflow-mapping)
8. [Conventions](#conventions)
9. [Extension Guide](#extension-guide)
10. [MVP vs Future Roadmap](#mvp-vs-future-roadmap)
11. [Testing Approach](#testing-approach)
12. [Operational Notes](#operational-notes)

---

## Purpose & Scope

### Mission

AfterResume is an AI-powered work tracking and resume generation system that helps users:
- Track daily work activities
- Extract and normalize technical skills automatically
- Generate professional reports (status, standup, resume)
- Maintain an always-up-to-date professional profile

### Scope

This backend provides:
- **RESTful API** for frontend interaction
- **Async job execution** via Huey task queue
- **AI agent orchestration** with LLM integration
- **Observability** with event timeline and structured logging
- **System dashboard** for operational monitoring

### Non-Goals (MVP)

- Real-time collaboration
- Advanced authentication/authorization (basic Django auth only)
- Multi-tenancy (single deployment per organization)
- Mobile-specific optimizations
- Production-ready LLM fine-tuning

---

## System Topology

```
┌─────────────┐
│   Frontend  │
│  (Separate) │
└──────┬──────┘
       │ HTTP/REST
       ▼
┌─────────────────────────────────────────────┐
│          AfterResume Backend                │
│  ┌────────────┐        ┌─────────────────┐ │
│  │ Django API │◄──────►│  Orchestration  │ │
│  │  /api/*    │        │   Workflows     │ │
│  └────────────┘        └────────┬────────┘ │
│                                 │          │
│  ┌────────────┐        ┌────────▼────────┐ │
│  │  System    │        │   AI Agents     │ │
│  │ Dashboard  │        │  (worklog, skill│ │
│  │ /system/*  │        │   report, resume│ │
│  └────────────┘        └────────┬────────┘ │
│                                 │          │
│  ┌────────────┐        ┌────────▼────────┐ │
│  │   Huey     │◄──────►│   LLM Client    │ │
│  │  Workers   │        │  (local/vLLM)   │ │
│  └────────────┘        └─────────────────┘ │
│         │                                   │
│         ▼                                   │
│  ┌────────────┐        ┌─────────────────┐ │
│  │  Postgres  │        │  Observability  │ │
│  │  (SQLite   │        │  Event Timeline │ │
│  │   for dev) │        └─────────────────┘ │
│  └────────────┘                            │
└─────────────────────────────────────────────┘
       │                │
       ▼                ▼
  ┌────────┐      ┌──────────┐
  │  Redis │      │  MinIO   │
  │ (Queue)│      │(Storage) │
  └────────┘      └──────────┘
```

### Components

- **Frontend**: Separate React/Vue app communicating via REST API
- **Django API**: Public-facing REST endpoints for CRUD operations
- **System Dashboard**: Internal monitoring API (staff-only)
- **Orchestration**: Workflow coordination layer
- **AI Agents**: Specialized agents for analysis tasks
- **Huey Workers**: Async job execution engine
- **LLM Client**: Abstraction over LLM providers
- **Observability**: Event logging and metrics
- **Postgres**: Primary data store (SQLite for dev)
- **Redis**: Task queue backend
- **MinIO**: Object storage for attachments (stub in MVP)

---

## Core Architecture

### Layered Design

```
┌─────────────────────────────────────────┐
│  Presentation Layer (DRF Views)         │
│  - REST endpoints                       │
│  - Serialization                        │
│  - Permission checks                    │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  Service Layer                          │
│  - Business logic                       │
│  - Transaction management               │
│  - Job enqueuing                        │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  Domain Layer                           │
│  - Models (worklog, skills, reporting)  │
│  - Selectors (queries)                  │
│  - Services (write operations)          │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  Infrastructure Layer                   │
│  - Job system (dispatcher, registry)    │
│  - Workers (Huey tasks)                 │
│  - Orchestration (workflows)            │
│  - Agents (AI logic)                    │
│  - LLM (provider abstraction)           │
│  - Storage (MinIO adapter)              │
│  - Observability (events, metrics)      │
└─────────────────────────────────────────┘
```

### Directory Structure

```
backend/
├── config/               # Django project config
│   ├── settings/         # Environment-based settings
│   ├── urls.py           # Root URL routing
│   ├── wsgi.py / asgi.py # Server interfaces
│
├── apps/                 # Application modules
│   ├── worklog/          # Work log domain
│   ├── skills/           # Skill tracking domain
│   ├── reporting/        # Report generation domain
│   ├── jobs/             # Job system infrastructure
│   ├── workers/          # Huey task definitions
│   ├── orchestration/    # Workflow coordination
│   ├── agents/           # AI agents
│   ├── llm/              # LLM provider abstraction
│   ├── storage/          # Storage adapters
│   ├── observability/    # Event logging & metrics
│   ├── api/              # Public API views
│   └── system/           # System dashboard views
│
├── scripts/              # Utility scripts
│   ├── bootstrap.py      # Initial setup
│   ├── create_admin.py   # Create admin user
│   └── seed_demo_data.py # Load demo data
│
└── tests/                # Test suite
    ├── test_jobs.py      # Job system tests
    ├── test_workflows.py # Workflow tests
    └── test_api.py       # API endpoint tests
```

### App Responsibilities

| App | Responsibility |
|-----|---------------|
| `worklog` | Work log CRUD, domain logic |
| `skills` | Skill extraction, normalization, evidence tracking |
| `reporting` | Report generation, templates, rendering |
| `jobs` | Job lifecycle management, scheduling, policies |
| `workers` | Huey task definitions, periodic jobs |
| `orchestration` | Workflow composition, chaining, persistence |
| `agents` | AI-powered analysis and generation |
| `llm` | LLM provider abstraction, prompt management |
| `storage` | MinIO adapter, artifact repository |
| `observability` | Event logging, metrics, execution context |
| `api` | Public REST API endpoints |
| `system` | Internal monitoring and health checks |

---

## Execution Model

### Job Lifecycle

```
1. Enqueue
   ├─ Create Job record (status=queued)
   ├─ Log "job queued" event
   └─ Submit to Huey queue

2. Execute (Worker)
   ├─ Load Job
   ├─ Transition to running
   ├─ Create ExecutionContext
   ├─ Log "job started" event
   ├─ Get workflow from registry
   ├─ Execute workflow
   │   ├─ Call agents
   │   ├─ Call LLM
   │   ├─ Persist results
   │   └─ Log step events
   ├─ Store result in Job
   ├─ Transition to success
   └─ Log "job completed" event

3. Error Handling
   ├─ Catch exception
   ├─ Log error event
   ├─ Check retry policy
   ├─ If retryable:
   │   ├─ Increment retry_count
   │   ├─ Calculate backoff delay
   │   └─ Re-enqueue
   └─ Else: Transition to failed
```

### Job States

- `queued`: Job created, waiting for worker
- `running`: Worker executing job
- `success`: Job completed successfully
- `failed`: Job failed permanently (after retries)
- `cancelled`: Job manually cancelled (future)

### Triggers

- `api`: User-initiated via REST API
- `schedule`: Cron-triggered by scheduler
- `system`: Internal system-triggered
- `retry`: Automatic retry after failure

### Scheduling

The scheduler runs as a Huey periodic task (every minute) and:
1. Loads enabled schedules
2. Evaluates cron expressions
3. Enqueues jobs for due schedules
4. Updates `last_run_at` timestamp

**Cron Syntax Support:**
- Standard cron: `0 9 * * *` (daily at 9am)
- Special: `@hourly`, `@daily`, `@every_minute`

---

## Observability Model

### Event Timeline

Every job has an associated event timeline tracking execution:

```python
Event(
    job=job,
    timestamp=datetime,
    level='info',      # debug, info, warning, error
    source='workflow', # system, worker, workflow, agent, llm
    message='Step completed',
    data={...}         # Structured JSON data
)
```

### Event Sources

- **system**: Infrastructure events (database, queue)
- **worker**: Job execution lifecycle
- **workflow**: Workflow step boundaries
- **agent**: Agent invocations
- **llm**: LLM calls and responses

### Structured Logging

All events are:
1. Stored in the `Event` model (queryable)
2. Logged to standard logging (console/file)
3. Tagged with `trace_id` for correlation

### ExecutionContext

```python
ExecutionContext(
    job_id=uuid,
    trace_id=uuid,      # For distributed tracing
    user_id=int,        # Optional
    parent_job_id=uuid  # For job chaining
)
```

Passed through all workflow steps for consistent event logging.

---

## API Surfaces

### Public API (`/api/*`)

**Authentication**: Django session or token (configurable)  
**Permissions**: User must own resources or be staff

#### Worklogs

- `POST /api/worklogs/` - Create worklog
- `GET /api/worklogs/` - List worklogs
- `GET /api/worklogs/{id}/` - Get worklog detail
- `POST /api/worklogs/{id}/analyze/` - Enqueue analysis job

#### Skills

- `GET /api/skills/` - List skills
- `GET /api/skills/{id}/evidence/` - List skill evidence
- `POST /api/skills/recompute/` - Enqueue skill extraction

#### Reports

- `GET /api/reports/` - List reports
- `POST /api/reports/generate/` - Generate report (status/standup/summary)
- `POST /api/resume/refresh/` - Refresh resume

#### Jobs

- `GET /api/jobs/{id}/` - Get job status
- `GET /api/jobs/{id}/events/` - Get job event timeline

#### Health

- `GET /api/healthz/` - Basic health check
- `GET /api/readyz/` - Readiness with dependency checks

### System Dashboard (`/system/*`)

**Authentication**: Staff only (or DEBUG + `SYSTEM_DASHBOARD_ENABLED`)

#### Monitoring

- `GET /system/overview/` - System stats (job counts, schedules)
- `GET /system/jobs/` - List jobs (filterable by status/type)
- `GET /system/jobs/{id}/` - Job detail
- `GET /system/jobs/{id}/events/` - Job event timeline
- `GET /system/schedules/` - List schedules
- `GET /system/health/` - Deep health checks

### Response Formats

**Job Enqueue Response (202 Accepted):**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "Job enqueued"
}
```

**Job Status Response:**
```json
{
  "id": "uuid",
  "type": "worklog.analyze",
  "status": "success",
  "result": {...},
  "error": null,
  "created_at": "ISO8601",
  "started_at": "ISO8601",
  "finished_at": "ISO8601"
}
```

---

## Job Types & Workflow Mapping

### Registry

Job types are mapped to workflow functions via decorator:

```python
from apps.jobs.registry import register

@register('worklog.analyze')
def analyze_worklog(ctx, payload):
    ...
```

### Job Types

| Job Type | Workflow | Agent | Description |
|----------|----------|-------|-------------|
| `worklog.analyze` | `worklog_analyze.py` | WorklogAgent | Analyze work log entry |
| `skills.extract` | `skills_extract.py` | SkillAgent | Extract skills from work logs |
| `report.generate` | `report_generate.py` | ReportAgent | Generate status/standup report |
| `resume.refresh` | `resume_refresh.py` | ResumeAgent | Refresh user resume |

### Workflow Chaining

Workflows can enqueue follow-up jobs automatically:

```python
# After worklog.analyze completes:
# → Optionally enqueue skills.extract
# → Optionally enqueue report.generate

# Controlled by WORKFLOW_AUTO_CHAIN setting
```

---

## Conventions

### Naming

- **Apps**: Singular domain noun (`worklog`, `skill`, not `worklogs`)
- **Models**: Singular PascalCase (`WorkLog`, `Skill`)
- **Services**: Action verb (`create_worklog`, `add_skill_evidence`)
- **Selectors**: Query verb (`list_worklogs`, `get_skill`)
- **Job types**: Dot-separated namespace (`worklog.analyze`, `skills.extract`)

### Payload Schema

Job payloads are JSON dictionaries:

```python
{
    'worklog_id': int,       # Primary entity ID
    'user_id': int,          # Optional user context
    'window_days': int,      # Time window for queries
    'kind': str,             # Report kind
    # ... type-specific fields
}
```

### Status Enums

Standardized across system:
- Job status: `queued`, `running`, `success`, `failed`, `cancelled`
- Event level: `debug`, `info`, `warning`, `error`
- Event source: `system`, `worker`, `workflow`, `agent`, `llm`

### Database Conventions

- All IDs: Auto-incrementing integers (except Job uses UUID)
- Timestamps: `created_at`, `updated_at` (auto-managed)
- Foreign keys: `{model}_id` or `{relation}` (e.g., `user`, `parent_job`)
- JSON fields: `metadata`, `payload`, `result`, `data`

---

## Extension Guide

### Adding a New Agent

1. **Create agent class** in `apps/agents/`:
   ```python
   from .base import BaseAgent
   
   class MyAgent(BaseAgent):
       def process(self, ctx, input_data):
           self._log(ctx, "Processing...")
           result = self._call_llm(ctx, prompt)
           return result
   ```

2. **Create workflow** in `apps/orchestration/workflows/`:
   ```python
   from apps.jobs.registry import register
   
   @register('my.workflow')
   def my_workflow(ctx, payload):
       agent = MyAgent()
       result = agent.process(ctx, payload)
       return persist_result(ctx, result, "description")
   ```

3. **Add API endpoint** in `apps/api/views/`:
   ```python
   @api_view(['POST'])
   def trigger_my_workflow(request):
       job = enqueue('my.workflow', payload, trigger='api')
       return Response({'job_id': str(job.id)}, 202)
   ```

4. **Register URL** in `apps/api/urls.py`

5. **Write tests** in `tests/`

### Adding a New LLM Provider

1. **Create provider class** in `apps/llm/providers/`:
   ```python
   class MyProvider:
       model_name = "my-model"
       
       def complete(self, prompt, **kwargs):
           # Call external API
           return {"response": "..."}
   ```

2. **Update client factory** in `apps/llm/client.py`:
   ```python
   if provider == 'myprovider':
       return MyProvider(...)
   ```

3. **Add settings** in `config/settings/base.py`:
   ```python
   MY_PROVIDER_ENDPOINT = os.environ.get(...)
   ```

### Adding a New Schedule

```python
from apps.jobs.scheduler import create_schedule

create_schedule(
    name='nightly_report',
    job_type='report.generate',
    cron='0 0 * * *',  # Midnight daily
    payload={'kind': 'summary'},
    enabled=True
)
```

### Adding Observability Instrumentation

Use decorator for automatic tracing:

```python
from apps.observability.decorators import trace_step

@trace_step('extract_entities', source='agent')
def extract_entities(ctx, text):
    # Automatically logs start/end/errors
    return entities
```

---

## MVP vs Future Roadmap

### MVP Implementation (Current)

✅ **Implemented:**
- Core domain models (worklog, skills, reporting)
- Job system with Huey queue
- Basic workflows (analyze, extract, generate)
- Fake LLM provider for testing
- Event timeline observability
- REST API for CRUD operations
- System dashboard (read-only)
- Basic scheduling
- Tests for core functionality

🔧 **Functional Stubs:**
- MinIO storage adapter (methods exist but not connected)
- vLLM provider (structure only, not functional)
- Idempotency checking (structure only)

### Future Enhancements

**Phase 2 - Production Hardening:**
- Real LLM integration (OpenAI, vLLM, Ollama)
- MinIO production implementation
- Advanced retry policies
- Idempotency enforcement
- Webhook notifications
- Job cancellation
- Batch job operations

**Phase 3 - Advanced Features:**
- Skill taxonomy and clustering
- Multi-user collaboration
- Resume templates and themes
- Email parsing for work log ingestion
- Slack/GitHub integration
- Advanced analytics dashboard
- Export to LinkedIn/PDF

**Phase 4 - Scale & Performance:**
- Database read replicas
- Redis Sentinel for HA
- Horizontal worker scaling
- Job priority queues
- Rate limiting
- Caching layer (Redis)

---

## Testing Approach

### Strategy

- **Unit tests**: Domain logic (selectors, services)
- **Integration tests**: Workflows end-to-end
- **API tests**: REST endpoint behavior
- **No external dependencies**: Fake LLM, in-memory queue, SQLite

### Test Configuration

**Settings**: `config/settings/test.py`
- In-memory database (SQLite `:memory:`)
- Huey MemoryHuey with `immediate=True`
- Fake LLM provider
- Simplified logging

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_jobs.py -v

# With coverage
pytest --cov=apps --cov-report=html

# Create test DB if needed
pytest --create-db
```

### Test Organization

```
tests/
├── conftest.py          # Shared fixtures
├── test_jobs.py         # Job lifecycle tests
├── test_workflows.py    # Workflow execution tests
└── test_api.py          # API endpoint tests
```

### Key Fixtures

- `fake_llm`: Ensures local fake provider
- `api_client`: DRF test client
- `test_user`: Authenticated user for API tests

---

## Operational Notes

### Environment Variables

```bash
# Django
DJANGO_SETTINGS_MODULE=config.settings.dev  # or prod, test
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://user:pass@host:5432/db  # or sqlite:///db.sqlite3

# Redis (for Huey)
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=afterresume

# LLM
LLM_PROVIDER=local  # local, vllm
LLM_VLLM_ENDPOINT=http://localhost:8000
LLM_MODEL_NAME=gpt-4

# System Dashboard
SYSTEM_DASHBOARD_ENABLED=True
```

### Running the System

**1. Install dependencies:**
```bash
pip install -e ".[dev]"
```

**2. Run migrations:**
```bash
python manage.py migrate
```

**3. Create admin user:**
```bash
python scripts/create_admin.py
# or
ADMIN_USERNAME=admin ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=admin python scripts/bootstrap.py
```

**4. Seed demo data (optional):**
```bash
python scripts/seed_demo_data.py
```

**5. Start Django server:**
```bash
python manage.py runserver
```

**6. Start Huey worker (separate terminal):**
```bash
python manage.py run_huey
```

**7. Access system:**
- API: http://localhost:8000/api/healthz/
- Admin: http://localhost:8000/admin/
- System Dashboard: http://localhost:8000/system/overview/

### Monitoring

**Check system health:**
```bash
curl http://localhost:8000/system/health/
```

**View job stats:**
```bash
curl http://localhost:8000/system/overview/
```

**Check job status:**
```bash
curl http://localhost:8000/api/jobs/{job_id}/
```

### Debugging

**View job events:**
```bash
curl http://localhost:8000/api/jobs/{job_id}/events/
```

**Check Huey logs:**
Huey worker outputs to console by default.

**Database shell:**
```bash
python manage.py dbshell
```

**Django shell:**
```bash
python manage.py shell
```

### Production Deployment

1. **Set environment:**
   ```bash
   export DJANGO_SETTINGS_MODULE=config.settings.prod
   ```

2. **Generate secret key:**
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

3. **Configure Postgres:**
   ```bash
   export DATABASE_URL=postgres://user:pass@host:5432/db
   ```

4. **Configure Redis:**
   ```bash
   export REDIS_URL=redis://host:6379/0
   ```

5. **Collect static files:**
   ```bash
   python manage.py collectstatic --no-input
   ```

6. **Run with Gunicorn:**
   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:8000
   ```

7. **Run Huey workers (supervisor/systemd):**
   ```bash
   python manage.py run_huey --workers=4
   ```

### Maintenance

**Cleanup old jobs:**
```python
# Runs automatically via periodic task
# Manual trigger:
from apps.workers.periodic import cleanup_old_jobs
cleanup_old_jobs()
```

**View schedules:**
```bash
python manage.py shell
>>> from apps.jobs.models import Schedule
>>> Schedule.objects.filter(enabled=True)
```

---

## Conclusion

This system provides a solid foundation for AI-powered work tracking and resume generation. The architecture is modular, extensible, and observable. The MVP focuses on core functionality with clear extension points for future enhancements.

**Key Design Principles:**
- 🎯 **Separation of Concerns**: Layered architecture with clear boundaries
- 🔄 **Async by Default**: All heavy work in background jobs
- 📊 **Observable**: Event timeline for every job
- 🧩 **Modular**: Easy to add agents, workflows, providers
- 🧪 **Testable**: No external dependencies in tests
- 📖 **Documented**: Code and system design aligned

For questions or contributions, see `README.md` and code comments.
