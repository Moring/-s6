# Django Frontend - AfterResume Chat Interface

## Overview

The Django frontend provides a conversational UI for AfterResume with a split-panel layout:
- **Top Panel**: Chat interface for user interaction
- **Bottom Panel**: Canvas for displaying structured results (dashboards, settings, etc.)
- **Footer**: Status bar with token counts and reserve balance

## Architecture

### Technologies
- **Django Templates**: Server-side rendering
- **HTMX**: Reactive UI updates without full page reloads
- **Bootstrap 5**: Responsive design from theme assets
- **Session-based Auth**: Django authentication with multi-step flows

### Directory Structure
```
frontend/
├── __init__.py
├── apps.py
├── views.py              # View logic for chat, canvas, status
├── urls.py               # URL routing
├── tests.py              # Pytest tests
├── templates/
│   └── frontend/
│       ├── base.html           # Base layout with assets
│       ├── index.html          # Main split-panel interface
│       └── partials/
│           ├── chat_message.html    # Single message
│           ├── chat_response.html   # User/bot pair
│           ├── dashboard_card.html  # Dashboard display
│           ├── settings_card.html   # Settings form
│           ├── error_card.html      # Error display
│           ├── status_bar.html      # Status updates
│           └── chat_history.html    # Message history
└── static/
    └── assets/                # Theme assets (CSS, JS, images)
```

## Chat Commands

### Logged Out
- `login` - Start login flow
- `signup` - Start signup flow (requires invite passkey)
- `help` - Show available commands

### Logged In
- `dashboard` - View dashboard card on canvas
- `worklogs` - Manage work logs (coming soon)
- `skills` - View skills library (coming soon)
- `reports` - Generate reports (coming soon)
- `settings` - View/edit settings (coming soon)
- `logout` - Sign out
- `help` - Show available commands

### Admin Only
- `admin create-passkey` - Create invite passkey (coming soon)
- `admin list-users` - List all users (coming soon)
- `admin disable-user <username>` - Disable user account (coming soon)

## Authentication Flows

### Signup Flow
1. User types `signup`
2. System prompts for username
3. System prompts for password
4. System prompts to confirm password
5. System prompts for invite passkey
6. System validates:
   - Passkey exists, is active, not expired, not used
   - Username is unique
   - Password meets requirements
7. On success:
   - Creates User
   - Auto-creates Tenant (via signal)
   - Auto-creates UserProfile (via signal)
   - Marks passkey as used
   - Logs user in automatically
   - Shows welcome message

### Login Flow
1. User types `login`
2. System prompts for username
3. System prompts for password
4. System authenticates
5. On success:
   - Logs user in
   - Shows welcome message
   - Dashboard available
6. On failure:
   - Shows generic error (no user enumeration)
   - Restarts flow

### Password Masking
- Up to 8 characters: shows one star per character (★★★★★★★★)
- More than 8 characters: all stars flash when typing (prevents length enumeration)
- Visual feedback without revealing actual length

## HTMX Integration

### Form Submission
```html
<form hx-post="{% url 'frontend:chat_send' %}" 
      hx-target="#chat-messages" 
      hx-swap="beforeend">
```

### Polling
```html
<div hx-get="{% url 'frontend:status_bar' %}" 
     hx-trigger="every 5s" 
     hx-swap="innerHTML">
```

### Indicators
```html
<div id="working-indicator" class="htmx-indicator">
    <span></span><span></span><span></span>
</div>
```

## Views

### IndexView
- Main application entry point
- Renders split-panel layout
- Shows welcome message based on auth state

### ChatSendView
- Handles all chat message submissions
- Manages multi-step authentication flows
- Routes commands to appropriate handlers
- Returns HTMX-compatible partial templates

### DashboardCardView (LoginRequired)
- Renders dashboard statistics
- Shows worklog count, skill count, reserve balance
- Loads into canvas area

### SettingsCardView (LoginRequired)
- Renders user settings form
- Displays username, email (readonly for now)
- Update functionality coming soon

### StatusBarView
- Returns current token counts and reserve balance
- Different display for authenticated/anonymous users
- Called via HTMX polling every 5 seconds

## Session State Management

Multi-step flows use Django session:
```python
request.session['auth_flow'] = 'login'  # or 'signup'
request.session['auth_step'] = 'username'  # or 'password', 'passkey', etc.
request.session['signup_data'] = {}  # temporary form data
```

State cleared on:
- Successful completion
- Error/restart
- User logout

## Testing

Run tests:
```bash
cd backend
python -m pytest frontend/tests.py -v
```

All tests passing:
- Index rendering (anonymous/authenticated)
- Chat commands (login, signup, help)
- Authentication requirements
- Canvas card access control
- Status bar rendering

## Development

### Adding New Commands
1. Update `ChatSendView.post()` to recognize command
2. Create handler method (e.g., `_handle_new_command()`)
3. Return appropriate template response
4. Add tests

### Adding New Canvas Cards
1. Create template in `partials/`
2. Create view class
3. Add URL route
4. Update chat command to trigger canvas load

### Customizing Theme
- Edit CSS in `static/assets/css/`
- Modify templates in `templates/frontend/`
- Update base.html for global changes

## Security

- CSRF protection enabled
- Session-based authentication
- Generic error messages (no user enumeration)
- Password masking
- Invite-only signup
- Tenant isolation
- Rate limiting ready

## Future Enhancements

- AI chat integration with LLM agents
- Admin command handlers
- Password reset email flow
- Chat history persistence
- More canvas card types
- Keyboard shortcuts
- File upload support
- Markdown rendering
- Notification system
- Dark mode
- Mobile optimization

## Troubleshooting

### Static assets not loading
```bash
python manage.py collectstatic --noinput
```

### HTMX not working
- Check browser console for errors
- Verify HTMX CDN is accessible
- Check CSRF token in forms

### Session state lost
- Check SESSION_COOKIE_AGE setting
- Verify session backend is configured
- Clear browser cookies and try again

### Tests failing
- Ensure test database is clean: `pytest --create-db`
- Check for conflicting signals creating duplicate data
- Verify fixtures use unique identifiers

## Contributing

When adding features:
1. Follow Django best practices
2. Use HTMX for interactivity
3. Add tests for new functionality
4. Update this README
5. Add entry to CHANGE_LOG.md
