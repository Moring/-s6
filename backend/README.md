# AfterResume Backend

AI-powered work tracking and resume generation system.

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run migrations
python manage.py migrate

# Create admin user
python scripts/create_admin.py

# Run development server
python manage.py runserver

# Run worker (in separate terminal)
python manage.py run_huey

# Run tests
pytest
```

## Environment Variables

```
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3  # or postgres://...
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
LLM_PROVIDER=local  # local, vllm
SYSTEM_DASHBOARD_ENABLED=True
```

## Architecture

See `SYSTEM_DESIGN.md` for complete architecture documentation.

### Key Components

- **Domain Apps**: worklog, skills, reporting
- **Job System**: async task execution with Huey
- **Orchestration**: workflows coordinating agents
- **Agents**: AI-powered analysis and generation
- **Observability**: event timeline and structured logging
- **System Dashboard**: operational monitoring API

### API Endpoints

- `/api/worklogs/` - Work log management
- `/api/skills/` - Skill tracking
- `/api/reports/` - Report generation
- `/api/jobs/{id}/` - Job status
- `/system/` - System dashboard (staff only)

## Development

```bash
# Seed demo data
python scripts/seed_demo_data.py

# Run specific tests
pytest tests/test_jobs.py -v

# Format code
black .
ruff check .
```
