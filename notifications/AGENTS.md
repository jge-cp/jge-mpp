# Notifications App

Email and in-app notification system.

## Philosophy

**ALWAYS use NotificationService** - never send emails directly:
```python
# ✅ DO: Use the service
NotificationService.notify(recipients=[user], notification_type='fa_submitted', ...)

# ❌ DON'T: Send emails directly
send_mail(subject, message, from_email, [user.email])
```

**ADD new notification types** to the existing service, not new functions.

## NotificationService

```python
from notifications.services import NotificationService

# Send notification (both email + in-app)
NotificationService.notify(
    recipients=[user],
    notification_type='fa_submitted',
    title='New FA Submission',
    message='...',
    action_url='/portal/admin/fa/review/123/'
)
```

## Notification Types

| Type | Event |
|------|-------|
| `fa_submitted` | Partner submitted FA |
| `fa_pending_final` | Primary approved FA |
| `fa_approved` | Final approved FA |
| `fa_rejected` | FA rejected |
| `lot_submitted` | Partner submitted Lot |
| `lot_approved` | Lot approved |
| `lot_rejected` | Lot rejected |

## HTMX Badge Refresh

The sidebar badge auto-refreshes when notifications change:

```python
# In view after marking read
response = HttpResponse(status=204)
response['HX-Trigger'] = 'notifications-changed'
return response
```

Template listens for this trigger:
```html
<span hx-get="{% url 'notifications:badge' %}"
      hx-trigger="load, every 10s, notifications-changed from:body"
      hx-swap="outerHTML">
```

## Key Files

| File | Purpose |
|------|---------|
| `services.py` | `NotificationService.notify()` |
| `models.py` | `Notification` model |
| `views.py` | List, mark read, dropdown |
| `context_processors.py` | Injects `unread_notification_count` |

## Email Configuration

| Environment | Backend |
|-------------|---------|
| Development | Console (prints to terminal) |
| Production | Resend SMTP API |
| Testing | In-memory (`mail.outbox`) |

## Testing Notifications

### Resend Test Emails

Test users use Resend's test email format that always succeeds:
- `delivered+username@resend.dev`

Example: `delivered+partner1a@resend.dev`, `delivered+primary_inspector@resend.dev`

These show as "Delivered" in Resend dashboard even without real mailboxes.

### Test All Notifications Command

```bash
# List available notification types
python manage.py test_notifications --list

# Test all notifications
python manage.py test_notifications

# Test specific notification
python manage.py test_notifications fa_submitted

# Dry run (show what would be sent)
python manage.py test_notifications --dry-run

# On production
./scripts/prod_run.sh test_notifications
```

### Verify in Resend Dashboard

After running tests, check: https://resend.com/emails

All test emails should show "Delivered" status.

## Management Commands

| Command | Purpose |
|---------|---------|
| `test_notifications` | Test all notification types |
| `test_notifications --list` | List notification types |
| `test_notifications <type>` | Test specific notification |

