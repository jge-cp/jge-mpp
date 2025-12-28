# Multicam Partner Portal

Django-based portal replacing 3,000+ Google Sheets for the Multicam Partner Program. Handles First Article (FA) submissions and Lot Acceptances with a two-stage inspection workflow.

## Code Philosophy (LEVER)

Before writing new code, follow this framework:

**L**everage - Use existing patterns first (managers, decorators, partials)
**E**xtend - Add to existing code vs. creating new files
**V**erify - Run existing tests, don't break working features
**E**liminate - Remove duplication, use shared components
**R**educe - Minimize complexity, fewer lines = fewer bugs

**Ask yourself:**
1. Does a model manager already filter this? → Use `.for_user(profile)`
2. Does a decorator already check this? → Use `@partner_required`
3. Does an HTMX partial already render this? → Use `_results.html`
4. Can I add a field vs. a new table? → Extend existing models

## Tech Stack
- **Backend**: Django 5.x, PostgreSQL (prod), SQLite (dev)
- **Frontend**: HTMX, Alpine.js, Tailwind CSS, Flowbite
- **Admin**: Django Unfold | **Email**: Resend | **Hosting**: Railway

## MVP User Roles

| Role | Code | Description |
|------|------|-------------|
| Partner | `user_functionality='partner'` | Submits FAs and Lots |
| Primary Inspector | `admin_role='primary_inspector'` | First FA review + all Lot reviews |
| Final Inspector | `admin_role='final_inspector'` | Final FA review only |
| Staff | `admin_role='staff_executive'` etc. | Dashboard access |

## Key Models
- `accounts.UserProfile` - Extended user with roles
- `inspections.FirstArticleInspection` - FA with two-stage review
- `inspections.LotAcceptance` - Lot submissions (single-stage)
- `notifications.Notification` - Email and in-app notifications

## Universal Conventions

**Naming (IMPORTANT):**
- Use "Partner" not "Printer"
- Use "Primary Inspector" and "Final Inspector" (not company names)
- Use "Staff" for executive/finance/operations users

**Display Names:**
- FA: `{fabric_style} - {multicam_variant} - {fa_lot_number}`
- Lot: `{fabric_style} - {multicam_variant} - {lot_lot_number}`

## Don'ts
- Don't use "printer" terminology
- Don't use company-specific names (1947, Crye)
- Don't add RM Supplier, FP Supplier, Government roles (removed from MVP)
- Don't modify `.env` without asking
- Don't create docs at root - put in `Docs/`

## JIT Index (Sub-AGENTS.md Files)

| Directory | Purpose | See |
|-----------|---------|-----|
| `accounts/` | Auth, decorators, profile management | [accounts/AGENTS.md](accounts/AGENTS.md) |
| `inspections/` | FA/Lot models, workflows, reviews | [inspections/AGENTS.md](inspections/AGENTS.md) |
| `dashboard/` | Dashboard views, routing | [dashboard/AGENTS.md](dashboard/AGENTS.md) |
| `templates/` | Tailwind, HTMX, Alpine patterns | [templates/AGENTS.md](templates/AGENTS.md) |
| `notifications/` | Notification service | [notifications/AGENTS.md](notifications/AGENTS.md) |
| `Docs/` | Documentation standards | [Docs/AGENTS.md](Docs/AGENTS.md) |

## Quick Find Commands

```bash
# Find a view function
rg -n "^def " */views.py

# Find a model
rg -n "^class.*Model" */models.py

# Find a decorator usage
rg -n "@partner_required|@inspector_required" */views.py

# Find HTMX endpoints
rg -n "hx-get|hx-post" templates/

# Find template by name
find templates -name "*.html" | xargs grep -l "pattern"
```

## Pre-Commit Checks

```bash
python manage.py check
python manage.py test
npm run build:css
```

## Railway Deployment

### Run Commands on Production
```bash
# Use the prod_run.sh script (sets DATABASE_URL)
./scripts/prod_run.sh shell
./scripts/prod_run.sh migrate
./scripts/prod_run.sh reset_all_data
./scripts/prod_run.sh test_notifications
```

### Checking Logs
```bash
# Railway logs stream continuously - use timeout
railway logs 2>&1 &
sleep 15
kill %1 2>/dev/null

# Or get snapshot of recent logs
railway logs --num 50
```

### Important: railway run vs Railway Container
- `railway run <cmd>` runs LOCALLY with Railway env vars injected
- The actual Railway container runs INSIDE Railway's infrastructure
- Network connectivity can differ between the two!

### Get/Set Railway Environment Variables
```bash
railway variables                    # Show all
railway variables | grep EMAIL       # Filter
railway variables --set "KEY=value"  # Set new value
```

## Email Configuration (Resend HTTP API)

### Backend
Uses Resend HTTP API (not SMTP) for reliability in containers:
- Backend: `notifications.backends.ResendEmailBackend`
- API Key: `RESEND_API_KEY` (or `EMAIL_HOST_PASSWORD`)

### Local Development
Override to console backend in `.env`:
```
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Test Email Format (Resend)
All test users use Resend's test email format - always shows "Delivered":
```
delivered+<username>@resend.dev
```

Examples:
- `delivered+partner1a@resend.dev`
- `delivered+primary_inspector@resend.dev`
- `delivered+mcadmin@resend.dev`

### Test Notifications
```bash
# Trigger all notification types (uses test data)
./scripts/prod_run.sh test_notifications

# Check Resend dashboard
https://resend.com/emails
```

### Production (future)
- Verify `multicampattern.com` domain in Resend
- Or switch to MS Exchange Graph API
- Change is just environment variable

