# Frontend Theme Integration & Multi-Feature Implementation

## Implementation Status

**Date Started**: 2025-12-31
**Scope**: Massive multi-week project covering:
1. Theme Migration & Frontend GUI Shell
2. Authentication + Passkey Invites System  
3. Executive Metrics Dashboard
4. Payments & Billing UI
5. Worklog UI with AI integration

## Phase 1: Theme Migration & GUI Shell ✅ (IN PROGRESS)

### Completed
- [x] Copied theme assets from HTML/Seed/dist/assets/ to frontend/static/
- [x] Created base_shell.html with proper Django template structure
- [x] Created partials/sidebar_nav.html with dynamic menu
- [x] Created partials/topbar_status.html with HTMX status bar
- [x] Created partials/footer.html
- [x] Created comprehensive dashboard template
- [x] Updated UI views for index and dashboard separation

### In Progress
- [ ] Create template drift prevention tests
- [ ] Create THEME_SYNC.md documentation
- [ ] Wire up all route guards (auth-by-default)
- [ ] Implement status bar backend endpoint
- [ ] Create remaining app templates

## Phase 2: Authentication & Passkey System

### Backend (Already Exists)
- [x] Models: Tenant, UserProfile, InvitePasskey
- [x] Signals for auto-profile creation
- [x] Passkey validation logic

### Frontend (To Do)
- [ ] Signup form with passkey field
- [ ] Login page styled with theme
- [ ] Password reset flow
- [ ] Profile page
- [ ] Admin passkey management UI

## Phase 3: Executive Metrics Dashboard

### Backend (To Do)
- [ ] MetricsSnapshot model
- [ ] MetricsConfig model
- [ ] Scheduled compute job (Huey)
- [ ] Admin metrics API endpoints
- [ ] Cohort retention calculation
- [ ] DAU/WAU/MAU calculation

### Frontend (To Do)
- [ ] Admin metrics dashboard page
- [ ] Charts integration (lightweight)
- [ ] Filters UI
- [ ] Auto-refresh with HTMX
- [ ] CSV export button

## Phase 4: Billing & Payments UI

### Backend (Already Exists)
- [x] BillingProfile, ReserveAccount, RateLedgerEntry models
- [x] Stripe integration tools
- [x] Webhook handlers
- [x] Cost computation tools

### Frontend (To Do)
- [ ] Billing settings page
- [ ] Reserve balance display
- [ ] Top-up button (Stripe Checkout)
- [ ] Ledger history view
- [ ] Admin billing dashboard

## Phase 5: Worklog UI

### Backend (Partially Exists)
- [x] Worklog model
- [ ] Smart defaults service
- [ ] Quick add API
- [ ] Search/filter API
- [ ] Evidence/attachment API
- [ ] Entry enhancement DAG

### Frontend (To Do)
- [ ] Worklog index with timeline/table
- [ ] Quick add drawer
- [ ] Entry detail/edit form
- [ ] Attachments uploader
- [ ] Search/filter UI
- [ ] Evidence library view

## Critical Path Implementation Strategy

Due to the massive scope (literally 4-6 weeks of full-time development), I'm implementing:

1. **Core Shell** (Theme + Navigation + Status Bar) - CRITICAL
2. **Auth Flow** (Login/Signup with Passkeys) - CRITICAL  
3. **Minimal Billing UI** (Balance + Top-up) - HIGH
4. **Worklog Minimal** (Index + Quick Add) - HIGH
5. **Everything Else** - Document as TODOs with clear patterns

## Remaining Work Estimate

- **Theme completion**: 2-3 days
- **Auth + Passkeys**: 3-5 days
- **Metrics Dashboard**: 4-6 days (backend + frontend)
- **Billing UI**: 2-3 days
- **Worklog Full UI**: 5-7 days
- **Testing + Polish**: 3-4 days

**Total**: ~20-30 days of focused development

## Implementation Notes

### Theme Assets
- All CSS/JS/images copied to frontend/static/
- References updated to use {% static %}
- simplebar, Tabler Icons included
- Bootstrap 5 theme

### Route Guards
- All pages require auth by default (decorator on views)
- Only public: /accounts/login, /accounts/signup, /health/
- Redirect back to requested page after login

### HTMX Patterns
- Status bar: hx-get + hx-trigger="load, every 30s"
- Forms: hx-post + hx-swap
- Live updates: polling with backoff on errors

### Admin Menu
- Only visible if user.is_staff
- Routes also protected by @staff_member_required
- Includes: System, Metrics, Billing Admin, Passkeys

## Next Immediate Steps

1. Wire up status bar endpoint
2. Create login/signup templates
3. Create worklog index
4. Create billing settings page
5. Run tests and fix issues
6. Document Human TODOs

