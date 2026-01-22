# Quick Testing Guide

## Start the System

```bash
cd /home/davmor/dm/s6/backend
python manage.py runserver
```

Visit: http://localhost:8000

## Test Checklist

### 1. Top Bar (Visual Check)
- [ ] "DigiMuse.ai" logo visible top-left
- [ ] User icon visible top-right
- [ ] Dropdown works on click
- [ ] Responsive on mobile (resize browser)

### 2. Gravatar (For Authenticated Users)
- [ ] Login with test user
- [ ] Avatar shows Gravatar or initial letter
- [ ] Avatar is circular and properly sized
- [ ] Dropdown shows username

### 3. Create Account Link
- [ ] As guest, see login form in canvas
- [ ] "Don't have an account?" text visible
- [ ] "Create Account" button present
- [ ] Click triggers signup in chat
- [ ] Signup flow completes successfully

### 4. Token Counting
- [ ] Send a message in chat
- [ ] Status bar shows token count update
- [ ] Count increases with each message
- [ ] Updates every 5 seconds
- [ ] Different sessions have different counts

### 5. Welcome Messages
- [ ] Guest sees: "Sign in using the form below or ask a question"
- [ ] No "type login or signup" text
- [ ] Authenticated sees: "Welcome back, [username]!"

### 6. Documentation
- [ ] `/backend/docs/USER_GUIDE.md` exists
- [ ] `/backend/docs/IMPLEMENTATION_SUMMARY.md` exists
- [ ] Both files are readable and complete

## Quick Test Commands

```bash
# Check system
cd /home/davmor/dm/s6/backend
python manage.py check

# Test templates
python manage.py shell
>>> from django.template.loader import get_template
>>> get_template('frontend/base.html')
>>> exit()

# View docs
cat docs/USER_GUIDE.md | head -50
```

## Expected Behavior

### Anonymous User Flow
1. Visits site
2. Sees login form in canvas
3. Sees "Create Account" button
4. Can click to start signup
5. Top-right shows "Guest" with user icon

### Authenticated User Flow
1. Logs in via form
2. Top-right shows avatar (Gravatar or initial)
3. Dropdown has Dashboard, Settings, Sign Out
4. Status bar shows token count
5. Token count increases with each chat message

### Token Tracking
```
Initial: Session Tokens: 0
After 1 message: Session Tokens: 45 (In: 20, Out: 25)
After 2 messages: Session Tokens: 90 (In: 40, Out: 50)
```

## Common Issues & Fixes

### Issue: Gravatar not showing
**Fix**: User needs email in database. Check:
```python
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='testuser')
>>> user.email
>>> user.email = 'test@example.com'
>>> user.save()
```

### Issue: Tokens not counting
**Check**:
1. Ollama is running
2. Session is persisting
3. Console for JavaScript errors
4. Django logs for exceptions

### Issue: Create account button not working
**Check**:
1. Chat form exists on page (id="chat-form")
2. Chat input exists (id="chat-input")
3. JavaScript loaded correctly
4. No CSP errors in console

## Success Indicators

✅ Top bar looks professional
✅ Avatar displays (Gravatar or fallback)
✅ Create account button visible and clickable
✅ Token count increases with usage
✅ Status bar updates every 5 seconds
✅ Documentation files complete
✅ No console errors
✅ No Django errors

## Performance Check

- [ ] Page loads in < 2 seconds
- [ ] Token updates don't lag
- [ ] No visible performance issues
- [ ] Responsive on mobile

---

**Ready to test!** Start the server and work through the checklist. 🚀
