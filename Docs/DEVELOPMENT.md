# Development Guide

Complete guide for local development, testing, and contributing.

## Quick Start (5 Minutes)

### 1. Setup

```bash
# Activate virtual environment
source venv/bin/activate  # Windows: venv\Scripts\activate

# Run migrations
python manage.py migrate

# Load initial data
python manage.py load_initial_data

# Create superuser
python manage.py createsuperuser
```

**Note:** No `.env` file needed! Django uses defaults for local development.

### 2. Start Server

```bash
python manage.py runserver
```

Visit: **http://localhost:8000**

### 3. Test Login

1. Go to: http://localhost:8000/admin/
2. Login with superuser credentials
3. You should see Django Unfold admin interface

---

## Complete Setup Instructions

### Prerequisites

- Python 3.11+
- Git
- Railway account (for production deployment)
- Resend account (for production email)

### Initial Setup

```bash
# Clone repository
git clone <your-repo-url>
cd MCP-3

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Load initial data (camouflage types)
python manage.py load_initial_data

# Create superuser
python manage.py createsuperuser
```

### Environment Configuration

**No `.env` file needed for local development!**

Django uses sensible defaults:
- **Database**: SQLite (`db.sqlite3`)
- **Email**: Console backend (prints to terminal)
- **Debug**: `True` (shows detailed errors)
- **Secret Key**: Uses default (fine for local dev)

If you want to customize settings, create `.env` file (see `.env.example` for reference).

### Import Partners

```bash
# Dry-run first to see what would be imported
python manage.py import_printers printers_import.csv --dry-run

# Actually import
python manage.py import_printers printers_import.csv
```

---

## Testing Guide

### Automated Tests

Run all tests:

```bash
# Run all tests
python manage.py test inspections.tests inspections.tests_workflow notifications.tests

# Run workflow tests only (FA, Lot, notifications)
python manage.py test inspections.tests_workflow --verbosity=2

# Run with coverage (if installed)
coverage run manage.py test && coverage report
```

**78 tests** cover:
- FA model and workflow tests
- Two-stage review workflow
- Lot submission and review
- Email notifications (7 types)
- In-app notifications
- Dashboard access by role

### Quick Test Checklist

- [ ] Server starts without errors
- [ ] Can access homepage
- [ ] Can login as admin
- [ ] Can create partner user
- [ ] Can submit FA as Partner
- [ ] Can review FA (primary) as Primary Inspector
- [ ] Can review FA (final) as Final Inspector
- [ ] Can submit Lot (after FA approved)
- [ ] Can review Lot as Primary Inspector
- [ ] Dashboards show correct stats
- [ ] Email notifications appear in console
- [ ] In-app notification bell shows count

### Test 1: User Creation

**Create Partner User via Admin:**
1. Admin → Users → Add User
2. Username: `partner1`
3. Email: `partner1@test.com`
4. Password: `test123`
5. Save
6. Admin → User Profiles → Add User Profile
7. Link to user, set `user_functionality='partner'`, `status='active'`

### Test 2: FA Submission Workflow

1. **Login as Partner:**
   - Go to: http://localhost:8000/accounts/login/
   - Login with partner credentials

2. **Submit First Article:**
   - Go to: http://localhost:8000/portal/fa/submit/
   - Fill form and submit
   - ✅ Should see success message with FA ID

3. **Check Email:**
   - Check terminal where server is running
   - Email should be printed to console

### Test 3: Two-Stage Inspector Review

1. **Create Primary Inspector:**
   - Admin → Users → Create user
   - Admin → User Profiles → Set `user_functionality='admin'`, `admin_role='primary_inspector'`

2. **Create Final Inspector:**
   - Admin → Users → Create user
   - Admin → User Profiles → Set `user_functionality='admin'`, `admin_role='final_inspector'`

3. **Primary Review:**
   - Login as Primary Inspector
   - Go to: http://localhost:8000/portal/admin/fa/queue/primary/
   - Review and approve → FA moves to `pending_final`

4. **Final Review:**
   - Login as Final Inspector
   - Go to: http://localhost:8000/portal/admin/fa/queue/final/
   - Review and approve → FA is fully approved

### Test 4: Lot Submission

1. Login as Partner
2. Go to: http://localhost:8000/portal/lot/submit/
3. Select Approved FA (from dropdown)
4. Fill additional fields and submit
5. Login as Primary Inspector to review and approve

### Test 5: Dashboards

- **Partner Dashboard**: http://localhost:8000/portal/dashboard/partner/
- **Inspector Dashboard**: http://localhost:8000/portal/admin/dashboard/
- **Staff Dashboard**: http://localhost:8000/portal/admin/staff/

---

## Pre-Commit Checklist

### Quick System Checks

```bash
# 1. Run Django checks
python manage.py check

# 2. Verify migrations are up to date
python manage.py makemigrations --check

# 3. Test database connection
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('✅ Database connected')"
```

### Critical Tests Before Commit

- [ ] `python manage.py check` passes
- [ ] Login/logout works
- [ ] Admin accessible
- [ ] FA/Lot workflows tested
- [ ] No migration issues

---

## Key URLs

### Public
- `/` - Homepage
- `/accounts/login/` - Login

### Partner Portal
- `/portal/dashboard/partner/` - Partner dashboard
- `/portal/fa/submit/` - Submit FA
- `/portal/fa/list/` - FA history
- `/portal/lot/submit/` - Submit Lot
- `/portal/lot/list/` - Lot history

### Inspector Portal
- `/portal/admin/dashboard/` - Inspector dashboard
- `/portal/admin/fa/queue/primary/` - Primary FA queue
- `/portal/admin/fa/queue/final/` - Final FA queue
- `/portal/admin/lot/queue/` - Lot queue

### Staff Portal
- `/portal/admin/staff/` - Staff dashboard

### Admin
- `/admin/` - Django admin

---

## Troubleshooting

### "ModuleNotFoundError"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "No such table" errors
```bash
python manage.py migrate
```

### Port 8000 already in use
```bash
python manage.py runserver 8001
```

### Static files not loading
```bash
python manage.py collectstatic
```

### Can't login
- Make sure user exists: `python manage.py createsuperuser`
- Check user has UserProfile: Admin → User Profiles
- Reset password if needed

---

## Management Commands

| Command | Description |
|---------|-------------|
| `python manage.py setup_test_users` | Create test users (partner, primary_inspector, final_inspector, staff) |
| `python manage.py load_initial_data` | Load camouflage types and variant colors |
| `python manage.py import_printers <csv>` | Import partners from CSV |
| `python manage.py import_historical_fas <csv>` | Import historical FA data |
| `python manage.py import_historical_lots <csv>` | Import historical Lot data |
| `python manage.py verify_migration` | Verify data migration |

### Test Users (for development)

```bash
python manage.py setup_test_users
```

Creates these users with passwords `{username}123`:

| Username | Role |
|----------|------|
| partner | Partner |
| primary_inspector | Primary Inspector |
| final_inspector | Final Inspector |
| staff | Staff Executive |

---

## Local vs Production Differences

| Feature | Local (Development) | Production (Railway) |
|---------|-------------------|----------------------|
| Database | SQLite (db.sqlite3) | PostgreSQL |
| Email | Console (prints to terminal) | Resend API (actual emails) |
| Static Files | Django dev server | WhiteNoise |
| Debug | True (shows errors) | False (hides errors) |
| URL | localhost:8000 | your-domain.com |

