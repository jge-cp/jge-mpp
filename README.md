# Multicam Partner Portal

Django-based portal for managing the Multicam Partner Program, replacing 3,000+ Google Sheets with a unified FA/Lot submission and review workflow.

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

# Run server
python manage.py runserver
```

**No `.env` file needed for local development!**

### Test Users

If you ran setup with `--with-test-users`, use these credentials:

| Username | Password | Role |
|----------|----------|------|
| partner | partner123 | Partner |
| primary_inspector | primary_inspector123 | Primary Inspector |
| final_inspector | final_inspector123 | Final Inspector |
| staff | staff123 | Staff Executive |

---

## MVP User Roles

| Role | Description |
|------|-------------|
| **Partner** | Submits First Articles and Lots |
| **Primary Inspector** | First FA review + all Lot reviews |
| **Final Inspector** | Final FA review only |
| **Staff** | Dashboard access (executive/finance/operations) |

## Two-Stage FA Workflow

```
Partner submits FA → Primary Inspector → Final Inspector → Approved
                           ↓ reject           ↓ reject
                     Partner notified    Partner notified
```

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
