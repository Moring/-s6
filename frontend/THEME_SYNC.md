# Theme Sync Documentation

## Overview

The AfterResume frontend uses the **Inspinia** (SEED) Bootstrap 5 admin theme as the visual foundation. This document describes the mapping between the theme source and Django templates to prevent drift and enable safe reruns.

## Theme Source

**Original Location**: `/HTML/Seed/dist/`  
**Status**: INPUT ONLY - This directory will be deleted after migration is complete.

## Django Migration Mapping

### Static Assets

| Theme Source | Django Target | Status |
|--------------|---------------|--------|
| `HTML/Seed/dist/assets/css/*` | `frontend/static/css/*` | ✅ Migrated |
| `HTML/Seed/dist/assets/js/*` | `frontend/static/js/*` | ✅ Migrated |
| `HTML/Seed/dist/assets/images/*` | `frontend/static/images/*` | ✅ Migrated |

### Template Mapping

| Theme HTML | Django Template | Purpose |
|------------|-----------------|---------|
| `layouts-scrollable.html` | `base_shell.html` | Master layout |
| (sidebar section) | `partials/sidebar_nav.html` | Navigation menu |
| (topbar section) | `partials/topbar_status.html` | Status bar + user menu |
| (footer section) | `partials/footer.html` | Footer |
| `index.html` | `ui/dashboard_new.html` | Dashboard |

## Rerun Procedure

When rerunning theme sync (e.g., to update theme version):

1. **Backup current**: `cp -r frontend/static frontend/static.backup`
2. **Sync assets**: `rsync -av HTML/Seed/dist/assets/ frontend/static/`
3. **Review templates**: Compare `layouts-scrollable.html` with `base_shell.html`
4. **Test**: Run drift tests (see below)
5. **Commit**: If tests pass, commit changes

## Drift Prevention

### Automated Tests

Location: `frontend/tests/test_theme_drift.py`

Tests enforce:
- No references to `/HTML/` directory in templates
- All templates extend `base_shell.html`
- Required theme CSS/JS classes present
- Static references use `{% static %}`

Run: `pytest frontend/tests/test_theme_drift.py`

### Manual Checklist

After any template changes, verify:

- [ ] Sidebar navigation renders correctly
- [ ] Topbar status bar updates via HTMX
- [ ] Footer appears on all pages
- [ ] Mobile responsive menu works
- [ ] Theme toggle (if enabled) works
- [ ] All icon classes (`ti ti-*`) render
- [ ] Bootstrap components work (modals, dropdowns, alerts)

## Theme Components Used

### CSS Files
- `vendors.min.css` - Bootstrap 5 + dependencies
- `app.min.css` - Theme-specific styles

### JavaScript Files
- `vendors.min.js` - jQuery, Bootstrap, simplebar
- `app.js` - Theme initialization
- `config.js` - Theme config (light/dark mode)

### Icon Font
- **Tabler Icons** (`ti ti-*` classes)

### Key Theme Classes

**Layout**:
- `.wrapper` - Main wrapper
- `.sidenav-menu` - Sidebar container
- `.content-page` - Main content area
- `.topbar` - Top navigation bar

**Components**:
- `.side-nav` - Sidebar menu list
- `.side-nav-item` - Menu items
- `.card` - Card component
- `.badge-soft-*` - Soft color badges

## Customization Notes

### Logo
Replace these files:
- `static/images/logo.png` - Light mode logo
- `static/images/logo-black.png` - Dark mode logo
- `static/images/logo-sm.png` - Small logo
- `static/images/favicon.ico` - Favicon

### Colors
Theme uses Bootstrap 5 color system:
- Primary: Blue
- Success: Green
- Warning: Yellow
- Danger: Red
- Info: Cyan

Override in custom CSS if needed.

### Menu Structure

Sidebar menu is defined in `partials/sidebar_nav.html`:
- Uses `{% if user.is_staff %}` for admin-only sections
- Active state: `{% if 'worklog' in request.path %}active{% endif %}`
- Icons: Tabler Icons (`ti ti-*`)

## Known Limitations

1. **Theme Version**: Using Inspinia/SEED v4.0.1 (check with vendor for updates)
2. **Customizations**: Any theme customizations should be in separate CSS file (`custom.css`)
3. **JavaScript**: Theme JS expects jQuery - do not remove it
4. **HTMX**: Coexists with theme JS, no conflicts detected

## Troubleshooting

### Icons Not Showing
- Check `vendors.min.css` is loaded
- Tabler Icons are included in vendor CSS

### Sidebar Not Working
- Check `app.js` is loaded after vendors
- Check `.sidenav-menu` element exists

### HTMX Not Updating
- Check browser console for errors
- Verify endpoint returns HTML (not JSON)
- Check HTMX script is loaded

## Migration Verification

Run this after any theme update:

```bash
# 1. Check no HTML directory references
grep -r "HTML/" frontend/templates/ && echo "FAIL: Found HTML refs" || echo "PASS"

# 2. Check static tag usage
grep -r "static/" frontend/templates/ | grep -v "{% static" && echo "FAIL: Found hardcoded static" || echo "PASS"

# 3. Run tests
pytest frontend/tests/test_theme_drift.py -v

# 4. Visual check
docker compose -f frontend/docker-compose.yml restart frontend
# Open http://localhost:3000 and verify rendering
```

## Contact

For theme-related issues:
- Theme Vendor: WebAppLayers / WrapBootstrap
- Internal: See frontend team lead

---

**Last Updated**: 2025-12-31  
**Theme Version**: Inspinia/SEED 4.0.1  
**Django Version**: 5.x
