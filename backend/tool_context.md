# AfterResume Backend - Tool Context for AI Agents

**Version**: 1.0  
**Last Updated**: 2025-12-31  
**Purpose**: Machine-readable specification for AI agents to understand, modify, and extend the AfterResume backend system.

---

## System Overview

AfterResume is a **job-driven, agent-oriented backend** for AI-powered work tracking and resume generation.

**Core Concept**: All long-running or AI-powered operations execute as **jobs** that are **observable**, **retryable**, and **composable**.

**Architecture Pattern**: Orchestration Platform (not a traditional web app)

---

## System Topology

```
Frontend (Vue SPA, Node-based runtime)
    ↓ HTTP/REST
Backend API (Django + DRF)
    ↓ Job Enqueue
Job Queue (Valkey + Huey)
    ↓ Worker Poll
Worker (Huey Consumer)
    ↓ Execute
Workflow (Orchestration Layer)
    ↓ Call
Agent (AI Logic)
    ↓ LLM Call
LLM Provider (vLLM/Local)
    ↓ Return
Result → Persistence → Event Log
```

---

## API Authentication & Service Auth

### Service-to-Service Token
- Frontend → backend requests to `/api/*` (except `/api/auth/`, `/api/healthz`, `/api/share/`) must include `X-Service-Token`
- Token format: `timestamp:hmac_signature` using `SERVICE_TO_SERVICE_SECRET`
- Token TTL: 5 minutes (clock skew tolerated)

### User Authentication (JWT)
- `/api/auth/login/` and `/api/auth/signup/` return `{access, user}` and set a refresh cookie
- SPA stores the access token in memory and sends `Authorization: Bearer <access>` on API calls
- `/api/auth/token/refresh/` issues a new access token using the HttpOnly refresh cookie
- `/api/auth/token/` returns `{access, refresh, user}` for scripts or non-SPA clients
- `/api/auth/logout/` clears the refresh cookie and blacklists the refresh token (when provided)

**Refresh Cookie Defaults**:
- Name: `JWT_REFRESH_COOKIE_NAME` (default `afterresume_refresh`)
- Path: `/api/auth/`
- HttpOnly, SameSite=Lax, Secure in production

---

## Directory Structure (Canonical)

```
backend/
├── config/                    # Django project settings
├── apps/
│   ├── api/                   # HTTP boundary (views)
│   ├── worklog/               # Domain: work logs
│   ├── skills/                # Domain: skills
│   ├── reporting/             # Domain: reports
│   ├── jobs/                  # Job system
│   ├── workers/               # Async execution
│   ├── orchestration/         # Workflows
│   ├── agents/                # AI logic
│   ├── llm/                   # LLM abstraction
│   ├── storage/               # Storage adapters
│   ├── observability/         # Events & tracing
│   └── system/                # Admin dashboard
├── scripts/                   # Operational scripts
└── tests/                     # Test suite
```

---

## Core Concepts

### 1. Job

**Definition**: A unit of asynchronous work with full lifecycle tracking.

**Model**: `apps/jobs/models.py::Job`

**Fields**:
- `id`: UUID (primary key)
- `type`: str (workflow identifier, e.g., 'worklog.analyze')
- `status`: enum ['queued', 'running', 'success', 'failed']
- `trigger`: enum ['api', 'schedule', 'retry', 'system']
- `payload`: JSON (workflow inputs)
- `result`: JSON (workflow outputs, nullable)
- `error`: str (failure message, nullable)
- `retry_count`: int
- `max_retries`: int (default 3)
- `scheduled_for`: datetime (nullable, for delayed execution)
- `parent_job`: FK to Job (nullable, for chaining)
- `user`: FK to User (nullable)
- `created_at`, `started_at`, `finished_at`: datetime

**Lifecycle**:
```
queued → running → [success|failed]
               ↓
            (retry) → queued
```

**Operations**:
- Create: `apps/jobs/dispatcher.py::enqueue()`
- Execute: `apps/workers/execute_job.py::execute_job()`
- Query: `apps/system/selectors.py` or `apps/api/views/jobs.py`

### 2. Workflow

**Definition**: A registered function that implements business logic for a job type.

**Location**: `apps/orchestration/workflows/*.py`

**Signature**:
```python
from apps.observability.context import ExecutionContext

def workflow_name(ctx: ExecutionContext, payload: dict) -> dict:
    """
    Execute workflow logic.
    
    Args:
        ctx: Execution context (job_id, trace_id, user_id)
        payload: Workflow inputs (job-specific)
    
    Returns:
        result: dict with workflow outputs
    
    Raises:
        Exception: On failure (triggers retry/fail)
    """
    pass
```

**Registration**:
```python
from apps.jobs.registry import register

@register('workflow.type')
def my_workflow(ctx, payload):
    # implementation
    return result
```

**Existing Workflows**:
1. `worklog.analyze` - Analyze work log content
2. `skills.extract` - Extract skills from work logs
3. `report.generate` - Generate reports (status/standup)
4. `resume.refresh` - Update resume from latest data
5. `gamification.reward_evaluate` - Evaluate rewards on worklog changes

### 3. Agent

**Definition**: Pure function/class containing AI logic (no side effects).

**Location**: `apps/agents/*.py`

**Base Class**: `apps/agents/base.py::BaseAgent`

**Responsibilities**:
- Call LLM with prompts
- Parse LLM responses
- Return structured data

**Constraints**:
- ❌ NO database access
- ❌ NO HTTP calls
- ❌ NO file I/O
- ✅ Pure transformation only
- ✅ Workflows handle persistence

**Pattern**:
```python
from apps.agents.base import BaseAgent

class MyAgent(BaseAgent):
    def process(self, ctx, input_data):
        # Build prompt
        prompt = self._build_prompt(input_data)
        
        # Call LLM
        response = self._call_llm(ctx, prompt)
        
        # Parse and return
        return self._parse_response(response)
```

**Existing Agents**:
- `WorklogAgent` - Analyze work logs
- `SkillAgent` - Extract skills
- `ReportAgent` - Generate reports
- `ResumeAgent` - Create resumes

### 4. ExecutionContext

**Definition**: Carrier object for trace information.

**Model**: `apps/observability/context.py::ExecutionContext`

**Fields**:
- `job_id`: UUID
- `trace_id`: str (unique per execution)
- `user_id`: int (nullable)

**Usage**:
```python
# Create from job
ctx = ExecutionContext.from_job(job)

# Pass to all functions
result = workflow(ctx, payload)
agent_output = agent.process(ctx, data)
log_event(ctx, "message", source='workflow')
```

**Purpose**: Enables distributed tracing and event correlation.

### 5. Event

**Definition**: Timestamped log entry associated with a job.

**Model**: `apps/observability/models.py::Event`

**Fields**:
- `job`: FK to Job
- `timestamp`: datetime
- `level`: enum ['debug', 'info', 'warning', 'error']
- `source`: enum ['system', 'workflow', 'agent', 'llm', 'worker']
- `message`: str
- `data`: JSON (additional context)

**Logging**:
```python
from apps.observability.services import log_event

log_event(
    ctx,
    message="Processing started",
    level='info',
    source='workflow',
    item_count=10,
    user_id=user.id
)
```

**Query**:
```python
from apps.observability.models import Event

events = Event.objects.filter(job_id=job_id).order_by('timestamp')
```

---

## Data Flow Patterns

### Pattern 1: API-Triggered Job

```
1. Frontend → POST /api/worklogs/{id}/analyze/
2. API View → enqueue('worklog.analyze', payload)
3. Dispatcher → Job.objects.create(status='queued')
4. Dispatcher → execute_job.delay(job_id)  # Huey task
5. Worker → Job.status = 'running'
6. Worker → workflow = get_workflow('worklog.analyze')
7. Worker → result = workflow(ctx, payload)
8. Workflow → agent = WorklogAgent()
9. Workflow → analysis = agent.analyze(ctx, content)
10. Agent → llm_response = llm_client.call(prompt)
11. Agent → return structured_data
12. Workflow → worklog.metadata.update(analysis)
13. Workflow → return result
14. Worker → Job.status = 'success', Job.result = result
15. API → GET /api/jobs/{job_id}/ returns status
```

### Pattern 2: Scheduled Job

```
1. Schedule → Schedule.objects.create(job_type='report.generate', cron='0 9 * * *')
2. Periodic Task → scheduler.tick() (every minute)
3. Scheduler → for schedule in Schedule.objects.filter(enabled=True)
4. Scheduler → if should_run(schedule):
5. Scheduler → enqueue(schedule.job_type, schedule.payload)
6. (continues as API-triggered job)
```

### Pattern 3: Job Chaining

```
1. Workflow A → enqueue('workflow.b', payload, parent_job=ctx.job_id)
2. Job B → parent_job FK points to Job A
3. Query → Job.objects.filter(parent_job=job_a_id)
```

### Pattern 4: Job Retry

```
1. Worker → try: workflow(ctx, payload)
2. Worker → except Exception as e:
3. Worker → if should_retry(job):
4. Worker → job.retry_count += 1
5. Worker → delay = calculate_retry_delay(retry_count)  # exponential backoff
6. Worker → enqueue(job.type, payload, scheduled_for=now + delay)
7. Worker → else: job.status = 'failed'
```

---

## API Endpoints

### Public API (`/api/*`)

**Health**:
- `GET /api/healthz/` - Simple health check
- `GET /api/readyz/` - Deep health check

**Worklogs**:
- `GET /api/worklogs/` - List work logs
- `POST /api/worklogs/` - Create work log
- `GET /api/worklogs/{id}/` - Get work log
- `PUT /api/worklogs/{id}/` - Update work log
- `DELETE /api/worklogs/{id}/` - Delete work log
- `POST /api/worklogs/{id}/analyze/` - Trigger analysis (returns job_id)

**Skills**:
- `GET /api/skills/` - List skills
- `GET /api/skills/{id}/evidence/` - List evidence for skill
- `POST /api/skills/recompute/` - Trigger extraction (returns job_id)

**Reports**:
- `GET /api/reports/` - List reports
- `POST /api/reports/generate/` - Generate report (returns job_id)
- `POST /api/resume/refresh/` - Refresh resume (returns job_id)

**Jobs**:
- `GET /api/jobs/{id}/` - Get job status
- `GET /api/jobs/{id}/events/` - Get job event timeline

### System Dashboard (`/system/*`, staff-only)

- `GET /system/overview/` - System stats (job counts, health)
- `GET /system/jobs/` - List jobs (with filters)
- `GET /system/jobs/{id}/` - Job detail
- `GET /system/jobs/{id}/events/` - Event timeline
- `GET /system/schedules/` - List schedules
- `GET /system/health/` - Deep health check

---

## Database Schema

### Core Tables

**jobs_job**:
```sql
CREATE TABLE jobs_job (
    id UUID PRIMARY KEY,
    type VARCHAR(100),
    status VARCHAR(20),  -- queued, running, success, failed
    trigger VARCHAR(20),  -- api, schedule, retry, system
    payload JSONB,
    result JSONB,
    error TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    scheduled_for TIMESTAMP,
    parent_job_id UUID REFERENCES jobs_job(id),
    user_id INT REFERENCES auth_user(id),
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);
```

**jobs_schedule**:
```sql
CREATE TABLE jobs_schedule (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),
    job_type VARCHAR(100),
    cron VARCHAR(100),  -- e.g., "0 9 * * *"
    payload JSONB,
    enabled BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP,
    created_at TIMESTAMP
);
```

**observability_event**:
```sql
CREATE TABLE observability_event (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES jobs_job(id),
    timestamp TIMESTAMP,
    level VARCHAR(20),  -- debug, info, warning, error
    source VARCHAR(50),  -- system, workflow, agent, llm, worker
    message TEXT,
    data JSONB
);
```

**worklog_worklog**:
```sql
CREATE TABLE worklog_worklog (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES auth_user(id),
    date DATE,
    content TEXT,
    source VARCHAR(50),  -- manual, import, api
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**skills_skill**:
```sql
CREATE TABLE skills_skill (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES auth_user(id),
    name VARCHAR(200),
    normalized VARCHAR(200),  -- canonical form
    confidence FLOAT,  -- 0.0 to 1.0
    level VARCHAR(50),  -- beginner, intermediate, advanced, expert
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**skills_skillevidence**:
```sql
CREATE TABLE skills_skillevidence (
    id SERIAL PRIMARY KEY,
    skill_id INT REFERENCES skills_skill(id),
    source_type VARCHAR(50),  -- worklog, project, certification
    source_id INT,
    excerpt TEXT,
    created_at TIMESTAMP
);
```

**reporting_report**:
```sql
CREATE TABLE reporting_report (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES auth_user(id),
    kind VARCHAR(50),  -- resume, status, standup
    content JSONB,
    rendered_text TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## Extension Guide

### Adding a New Workflow

**1. Create workflow file**:
```python
# apps/orchestration/workflows/my_workflow.py

from apps.jobs.registry import register
from apps.observability.services import log_event

@register('my.workflow')
def my_workflow(ctx, payload: dict) -> dict:
    """
    My new workflow.
    
    Payload:
        input_id: ID of input object
    
    Returns:
        output: dict with results
    """
    input_id = payload['input_id']
    
    log_event(ctx, f"Processing input {input_id}", source='workflow')
    
    # Load data
    from apps.myapp.selectors import get_input
    input_obj = get_input(input_id)
    
    # Run agent
    from apps.agents.my_agent import MyAgent
    agent = MyAgent()
    result = agent.process(ctx, input_obj.data)
    
    # Persist
    from apps.myapp.services import save_output
    output = save_output(input_id, result)
    
    log_event(ctx, "Processing complete", source='workflow')
    
    return {'output_id': output.id, 'result': result}
```

**2. Create API endpoint**:
```python
# apps/api/views/my_views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from apps.jobs.dispatcher import enqueue

@api_view(['POST'])
def trigger_my_workflow(request, pk):
    """Trigger my workflow."""
    job = enqueue(
        job_type='my.workflow',
        payload={'input_id': pk},
        trigger='api',
        user=request.user if request.user.is_authenticated else None
    )
    
    return Response({
        'job_id': str(job.id),
        'status': job.status
    }, status=status.HTTP_202_ACCEPTED)
```

**3. Register URL**:
```python
# apps/api/urls.py

from apps.api.views.my_views import trigger_my_workflow

urlpatterns = [
    # ...
    path('my-resource/<int:pk>/process/', trigger_my_workflow),
]
```

**4. Test**:
```python
# tests/test_my_workflow.py

import pytest
from apps.jobs.dispatcher import enqueue
from apps.workers.execute_job import execute_job

@pytest.mark.django_db
def test_my_workflow():
    # Create input
    input_obj = MyInput.objects.create(data='test')
    
    # Enqueue job
    job = enqueue('my.workflow', {'input_id': input_obj.id}, trigger='test')
    
    # Execute
    execute_job(str(job.id))
    
    # Verify
    job.refresh_from_db()
    assert job.status == 'success'
    assert 'output_id' in job.result
```

### Adding a New Agent

**1. Create agent class**:
```python
# apps/agents/my_agent.py

from .base import BaseAgent

class MyAgent(BaseAgent):
    """My custom agent."""
    
    def process(self, ctx, input_data: dict) -> dict:
        """
        Process input data.
        
        Args:
            ctx: Execution context
            input_data: Input dictionary
        
        Returns:
            result: Processed output
        """
        self._log(ctx, "Processing input", input_size=len(input_data))
        
        # Build prompt
        prompt = self._build_prompt(input_data)
        
        # Call LLM
        llm_response = self._call_llm(ctx, prompt)
        
        # Parse
        result = self._parse_response(llm_response)
        
        self._log(ctx, "Processing complete", result_size=len(result))
        
        return result
    
    def _build_prompt(self, input_data: dict) -> str:
        """Build LLM prompt."""
        return f"Process this data: {input_data}"
    
    def _parse_response(self, response: dict) -> dict:
        """Parse LLM response."""
        return response.get('result', {})
```

**2. Use in workflow**:
```python
# apps/orchestration/workflows/my_workflow.py

from apps.agents.my_agent import MyAgent

@register('use.my.agent')
def use_my_agent_workflow(ctx, payload):
    agent = MyAgent()
    result = agent.process(ctx, payload)
    return result
```

### Adding a New LLM Provider

**1. Create provider class**:
```python
# apps/llm/providers/my_provider.py

from typing import Optional

class MyLLMProvider:
    """My custom LLM provider."""
    
    def __init__(self, endpoint: str, api_key: Optional[str] = None):
        self.endpoint = endpoint
        self.api_key = api_key
    
    def call(
        self,
        prompt: str,
        model: str = 'default',
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> dict:
        """
        Call LLM.
        
        Args:
            prompt: Input prompt
            model: Model identifier
            max_tokens: Max response length
            temperature: Sampling temperature
        
        Returns:
            response: dict with 'text' key
        """
        import requests
        
        response = requests.post(
            f"{self.endpoint}/v1/completions",
            headers={'Authorization': f'Bearer {self.api_key}'},
            json={
                'model': model,
                'prompt': prompt,
                'max_tokens': max_tokens,
                'temperature': temperature
            }
        )
        
        return response.json()
```

**2. Update client factory**:
```python
# apps/llm/client.py

def get_llm_client(provider: str = None):
    """Get LLM client."""
    provider = provider or os.environ.get('LLM_PROVIDER', 'local')
    
    if provider == 'local':
        from .providers.local import LocalLLMProvider
        return LocalLLMProvider()
    
    elif provider == 'vllm':
        from .providers.vllm import VLLMProvider
        endpoint = os.environ.get('LLM_VLLM_ENDPOINT')
        return VLLMProvider(endpoint)

    elif provider == 'ollama':
        from .providers.ollama import OllamaProvider
        endpoint = os.environ.get('OLLAMA_ENDPOINT')
        model = os.environ.get('LLM_MODEL_NAME')
        return OllamaProvider(endpoint, model)
    
    elif provider == 'my_provider':
        from .providers.my_provider import MyLLMProvider
        endpoint = os.environ.get('MY_PROVIDER_ENDPOINT')
        api_key = os.environ.get('MY_PROVIDER_API_KEY')
        return MyLLMProvider(endpoint, api_key)
    
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
```

**3. Configure**:
```bash
# .env
LLM_PROVIDER=my_provider
MY_PROVIDER_ENDPOINT=https://api.example.com
MY_PROVIDER_API_KEY=secret
```

---

## Testing Patterns

### Unit Test (Domain Logic)

```python
import pytest
from apps.myapp.services import my_service

@pytest.mark.django_db
def test_my_service():
    result = my_service(input_data='test')
    assert result == expected
```

### Integration Test (Workflow)

```python
import pytest
from apps.jobs.dispatcher import enqueue
from apps.workers.execute_job import execute_job

@pytest.mark.django_db
def test_my_workflow():
    job = enqueue('my.workflow', {'input': 'test'}, trigger='test')
    execute_job(str(job.id))
    
    job.refresh_from_db()
    assert job.status == 'success'
    assert job.result['output'] == expected
```

### API Test

```python
import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_my_endpoint():
    client = APIClient()
    response = client.post('/api/my-endpoint/', {'data': 'test'})
    
    assert response.status_code == 202
    assert 'job_id' in response.data
```

---

## Configuration

### Environment Variables

**Django**:
- `DJANGO_SETTINGS_MODULE`: `config.settings.dev|prod`
- `SECRET_KEY`: Django secret key
- `DEBUG`: `True|False`
- `DJANGO_ALLOWED_HOSTS`: Comma-separated hosts

**Database**:
- `DATABASE_URL`: PostgreSQL connection string
- Or individual: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`

**Queue (Huey)**:
- `REDIS_URL`: `redis://host:port/db`
- `HUEY_IMMEDIATE`: `true|false` (sync execution for tests)

**Storage (MinIO)**:
- `MINIO_ENDPOINT`: `host:port`
- `MINIO_ACCESS_KEY`: Access key
- `MINIO_SECRET_KEY`: Secret key
- `MINIO_SECURE`: `True|False` (use HTTPS)
- `MINIO_BUCKET`: Bucket name

**LLM**:
- `LLM_PROVIDER`: `local|vllm|ollama|custom`
- `LLM_VLLM_ENDPOINT`: vLLM API endpoint
- `OLLAMA_ENDPOINT`: Ollama API endpoint
- `LLM_MODEL_NAME`: Model identifier

**Text Extraction (Tika)**:
- `TIKA_ENDPOINT`: Apache Tika endpoint

**System**:
- `SYSTEM_DASHBOARD_ENABLED`: `True|False`

---

## Operational Commands

### Development

```bash
# Start development server
python manage.py runserver

# Run worker
python manage.py run_huey

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run tests
pytest tests/ -v
```

### Production

```bash
# Collect static files
python manage.py collectstatic --noinput

# Run with gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4

# Run worker (multiple processes)
python manage.py run_huey -w 8 -k thread

# Run scheduler (periodic tasks)
python manage.py run_huey --periodic
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Putting logic in API views

**Wrong**:
```python
@api_view(['POST'])
def process_worklog(request, pk):
    worklog = WorkLog.objects.get(pk=pk)
    # ❌ Business logic in view
    result = analyze_content(worklog.content)
    worklog.metadata['analysis'] = result
    worklog.save()
    return Response(result)
```

**Right**:
```python
@api_view(['POST'])
def process_worklog(request, pk):
    # ✅ Enqueue job
    job = enqueue('worklog.analyze', {'worklog_id': pk}, trigger='api')
    return Response({'job_id': str(job.id)}, status=202)
```

### Pitfall 2: Agents accessing database

**Wrong**:
```python
class MyAgent(BaseAgent):
    def process(self, ctx, input_id):
        # ❌ DB access in agent
        obj = MyModel.objects.get(id=input_id)
        return self.analyze(obj.data)
```

**Right**:
```python
# In workflow:
@register('my.workflow')
def my_workflow(ctx, payload):
    input_id = payload['input_id']
    
    # ✅ Workflow loads data
    obj = MyModel.objects.get(id=input_id)
    
    # ✅ Agent gets pure data
    agent = MyAgent()
    result = agent.process(ctx, obj.data)
    
    # ✅ Workflow persists
    obj.processed_data = result
    obj.save()
    
    return result
```

### Pitfall 3: Missing event logging

**Wrong**:
```python
@register('my.workflow')
def my_workflow(ctx, payload):
    # Process stuff
    return result
```

**Right**:
```python
@register('my.workflow')
def my_workflow(ctx, payload):
    log_event(ctx, "Workflow started", source='workflow')
    
    # Process stuff
    
    log_event(ctx, "Workflow complete", source='workflow', result_size=len(result))
    return result
```

### Pitfall 4: Synchronous I/O in workflows

**Wrong**:
```python
@register('slow.workflow')
def slow_workflow(ctx, payload):
    # ❌ Blocking I/O
    time.sleep(60)
    return result
```

**Right**:
```python
# If truly long-running:
@register('parent.workflow')
def parent_workflow(ctx, payload):
    # ✅ Chain jobs
    enqueue('child.workflow', payload, parent_job=ctx.job_id)
    return {'status': 'chained'}
```

---

## Gamification Workflow: Reward Evaluation

### Workflow: `gamification.reward_evaluate`

**Location**: `apps/orchestration/workflows/reward_evaluate.py`

**Purpose**: Evaluate and grant rewards (XP, badges, challenges) when a worklog entry is created or updated.

**Trigger**: Automatically called by `apps/worklog/services.py` on entry create/update and attachment upload.

**Payload**:
```python
{
    'entry_id': int  # WorkLog ID
}
```

**Returns**:
```python
{
    'entry_id': int,
    'job_id': str,
    'valid': bool,                    # Entry passed validation
    'xp_awarded': int,                # XP granted
    'streak_updated': bool,           # Streak incremented
    'streak': {
        'current': int,
        'longest': int,
        'freeze_used': bool,
        'broken': bool
    },
    'badges_awarded': list[str],      # Badge codes awarded
    'challenges_updated': list[str],  # Challenge codes updated
    'errors': list[str]               # Any errors encountered
}
```

### Workflow Steps

**Step 1: Load Entry**
- Fetch WorkLog by `entry_id`
- Validate user exists
- Load reward configuration (RewardConfig model or defaults)

**Step 2: Validate Meaningfulness**
- Tool: `apps/gamification/tools/entry_validator.py::is_meaningful_entry()`
- Checks:
  - Minimum content length (20 chars)
  - Not duplicate/spam (rate limits: max 10/hour, 60s between duplicates)
  - Recent entries for abuse detection
- Returns: `(bool, dict)` - valid flag + reasons

**Step 3: Compute XP**
- Tool: `apps/gamification/tools/xp_calculator.py::compute_xp()`
- Inputs: entry, attachments_count, tags, config
- Quality signals:
  - Base entry: 10 XP
  - Per attachment: 5 XP (max 3)
  - Per tag: 3 XP (max 5)
  - Length bonus: 10 XP (>= 200 chars)
  - Outcome/impact fields: 15 XP
  - Metrics present: 10 XP
- Daily cap enforcement: max 200 XP/day
- Returns: `{'total_xp': int, 'breakdown': dict, 'capped': bool}`

**Step 4: Persist XP Event**
- Tool: `apps/gamification/tools/persister.py::persist_events()`
- Creates `XPEvent` with idempotency key: `xp:{user_id}:{entry_id}:{date}:{reason_hash}`
- Updates `UserXP.total_xp`, `UserXP.daily_xp`, `UserXP.level`
- Atomicity: uses transaction + unique constraint on idempotency_key

**Step 5: Update Streak**
- Tool: `apps/gamification/tools/streak_updater.py::update_streak()`
- Logic:
  - Same day: no change
  - Consecutive day: increment `current_streak`
  - Missed 1 day + freeze available: decrement `freezes_remaining`, keep streak
  - Missed >1 day or no freeze: reset streak to 1
  - Update `longest_streak` if `current_streak` exceeds it
- Returns: new streak state

**Step 6: Award Badges**
- Tool: `apps/gamification/tools/badge_awarder.py::award_badges()`
- Triggers checked:
  - `first_entry`: worklog count == 1
  - `streak_7/30/100`: current_streak threshold
  - `total_entries_10/50/100`: worklog count threshold
  - `first_attachment`: has_attachment && attachment_count == 1
  - `level_5/10`: user level threshold
- Idempotency key: `badge:{user_id}:{badge_code}`
- Creates `UserBadge` with provenance: `{'job_id': ..., 'trigger': ..., 'threshold': ...}`
- Returns: list of badge codes awarded

**Step 7: Update Challenges**
- Tool: `apps/gamification/tools/challenge_updater.py::update_challenges()`
- Weekly challenges (Monday-Sunday):
  - `log_days`: increment if unique date
  - `attach_evidence`: increment if has_attachment
  - `write_outcomes`: increment if has outcome/impact
- Mark completed if `current_progress >= target_progress`
- Award XP on completion (via XPEvent with idempotency)
- Returns: list of challenge codes updated

**Step 8: Emit Events**
- Log observability events at each step:
  - `log_event(ctx, "Validating entry", source='workflow.reward')`
  - `log_event(ctx, "Awarded XP", source='workflow.reward', xp=10)`
  - etc.

### Anti-Gaming Protections

**Idempotency**:
- XPEvent uses unique idempotency key (prevents double XP on retries)
- UserBadge has unique constraint on (user, badge)

**Rate Limiting**:
- Max 10 entries/hour per user
- Min 60 seconds between entries (duplicate detection)
- Daily XP cap: 200 XP

**Quality Thresholds**:
- Minimum 20 character content
- Attachment bonuses capped (max 3)
- Tag bonuses capped (max 5)

**Streak Fairness**:
- Streak freezes limited (3 total, earnable via perks)
- Only 1 freeze applies per missed day
- Micro-spam entries rejected by validation

### Configuration

**RewardConfig Model** (editable via Django admin):
```python
{
    'min_entry_length': 20,
    'max_entries_per_hour': 10,
    'duplicate_threshold_seconds': 60,
    'max_daily_xp': 200,
    'xp_rules': {
        'base_entry': 10,
        'per_attachment': 5,
        'per_tag': 3,
        'length_bonus_threshold': 200,
        'length_bonus': 10,
        'outcome_bonus': 15,
        'metrics_bonus': 10,
        'agile_field_bonus': 5
    },
    'max_freezes': 3
}
```

### Example Execution

**Input**:
```python
payload = {'entry_id': 123}
```

**Flow**:
1. Load WorkLog #123 (user: alice, date: 2025-12-31, content: 250 chars, 1 attachment, 2 tags, has outcome)
2. Validate: ✅ valid (length OK, not spam, not duplicate)
3. Compute XP: 10 (base) + 5 (attachment) + 6 (2 tags) + 10 (length) + 15 (outcome) = 46 XP
4. Persist: XPEvent created, UserXP.total_xp += 46, level = 1 → 1 (no level up)
5. Streak: yesterday logged → increment to 2 days
6. Badges: Check `first_attachment` → already awarded, skip
7. Challenges: Increment "log_days" (3/5), "write_outcomes" (2/3)
8. Return: `{'xp_awarded': 46, 'streak': {'current': 2, ...}, 'badges_awarded': [], ...}`

**Observability Events**:
```
[workflow.reward] Validating entry
[workflow.reward] Computing XP
[workflow.reward] Awarded 46 XP
[workflow.reward] Updating streak
[workflow.reward] Checking badges
[workflow.reward] Updating challenges
[workflow.reward] Reward evaluation completed: XP=46, badges=0, challenges=2
```

### Testing

**Test Coverage** (`tests/test_gamification.py`):
- Entry validation (valid, too short, rate limited)
- XP calculation (base, bonuses, caps, daily limits)
- Streak logic (first, consecutive, same day, freeze usage, broken)
- Badge awarding (idempotency, thresholds)
- Challenge progress (log days, completion, XP rewards)
- Tenant isolation
- Manual admin actions

**Integration Test**:
```python
# Create worklog entry
worklog = WorkLog.objects.create(user=user, date=today, content="Test" * 50)

# Trigger reward evaluation (happens automatically via service)
from apps.gamification.services import trigger_reward_evaluation
job_id = trigger_reward_evaluation(worklog.id, user.id)

# Wait for job completion
job = Job.objects.get(id=job_id)
assert job.status == 'success'

# Verify XP awarded
user.refresh_from_db()
assert user.xp.total_xp > 0
assert user.xp.daily_xp > 0

# Verify streak updated
assert user.streak.current_streak > 0
```

---

## Summary for AI Agents

**To work with this codebase**:

1. **All async work** goes through `enqueue()` → creates `Job` → triggers `execute_job()`
2. **Workflows** are registered functions in `apps/orchestration/workflows/`
3. **Agents** are pure classes in `apps/agents/` (no side effects)
4. **Events** must be logged at every step via `log_event(ctx, ...)`
5. **Context** (`ExecutionContext`) propagates through every function
6. **API views** only validate, enqueue jobs, and return job_id
7. **Tests** must pass before any change is complete

**To extend**:
- New workflow? → Create file, register with `@register()`, add API endpoint, test
- New agent? → Subclass `BaseAgent`, implement `process()`, use in workflow
- New domain? → Create app with models/services/selectors, follow existing patterns

**Architecture Goal**: Small orchestration platform, not web app with AI glued on.

---

**End of Tool Context**
