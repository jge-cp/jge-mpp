# Complete Guide to All Python Files in Multicam Partner Portal

This document explains what every `.py` file does in the project, organized by app/folder.

---

## 📁 Root Level

### `manage.py`
**Purpose**: Django's command-line utility for administrative tasks  
**What it does**: 
- Entry point for all Django management commands (`python manage.py ...`)
- Sets up Django environment and executes commands
- Used for: `runserver`, `migrate`, `createsuperuser`, `test`, etc.

---

## 📁 `config/` - Project Configuration

### `__init__.py`
**Purpose**: Marks folder as Python package (empty file)

### `settings.py`
**Purpose**: Main Django configuration file  
**What it does**:
- **Database**: Configures SQLite (dev) or PostgreSQL (prod) based on `DATABASE_URL`
- **Apps**: Lists all installed Django apps (`accounts`, `inspections`, `core`, etc.)
- **Middleware**: Security, sessions, authentication, HTMX support
- **Static/Media Files**: Where CSS/JS/images are stored and served
- **Email**: Resend SMTP configuration (or console for dev)
- **Templates**: Where HTML templates are located
- **Security**: Secret keys, allowed hosts, CSRF protection
- **Django Unfold**: Admin theme configuration

### `urls.py`
**Purpose**: Main URL routing - maps URLs to views  
**What it does**:
- Routes `/admin/` → Django admin
- Routes `/accounts/` → accounts app URLs
- Routes `/portal/` → inspections and dashboard URLs
- Routes `/notifications/` → notifications app URLs
- Routes `/` → core app (homepage, marketing pages)
- Serves static/media files in development

### `wsgi.py`
**Purpose**: Web Server Gateway Interface for production deployment  
**What it does**: Entry point for production servers (Railway, Heroku, etc.) using WSGI protocol

### `asgi.py`
**Purpose**: Asynchronous Server Gateway Interface  
**What it does**: Entry point for async web servers (future WebSocket support)

### `admin.py`
**Purpose**: Project-level admin configuration (currently just a comment)

---

## 📁 `accounts/` - User Management

### `__init__.py`
**Purpose**: Marks folder as Python package

### `apps.py`
**Purpose**: App configuration  
**What it does**: 
- Registers the accounts app
- Loads signals when Django starts (auto-creates UserProfile)

### `models.py`
**Purpose**: Database models for users  
**What it does**:
- **UserProfile**: Extended user model with:
  - Company information (name, email, address)
  - User roles (`partner`, `admin`)
  - Admin roles (`primary_inspector`, `final_inspector`, `staff_*`, `full_admin`)
  - Permissions (can_submit_fa, can_review_lots, etc.)
  - License information
  - Helper methods: `is_partner()`, `is_primary_inspector()`, `get_dashboard_url()`

### `views.py`
**Purpose**: View functions for user actions  
**What it does**:
- **custom_logout()**: Logs user out and redirects to home

### `urls.py`
**Purpose**: URL routing for accounts app  
**What it does**:
- `/accounts/login/` → Django's built-in LoginView
- `/accounts/logout/` → custom logout view
- Password reset URLs

### `admin.py`
**Purpose**: Django admin interface for users  
**What it does**:
- Customizes User admin to show UserProfile inline
- UserProfile admin with filters, search, permission management
- Action to reset permissions to defaults

### `signals.py`
**Purpose**: Automatic actions when users are created/updated  
**What it does**:
- **create_user_profile()**: Auto-creates UserProfile when User is created
- **sync_technical_email_to_user()**: Syncs email between User and UserProfile

### `decorators.py`
**Purpose**: Permission decorators for views  
**What it does**: Provides decorators to restrict access:
- `@user_type_required(['partner', 'admin'])` - Require specific user types
- `@admin_required` - Require admin access
- `@inspector_required` - Require inspector role
- `@can_submit_fa` - Require FA submission permission
- `@can_review_lots` - Require lot review permission
- And many more...

### `tests.py`
**Purpose**: Automated tests for accounts app  
**What it does**: Tests user creation, permissions, profile creation, etc.

### `management/commands/`
**Purpose**: Custom Django management commands

#### `create_admin.py`
**What it does**: Command to create admin users (`python manage.py create_admin`)

#### `import_printers.py`
**What it does**: Command to import partner/printer data from CSV

#### `setup_test_users.py`
**What it does**: Creates test users for development (partner, primary_inspector, final_inspector, staff)

---

## 📁 `approvals/` - Camouflage Approvals

### `__init__.py`
**Purpose**: Marks folder as Python package

### `apps.py`
**Purpose**: App configuration

### `models.py`
**Purpose**: Database models  
**What it does**:
- **CamouflageApproval**: Links partners with approved camouflage types
- Tracks approval dates, expiry, status, supporting documents

### `views.py`
**Purpose**: View functions (currently empty - placeholder)

### `admin.py`
**Purpose**: Django admin for approvals  
**What it does**: Admin interface to manage camouflage approvals

### `tests.py`
**Purpose**: Tests (currently empty)

---

## 📁 `core/` - Core Data & Marketing Pages

### `__init__.py`
**Purpose**: Marks folder as Python package

### `apps.py`
**Purpose**: App configuration

### `models.py`
**Purpose**: Core data models  
**What it does**:
- **PrinterLevel**: Partner tier levels (Gold, Silver, etc.)
- **CamouflageType**: MultiCam variants (MultiCam, Alpine, Tropic, etc.)
- **VariantColor**: Colors for each variant (for shade matching evaluation)
- **CamouflageFile**: Files associated with camouflage types
- **FileUpload**: Generic file uploads
- **RawMaterialArticle**: RM supplier product articles
- **TechnicalDataSheet**: TDS files for articles
- **MarketingOrder**: FP supplier marketing material orders

### `views.py`
**Purpose**: View functions for marketing pages and supplier features  
**What it does**:
- **Public pages**: `home()`, `about()`, `contact()`, `gallery()`, `patterns()`, `faq()`, `suppliers()`
- **RM Supplier views**: Register articles, upload TDS, view printers, finished products
- **FP Supplier views**: Browse RM library, view suppliers, create marketing orders
- **Admin views**: Process marketing orders

### `urls.py`
**Purpose**: URL routing for core app  
**What it does**: Maps URLs to views (home, about, RM/FP supplier features, marketing orders)

### `admin.py`
**Purpose**: Django admin for core models  
**What it does**: Admin interfaces for camouflage types, variant colors, file uploads, etc.

### `tests.py`
**Purpose**: Tests for core models and public pages

### `management/commands/`
**Purpose**: Custom management commands

#### `load_initial_data.py`
**What it does**: Loads initial camouflage types and printer levels

#### `load_variant_colors.py`
**What it does**: Loads variant colors for all camouflage types (7 colors for MultiCam, 3 for Alpine, etc.)

---

## 📁 `dashboard/` - User Dashboards

### `__init__.py`
**Purpose**: Marks folder as Python package

### `apps.py`
**Purpose**: App configuration

### `models.py`
**Purpose**: Database models (currently empty - dashboards are view-only)

### `views.py`
**Purpose**: Dashboard view functions  
**What it does**:
- **dashboard_router()**: Routes users to correct dashboard based on role
- **partner_dashboard()**: Shows FA/Lot stats, recent submissions for partners
- **inspector_dashboard()**: Shows queues, stats, alerts for Primary/Final Inspectors
- **staff_dashboard()**: High-level stats, trends, yardage for executives/finance/operations
- Legacy redirects for deprecated dashboards

### `urls.py`
**Purpose**: URL routing for dashboards  
**What it does**: Maps dashboard URLs to views

### `admin.py`
**Purpose**: Admin (empty)

### `tests.py`
**Purpose**: Tests dashboard routing and access control

---

## 📁 `inspections/` - FA & Lot Submissions

### `__init__.py`
**Purpose**: Marks folder as Python package

### `apps.py`
**Purpose**: App configuration

### `models.py`
**Purpose**: Database models for inspections  
**What it does**:
- **FirstArticleInspection**: FA submissions with two-stage review
- **FAEvaluation**: Evaluation records (primary/final)
- **FAColorEvaluation**: Color-by-color shade matching ratings
- **LotAcceptance**: Lot submissions (single-stage review)
- **LotEvaluation**: Lot evaluation records
- **LotSampleEvaluation**: Per-sample evaluations within a lot
- **LotSampleColorEvaluation**: Color ratings for each sample
- **MonthlyReport**: Partner monthly production reports
- Shade rating system (0-5 scale with half-steps)

### `views.py`
**Purpose**: View functions for FA/Lot workflows  
**What it does**:
- **Partner views**: Submit FA, submit Lot, view lists/details, resubmit
- **Inspector views**: Review queues (primary/final), review FA/Lot, evaluation forms
- **Staff views**: Accounting reports queue, review reports
- Two-stage FA review process (primary → final)
- Single-stage Lot review (primary only)

### `urls.py`
**Purpose**: URL routing for inspections  
**What it does**: Maps all FA/Lot/report URLs to views

### `forms.py`
**Purpose**: Django forms for submissions and reviews  
**What it does**:
- **FirstArticleInspectionForm**: FA submission form
- **LotAcceptanceForm**: Lot submission form
- **FAEvaluationForm**: FA evaluation form (Pattern, Scale, Spectral)
- **FAColorEvaluationForm**: Color rating form
- **LotEvaluationForm**: Lot evaluation form
- **LotSampleEvaluationForm**: Sample evaluation form
- **MonthlyReportForm**: Monthly report submission form

### `emails.py`
**Purpose**: Email notification functions  
**What it does**: Functions to send notifications:
- `send_fa_submitted_notification()` - FA submitted → Primary Inspector
- `send_fa_pending_final_notification()` - Primary approved → Final Inspector
- `send_fa_approved_notification()` - Final approved → Partner
- `send_fa_rejected_notification()` - Rejected → Partner
- `send_lot_submitted_notification()` - Lot submitted → Primary Inspector
- `send_lot_approved_notification()` - Lot approved → Partner
- `send_lot_rejected_notification()` - Lot rejected → Partner

### `admin.py`
**Purpose**: Django admin for inspections  
**What it does**: Admin interfaces for FAs, Lots, evaluations, reports

### `tests.py`
**Purpose**: Model and view tests

### `tests_workflow.py`
**Purpose**: End-to-end workflow tests (FA/Lot submission → review → approval)

### `management/commands/`
**Purpose**: Custom management commands

#### `create_test_data.py`
**What it does**: Creates test FA and Lot submissions

#### `import_historical_fas.py`
**What it does**: Imports historical FA data from Google Sheets

#### `import_historical_lots.py`
**What it does**: Imports historical Lot data from Google Sheets

#### `verify_migration.py`
**What it does**: Verifies data migration from Google Sheets

---

## 📁 `notifications/` - Notification System

### `__init__.py`
**Purpose**: Marks folder as Python package

### `apps.py`
**Purpose**: App configuration

### `models.py`
**Purpose**: Notification database model  
**What it does**:
- **Notification**: Tracks all notifications (email + in-app)
- Stores recipient, channel, type, title, message, status
- Links to related objects (FA, Lot) via GenericForeignKey
- Tracks read/unread status, sent timestamps, errors

### `views.py`
**Purpose**: Notification view functions  
**What it does**:
- **notification_list()**: Paginated list of all notifications
- **notification_dropdown()**: HTMX endpoint for bell dropdown
- **notification_detail()**: View notification and mark as read
- **mark_notification_read()**: HTMX endpoint to mark as read
- **mark_all_read()**: Mark all notifications as read

### `urls.py`
**Purpose**: URL routing for notifications  
**What it does**: Maps notification URLs to views

### `services.py`
**Purpose**: Notification service class  
**What it does**:
- **NotificationService**: Central service for sending notifications
- `notify()`: Sends email and/or in-app notifications
- `send_email()`: Sends email via Django's mail system
- `get_unread_count()`: Gets unread notification count
- `get_recent_notifications()`: Gets recent notifications
- Helper functions: `get_primary_inspectors()`, `get_final_inspectors()`, `get_staff_users()`

### `context_processors.py`
**Purpose**: Template context processor  
**What it does**: Adds `unread_notification_count` to all template contexts (for bell badge)

### `admin.py`
**Purpose**: Django admin for notifications  
**What it does**: Admin interface to view notification logs, retry failed emails

### `tests.py`
**Purpose**: Tests for notification system

---

## 🔄 How Files Work Together

### Example: FA Submission Flow

1. **User visits** `/portal/fa/submit/`
   - `config/urls.py` routes to `inspections.urls`
   - `inspections/urls.py` routes to `fa_submit` view

2. **View processes form** (`inspections/views.py`)
   - Uses `FirstArticleInspectionForm` from `inspections/forms.py`
   - Creates `FirstArticleInspection` model from `inspections/models.py`
   - Links to `UserProfile` from `accounts/models.py`

3. **Notification sent** (`inspections/emails.py`)
   - Calls `send_fa_submitted_notification()`
   - Uses `NotificationService` from `notifications/services.py`
   - Creates `Notification` model from `notifications/models.py`
   - Sends email via Django mail (configured in `config/settings.py`)

4. **Inspector sees notification**
   - `notifications/context_processors.py` adds unread count to template
   - Bell badge shows count
   - Clicking opens dropdown via `notifications/views.py`

5. **Inspector reviews FA**
   - `inspections/views.py` handles review
   - Updates FA status in `inspections/models.py`
   - Sends next notification via `inspections/emails.py`

---

## 📝 Key Patterns

### Models → Views → Templates
- **Models** (`models.py`): Define database structure
- **Views** (`views.py`): Handle HTTP requests, process data
- **Templates** (`templates/`): Render HTML (not Python, but referenced by views)

### URL Routing
- `config/urls.py`: Main router (includes app URLs)
- Each app's `urls.py`: App-specific routes

### Forms
- `forms.py`: Define form fields and validation
- Views use forms to process user input

### Admin
- `admin.py`: Configure Django admin interface for models

### Signals
- `signals.py`: Automatic actions when models are saved/deleted

### Management Commands
- `management/commands/`: Custom `python manage.py` commands

---

## 🎯 Quick Reference

| File | Purpose |
|------|---------|
| `models.py` | Database structure |
| `views.py` | HTTP request handlers |
| `urls.py` | URL routing |
| `forms.py` | Form definitions |
| `admin.py` | Django admin configuration |
| `signals.py` | Automatic model actions |
| `tests.py` | Automated tests |
| `apps.py` | App configuration |
| `settings.py` | Django project settings |
| `manage.py` | Django command-line utility |

---

This guide covers all Python files in the project. Each file has a specific role in the Django application architecture.



