# AfterResume Frontend

Django + HTMX frontend for AfterResume AI-powered work tracking system.

## Architecture

**Pattern**: Presentation layer only  
**Framework**: Django 6.0 + HTMX  
**Theme**: Inspinia/SEED Bootstrap 5 Admin  
**Auth**: django-allauth (session-based)

The frontend **never** directly accesses the database or MinIO. All data operations go through the backend API (`BACKEND_BASE_URL`).

## Directory Structure

```
frontend/
├── apps/                      # Django apps
│   ├── ui/                    # Home, dashboard, jobs
│   ├── worklog/               # Worklog UI
│   ├── billing/               # Billing & reserve UI
│   ├── skills/                # Skills UI
│   ├── reporting/             # Reports UI
│   ├── admin_panel/           # Admin dashboards
│   ├── system/                # System monitoring
│   ├── accounts/              # User profiles
│   └── api_proxy/             # Backend API client
├── templates/                 # Django templates
│   ├── base_shell.html        # Master layout
│   ├── partials/              # Reusable components
│   ├── ui/, worklog/, etc.    # App-specific templates
├── static/                    # Theme assets
│   ├── css/                   # Bootstrap 5 + theme
│   ├── js/                    # Theme scripts + HTMX
│   ├── images/                # Logos, icons
│   └── fonts/                 # Web fonts
├── config/                    # Django settings
└── tests/                     # Frontend tests

```

## Quick Start

```bash
# Start frontend (requires backend running)
docker compose -f docker-compose.yml up -d

# Restart after code changes
docker compose -f docker-compose.yml restart frontend

# View logs
docker compose -f docker-compose.yml logs -f frontend

# Open shell
docker compose -f docker-compose.yml exec frontend python manage.py shell

# Access
http://localhost:3000
```

## Key URLs

- `/` - Home (redirects to dashboard if logged in)
- `/dashboard/` - Main dashboard
- `/worklog/` - Worklog timeline
- `/billing/settings/` - Billing & reserve
- `/skills/` - Skills view
- `/reporting/` - Reports
- `/admin-panel/metrics/` - Executive metrics (staff only)
- `/admin-panel/billing/` - Billing admin (staff only)
- `/admin-panel/passkeys/` - Invite passkeys (staff only)
- `/system/` - System dashboard (staff only)
- `/accounts/login/` - Login
- `/accounts/signup/` - Signup (passkey required)
- `/django-admin/` - Django admin panel

## Theme

**Source**: Inspinia/SEED v4.0.1 (Bootstrap 5)  
**Documentation**: `THEME_SYNC.md`  
**Assets Location**: `frontend/static/`

The theme provides:
- Responsive layout (scrollable sidebar)
- Dark/light mode toggle
- Bootstrap 5 components
- Tabler Icons (`ti ti-*`)
- simplebar scrollbars
- jQuery + Bootstrap JS

### Theme Customization

To update logos:
- `static/images/logo.png` - Light mode logo
- `static/images/logo-black.png` - Dark mode logo
- `static/images/logo-sm.png` - Small/mobile logo
- `static/images/favicon.ico` - Favicon

## HTMX Usage

HTMX is used for:
- **Status bar**: Auto-refresh every 30s (`hx-get`, `hx-trigger="load, every 30s"`)
- **Reserve balance**: Live updates
- **Partial updates**: Modal content, inline edits
- **Form submissions**: No full page reloads

Example:
```html
<div hx-get="/api-proxy/status-bar/" 
     hx-trigger="load, every 30s" 
     hx-swap="innerHTML">
    Loading...
</div>
```

## Security

- **Auth-by-default**: All views require `@login_required` or `@staff_member_required`
- **Public routes**: Only `/accounts/*` and `/health/`
- **CSRF**: Enabled on all POST forms
- **Session-based**: Django sessions (not JWT)
- **Admin routes**: Require `user.is_staff = True`

## Development Workflow

### Add a New Page

1. **Create view** in `apps/<app>/views.py`:
   ```python
   @login_required
   def my_view(request):
       return render(request, 'myapp/page.html', context)
   ```

2. **Add URL** in `apps/<app>/urls.py`:
   ```python
   path('page/', views.my_view, name='page'),
   ```

3. **Create template** in `templates/myapp/page.html`:
   ```django
   {% extends "base_shell.html" %}
   {% block content %}
   <h1>My Page</h1>
   {% endblock %}
   ```

4. **Add to nav** in `templates/partials/sidebar_nav.html`:
   ```html
   <li class="side-nav-item">
       <a href="{% url 'myapp:page' %}" class="side-nav-link">
           <span class="menu-icon"><i class="ti ti-icon"></i></span>
           <span class="menu-text">My Page</span>
       </a>
   </li>
   ```

### Call Backend API

Use `apps/api_proxy/services.py` or `apps/api_proxy/client.py`:

```python
from apps.api_proxy.services import get_backend_client

def my_view(request):
    client = get_backend_client()
    data = client.get('/api/some-endpoint/')
    return render(request, 'template.html', {'data': data})
```

## Testing

```bash
# Run tests
docker compose exec frontend python manage.py test

# Run specific test
docker compose exec frontend python manage.py test apps.ui.tests

# Theme drift tests
docker compose exec frontend python manage.py test tests.test_theme_drift
```

## Environment Variables

Required:
- `BACKEND_BASE_URL` - Backend API URL (e.g., `http://backend-api:8000`)
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (0 or 1)
- `DJANGO_ALLOWED_HOSTS` - Comma-separated hostnames

Optional:
- `FRONTEND_PORT` - Port to run on (default: 3000)
- `SESSION_COOKIE_AGE` - Session timeout in seconds

## Implementation Status

See `IMPLEMENTATION_STATUS.md` for detailed roadmap.

**Current Phase**: Phase 1 - Theme Integration & App Structure ✅  
**Next Phase**: Auth + Passkeys UI  
**Future**: Metrics Dashboard, Billing UI, Worklog Full UI

## Known Issues

1. **Backend Networking**: Frontend and backend on separate Docker networks
   - Workaround: Use `host.docker.internal` or unified compose
   
2. **Auth Pages**: django-allauth templates need theme styling

3. **Placeholder Data**: Most views return empty/stub data until backend endpoints wired

## Documentation

- `THEME_SYNC.md` - Theme update procedures
- `IMPLEMENTATION_STATUS.md` - Multi-week roadmap
- `tests/test_theme_drift.py` - Automated drift prevention
- Main docs: `/README.md`, `/ARCHITECTURE_STATUS.md`, `/CC.md`

## Support

For issues:
1. Check logs: `docker compose logs frontend`
2. Verify backend connectivity: `curl http://backend-api:8000/api/healthz/`
3. Check theme assets: `curl http://localhost:3000/static/css/app.min.css`
4. Review `CHANGE_LOG.md` for recent changes

