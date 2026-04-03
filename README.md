# Multicam Partner Portal
**THIS IS NOT PRODUCTION REPO**
**BRANCH TESTING**


Django-based portal for managing the Multicam Partner Program

## Quick Start

### Automated Setup (Recommended)

Clone the repository and run the setup script:

```bash
git clone https://github.com/Crye-Precision/multicam-partner-portal.git
cd multicam-partner-portal
```

**Mac/Linux:**
```bash
./scripts/setup.sh --with-test-users
```

**Windows:**
```cmd
scripts\setup.bat /with-test-users
```

Then start the server:
```bash
source venv/bin/activate   # Windows: venv\Scripts\activate
python manage.py runserver
```

Visit: **http://localhost:8000**

### Manual Setup

If you prefer to run commands manually:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database (SQLite for local dev)
python manage.py migrate
python manage.py load_initial_data

# Create test users (optional)
python manage.py setup_test_users

# Create test data with sample FAs and Lots (optional)
python manage.py create_test_data         # Add to existing data
python manage.py create_test_data --clear # Clear first, then add

# Run server
python manage.py runserver
```

### Email Configuration (Optional)

By default, emails print to the console. To send real emails via Resend:

1. Create a `.env` file in the project root:
```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST_PASSWORD=your-resend-api-key-here
```

2. Get your Resend API key from https://resend.com/api-keys

**Without `.env`**: Emails print to console (good for development)  
**With `.env`**: Emails send via Resend (good for testing actual delivery)

### Test Users

If you ran setup with `--with-test-users`, use these credentials:

| Username | Password | Role | Company |
|----------|----------|------|---------|
| partner1a | partner1a123 | Partner | ACME |
| partner1b | partner1b123 | Partner | ACME |
| partner2a | partner2a123 | Partner | GLOBEX |
| partner2b | partner2b123 | Partner | GLOBEX |
| primary_inspector | primary_inspector123 | Primary Inspector | - |
| final_inspector | final_inspector123 | Final Inspector | - |
| staff | staff123 | Staff Executive | - |

**Note:** 
- **ACME**: `partner1a` and `partner1b` belong to the same company. FAs/Lots submitted by either are visible to both.
- **GLOBEX**: `partner2a` and `partner2b` belong to the same company. FAs/Lots submitted by either are visible to both.

### Test Data

Run `python manage.py create_test_data` to create sample FAs and Lots for testing:

**Company 1 (ACME):**
- FA: APPROVED (partner1a) + FA: PENDING_FINAL (partner1b)
- 2 PENDING Lots (one from each partner)

**Company 2 (GLOBEX):**
- FA: APPROVED (partner2a) + FA: PENDING_FINAL (partner2b)
- 2 PENDING Lots (one from each partner)

Use `--clear` flag to wipe existing data before creating fresh test data.

---

## MVP User Roles

| Role | Description |
|------|-------------|
| **Partner** | Submits First Articles and Lots |
| **Primary Inspector** | First FA review + all Lot reviews |
| **Final Inspector** | Final FA review only |
| **Staff** | Dashboard access (executive/finance/operations) |

## Partner Companies

Partners belong to a **PartnerCompany** for multi-user access:

- **Company Code**: Short ID used in FA/Lot prefixes (e.g., `ACME-FA-0001`)
- **Multi-User Access**: All employees in a company see the same FAs/Lots
- **Submitter Audit Trail**: Original submitter is recorded immutably (survives user deletion)

## Two-Stage FA Workflow

```
Partner submits FA → Primary Inspector → Final Inspector → Approved
                           ↓ reject           ↓ reject
                     Partner notified    Partner notified
```

## Real-Time Updates (HTMX)

The UI is designed so users generally **do not need to manually refresh**:

- **Notification bell badge** updates via HTMX polling and `notifications-changed` events.
- **Notification dropdown** loads via HTMX and polls **only while open**.
- **Dashboards / queues / detail pages** poll “live” fragments to keep state consistent for all users.

To reduce stale back-button behavior, authenticated HTML responses are served with **`Cache-Control: no-store`**.

## Documentation

| File | Description |
|------|-------------|
| [PROJECT_OVERVIEW.md](Docs/PROJECT_OVERVIEW.md) | MVP scope, user roles, workflows, models |
| [DEVELOPMENT.md](Docs/DEVELOPMENT.md) | Setup, testing, troubleshooting |
| [DEPLOYMENT.md](Docs/DEPLOYMENT.md) | Railway production deployment |

## Key URLs

| URL | Description |
|-----|-------------|
| `/` | Homepage |
| `/accounts/login/` | Login |
| `/portal/dashboard/partner/` | Partner dashboard |
| `/portal/admin/dashboard/` | Inspector dashboard |
| `/portal/admin/staff/` | Staff dashboard |
| `/admin/` | Django admin |

## Technology Stack

- **Backend**: Django 5.x, PostgreSQL (prod), SQLite (dev)
- **Frontend**: HTMX, Alpine.js, Tailwind CSS
- **Infrastructure**: Railway, WhiteNoise, Resend
- **Admin**: Django Unfold

## Project Structure

```
multicam-partner-portal/
├── config/          # Django settings
├── accounts/        # User auth & profiles
├── inspections/     # FA & Lot workflows
├── notifications/   # Email & in-app notifications
├── dashboard/       # Role-based dashboards
├── core/            # Public pages & shared models
├── templates/       # HTML templates
├── scripts/         # Setup scripts
└── Docs/            # Documentation
```

## License

Proprietary - Multicam Partner Program

## Useful Commands

```bash
#Compiles src/css/input.css → static/css/output.css
npm run build:css
```

```bash
# Backfill TEMP COLOR for any Multicam variants missing colors
python manage.py backfill_variant_temp_colors

# Run workflow + notifications tests (covers FA/Lot routing + notifications)
python manage.py test inspections.tests_workflow notifications.tests --verbosity=2
```
