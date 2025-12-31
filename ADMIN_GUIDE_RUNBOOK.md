# AfterResume Admin Guide & Runbook

**Version**: 1.0  
**Last Updated**: 2025-12-31

---

## Quick Start

### Start System
```bash
task up
```

### Check Health
```bash
curl http://localhost:8000/api/healthz/  # Backend
curl http://localhost:3000/health/       # Frontend
```

### Default Admin Login
- **URL**: http://localhost:3000/accounts/login/
- **Username**: `admin`
- **Password**: `admin123` (⚠️ CHANGE IN PRODUCTION)

---

## User Management

### Create Invite Passkey

Users cannot sign up without an invite passkey.

**Via Django Shell:**
```bash
docker compose -f backend/docker-compose.yml exec backend-api python manage.py shell
```

```python
from apps.invitations.models import InvitePasskey
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

admin = User.objects.get(username='admin')
raw_key = InvitePasskey.generate_key()
hashed = InvitePasskey.hash_key(raw_key)

passkey = InvitePasskey.objects.create(
    key=hashed,
    raw_key=raw_key,
    created_by=admin,
    expires_at=timezone.now() + timedelta(days=7),
    notes="Invite for new user"
)

print(f"PASSKEY: {raw_key}")
```

**Share this passkey with the user** - they'll enter it at signup.

---

## Billing & Reserve

### Check Reserve Balance

```bash
curl -X GET http://localhost:8000/api/billing/reserve/balance/ \
  -H "Authorization: Token <user-token>"
```

### Manual Credit (Admin Only)

```bash
curl -X POST http://localhost:8000/api/billing/admin/reserve/adjust/ \
  -H "Authorization: Token <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "amount_cents": 10000,
    "reason": "Promotional credit"
  }'
```

---

## Troubleshooting

### Frontend Can't Reach Backend

```bash
# Check network
docker network inspect afterresume-net

# Test connectivity
docker exec afterresume-frontend curl -s http://backend-api:8000/api/healthz/
```

### Jobs Not Running

```bash
# Check worker logs
docker logs afterresume-backend-worker --tail=50

# Restart worker
docker compose -f backend/docker-compose.yml restart backend-worker
```

### Database Issues

```bash
# Run migrations
task migrate

# Access DB shell
task dbshell
```

---

## Backup & Recovery

### Database Backup
```bash
docker exec afterresume-postgres pg_dump -U afterresume afterresume > backup.sql
```

### Restore
```bash
docker exec -i afterresume-postgres psql -U afterresume afterresume < backup.sql
```

---

## Security Checklist (Production)

- [ ] Change default admin password
- [ ] Set `DEBUG=0` in .env
- [ ] Generate strong `SECRET_KEY`
- [ ] Configure HTTPS
- [ ] Set `SESSION_COOKIE_SECURE=True`
- [ ] Configure firewall (only 80/443 public)
- [ ] Set up Stripe live keys + webhook
- [ ] Configure email provider
- [ ] Enable rate limiting (TODO)
- [ ] Set up monitoring + alerts

---

## Useful Commands

```bash
# Services
task up / down / restart / status / logs

# Shell Access
task bash-backend       # Container shell
task shell-backend      # Django shell
task dbshell            # Database shell

# Database
task migrate            # Run migrations
task makemigrations     # Create migrations

# Testing
task test-backend       # Run backend tests
```

---

## Support

For issues, check:
1. `docker logs <container-name>` for errors
2. Backend health: `http://localhost:8000/api/healthz/`
3. IMPLEMENTATION_PROGRESS.md for known limitations

