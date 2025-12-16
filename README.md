# Multicam Partner Portal

Django-based portal for managing the Multicam Partner Program

## Quick Start

```bash
# Setup (one time)
source venv/bin/activate
python manage.py migrate
python manage.py load_initial_data
python manage.py createsuperuser

# Run server
python manage.py runserver
```

Visit: http://localhost:8000

**No `.env` file needed for local development!**

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
MCP-3/
├── config/          # Django settings
├── accounts/        # User auth & profiles
├── inspections/     # FA & Lot workflows
├── dashboard/       # Dashboards
├── core/            # Public pages
├── templates/       # HTML templates
└── Docs/            # All documentation
```

## License

Proprietary - Multicam Partner Program