# Quick Start Guide: Django Frontend with Chat Interface

## Prerequisites
- AfterResume backend running (Django + Postgres + dependencies)
- Python virtual environment activated
- Admin user created

## Step 1: Verify Setup

```bash
cd /home/davmor/dm/s6/backend

# Check Django configuration
python manage.py check

# Run frontend tests
python -m pytest frontend/tests.py -v
```

## Step 2: Create Invite Passkey

Users need an invite passkey to sign up. Create one via Django shell:

```bash
python manage.py shell
```

```python
from apps.invitations.models import InvitePasskey
from datetime import timedelta
from django.utils import timezone

# Create a passkey valid for 30 days
passkey = InvitePasskey.objects.create(
    key="WELCOME2026",
    expires_at=timezone.now() + timedelta(days=30),
    is_active=True,
    max_uses=10,
    notes="Test passkey for initial users"
)
print(f"Created passkey: {passkey.key}")
```

## Step 3: Start Django Server

```bash
python manage.py runserver
```

## Step 4: Test the Chat Interface

Open your browser to: http://localhost:8000/

### Try These Commands:

**As Anonymous User:**
1. Type: `help` - See available commands
2. Type: `signup` - Start signup flow
   - Enter username: `alice`
   - Enter password: `SecurePass123!`
   - Confirm password: `SecurePass123!`
   - Enter passkey: `WELCOME2026`
   - You'll be logged in automatically!

3. Type: `dashboard` - See your dashboard
4. Type: `help` - See authenticated commands
5. Type: `logout` - Sign out

**Login Flow:**
1. Type: `login`
2. Enter username: `alice`
3. Enter password: `SecurePass123!`
4. Welcome back!

## Step 5: Verify Features

### Status Bar (Bottom)
- Should show token counts
- Should show reserve balance
- Updates every 5 seconds

### Chat Features
- Enter sends message
- Shift+Enter adds new line
- Working indicator shows during requests
- Auto-scrolls to latest message

### Canvas (Bottom Panel)
- Type `dashboard` when logged in
- Should show stats cards
- Interactive, loads via HTMX

## Common Commands Reference

### Anonymous
- `login` - Sign in
- `signup` - Create account
- `help` - Show commands

### Authenticated
- `dashboard` - View dashboard
- `settings` - View settings
- `logout` - Sign out
- `help` - Show commands

## Troubleshooting

### "Could not connect to server"
- Ensure Django server is running: `python manage.py runserver`
- Check port 8000 is not in use

### "Invalid passkey"
- Create a new passkey (Step 2)
- Check passkey hasn't expired
- Verify passkey hasn't been used max_uses times

### Chat not responding
- Check browser console for errors
- Verify HTMX is loading (check Network tab)
- Check Django logs for errors

### Status bar not updating
- Check HTMX polling is working (Network tab should show requests every 5s)
- Verify user is authenticated for balance display

## Next Steps

### For Developers
1. Read `backend/frontend/README.md` for architecture details
2. Look at `backend/frontend/views.py` to understand chat logic
3. Check `backend/frontend/templates/frontend/` for UI components
4. Add new commands by extending `ChatSendView`

### For Users
1. Explore available commands with `help`
2. Create work logs (feature coming soon)
3. View skills (feature coming soon)
4. Generate reports (feature coming soon)

## Testing

Run comprehensive frontend tests:

```bash
cd /home/davmor/dm/s6/backend
python -m pytest frontend/tests.py -v

# Expected output:
# ============ 12 passed, 1 warning in 4.07s =============
```

## Production Deployment

See `CHANGE_LOG.md` section "Human TODOs" for production checklist:
- Configure email for password reset
- Set up static file serving
- Configure session security
- Set ALLOWED_HOSTS
- Enable rate limiting
- Add monitoring

## Support

- Architecture: See `ARCHITECTURE.md`
- Changes: See `CHANGE_LOG.md`
- Admin Guide: See `ADMIN_GUIDE.md`
- Issues: Check Django logs and browser console

---

**Congratulations!** You now have a working Django frontend with conversational chat interface! 🎉
