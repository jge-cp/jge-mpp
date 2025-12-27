# Architecture Patterns

This document describes the DRY patterns and best practices used in the Multicam Partner Portal codebase.

## Table of Contents
1. [Profile Management](#profile-management)
2. [Permission Decorators](#permission-decorators)
3. [Model Managers](#model-managers)
4. [Access Control Helpers](#access-control-helpers)
5. [HTMX Patterns](#htmx-patterns)
6. [When to Use What](#when-to-use-what)

---

## Profile Management

### ProfileMiddleware

The `ProfileMiddleware` automatically injects `request.profile` for all authenticated requests:

```python
# core/middleware.py
class ProfileMiddleware:
    def __call__(self, request):
        if request.user.is_authenticated:
            request.profile = get_or_create_profile(request.user)
        else:
            request.profile = None
        return self.get_response(request)
```

**Usage in views:**
```python
@login_required
def my_view(request):
    profile = request.profile  # Always available for authenticated users
```

### get_or_create_profile

Centralized profile creation/retrieval in `accounts/utils.py`:

```python
from accounts.utils import get_or_create_profile

profile = get_or_create_profile(user)
```

This is the single source of truth for profile creation. Used by:
- `ProfileMiddleware`
- `accounts/decorators.py`
- `accounts/context_processors.py`

---

## Permission Decorators

Located in `accounts/decorators.py`. All decorators:
1. Inject `request.profile` if not already present
2. Check permissions
3. Redirect with error message if unauthorized

### Available Decorators

| Decorator | Allows | Use Case |
|-----------|--------|----------|
| `@partner_required` | Partners only | FA/Lot submission |
| `@inspector_required` | Any inspector + full_admin | Review queues |
| `@primary_inspector_required` | Primary inspector + full_admin | Primary review |
| `@final_inspector_required` | Final inspector + full_admin | Final review |
| `@staff_required` | Staff + full_admin | Staff dashboard |
| `@admin_required` | Any admin user | Admin-only pages |

### Usage Examples

**Basic protection:**
```python
from accounts.decorators import partner_required

@login_required
@partner_required
def fa_submit(request):
    profile = request.profile  # Injected by decorator
    # ... rest of view
```

**Multiple decorators (order matters!):**
```python
@login_required
@can_submit_fa      # Check specific permission
@partner_required   # Check role
def fa_submit(request):
    # ...
```

### When NOT to Use Decorators

Decorators are for **route-level protection** (blocking access entirely). Don't use them when:

1. **Different users see different data** - Use model managers instead:
   ```python
   # DON'T: Use decorator to block, then manually filter
   # DO: Use model manager
   fas = FirstArticleInspection.objects.for_user(profile)
   ```

2. **Complex conditional logic** - Keep in view:
   ```python
   # View needs to check multiple conditions
   if profile.is_primary_inspector() and fa.status == 'pending':
       # allow review
   ```

---

## Model Managers

Located in `inspections/managers.py`. Provide chainable, reusable query methods.

### FirstArticleInspection.objects

| Method | Returns | Description |
|--------|---------|-------------|
| `.for_user(profile)` | QuerySet | Access-controlled FAs |
| `.pending()` | QuerySet | status='pending' |
| `.pending_final()` | QuerySet | status='pending_final' |
| `.pending_any()` | QuerySet | pending OR pending_final |
| `.approved()` | QuerySet | status='approved' |
| `.rejected()` | QuerySet | status='rejected' |
| `.with_related()` | QuerySet | Optimized select_related |

### LotAcceptance.objects

| Method | Returns | Description |
|--------|---------|-------------|
| `.for_user(profile)` | QuerySet | Access-controlled Lots |
| `.pending()` | QuerySet | status='pending' |
| `.approved()` | QuerySet | status='approved' |
| `.rejected()` | QuerySet | status='rejected' |
| `.with_related()` | QuerySet | Optimized select_related |

### Usage Examples

**Simple filtering:**
```python
# Get all pending FAs (for inspectors)
pending_fas = FirstArticleInspection.objects.pending()

# Get FAs visible to current user
my_fas = FirstArticleInspection.objects.for_user(profile)
```

**Chained queries:**
```python
# Get pending FAs for current user with optimized relations
fas = FirstArticleInspection.objects.for_user(profile).pending().with_related()

# Get stats
stats = {
    'pending': FirstArticleInspection.objects.for_user(profile).pending_any().count(),
    'approved': FirstArticleInspection.objects.for_user(profile).approved().count(),
}
```

**In dashboard views:**
```python
# Before (verbose, error-prone):
if profile.company:
    fa_base = FirstArticleInspection.objects.filter(company=profile.company)
else:
    fa_base = FirstArticleInspection.objects.filter(vendor=profile)
fa_stats = {
    'pending': fa_base.filter(status__in=['pending', 'pending_final']).count(),
}

# After (clean, DRY):
fa_stats = {
    'pending': FirstArticleInspection.objects.for_user(profile).pending_any().count(),
}
```

---

## Access Control Helpers

Located in `accounts/utils.py`. For retrieving single objects with access control.

### get_fa_for_user(profile, fai_id)

```python
from accounts.utils import get_fa_for_user

fa = get_fa_for_user(profile, fai_id)
# Raises Http404 if FA doesn't exist or user can't access it
```

**Access rules:**
- Partners: Can only access FAs from their company
- Inspectors/Staff: Can access all FAs

### get_lot_for_user(profile, lot_id)

```python
from accounts.utils import get_lot_for_user

lot = get_lot_for_user(profile, lot_id)
# Raises Http404 if Lot doesn't exist or user can't access it
```

**Access rules:**
- Partners: Can only access Lots from their company
- Inspectors/Staff: Can access all Lots

---

## HTMX Patterns

### Server-Side Event Triggers

When a view needs to trigger client-side updates, use HX-Trigger header:

```python
# notifications/views.py
@login_required
@require_POST
def mark_all_read(request):
    NotificationService.mark_all_as_read(request.user)
    
    if request.headers.get('HX-Request'):
        response = HttpResponse(status=204)
        response['HX-Trigger'] = 'notifications-changed'  # Trigger event
        return response
    
    return redirect('notifications:list')
```

**Client-side listener:**
```html
<span hx-get="{% url 'notifications:badge' %}"
      hx-trigger="load, every 10s, notifications-changed from:body"
      hx-swap="outerHTML">
```

### Queue Badges

Sidebar badges use HTMX for dynamic updates:

```html
<span hx-get="{% url 'inspections:fa_queue_badge_primary' %}"
      hx-trigger="load, every 30s, fa-queue-changed from:body"
      hx-swap="outerHTML">
    {% include 'inspections/_queue_badge.html' with count=0 %}
</span>
```

---

## When to Use What

### Decision Tree

```
Need to protect a route entirely?
├── Yes → Use @decorator
│   └── Need access-controlled data? → Also use model manager
└── No → Use model manager for data filtering

Retrieving a single object by ID?
├── Need access control? → Use get_fa_for_user() or get_lot_for_user()
└── Admin-only view? → Use get_object_or_404() directly

Building a queryset for a list?
├── Need access control? → Start with .for_user(profile)
├── Need status filter? → Chain .pending(), .approved(), etc.
└── Displaying in template? → End with .with_related()
```

### Common Patterns

**Partner submitting FA:**
```python
@login_required
@can_submit_fa
@partner_required
def fa_submit(request):
    profile = request.profile
    # ... form handling
```

**Inspector viewing queue:**
```python
@login_required
@primary_inspector_required
def fa_review_queue_primary(request):
    profile = request.profile
    fas = FirstArticleInspection.objects.pending().with_related()
    # ... render queue
```

**Partner viewing their FAs:**
```python
@login_required
def fa_list(request):
    profile = request.profile
    fas = FirstArticleInspection.objects.for_user(profile).with_related()
    # ... render list
```

**Detail view with access control:**
```python
@login_required
def fa_detail(request, fai_id):
    profile = request.profile
    fa = get_fa_for_user(profile, fai_id)  # Handles 404 and access
    # ... render detail
```

---

## Testing

All patterns have test coverage:

| Module | Test File | Coverage |
|--------|-----------|----------|
| Profile utils | `accounts/tests_utils.py` | get_or_create_profile, access helpers |
| Decorators | `accounts/tests_decorators.py` | All permission decorators |
| Middleware | `core/tests_middleware.py` | ProfileMiddleware |
| Managers | `inspections/tests_managers.py` | for_user, status filters |

Run all architecture tests:
```bash
python manage.py test accounts.tests_utils accounts.tests_decorators core.tests_middleware inspections.tests_managers -v2
```

---

## Code Review Findings

### Views Using Decorators Correctly ✅

| View | File | Decorator |
|------|------|-----------|
| `fa_submit` | `inspections/views.py` | `@partner_required` |
| `fa_resubmit` | `inspections/views.py` | `@partner_required` |
| `lot_submit` | `inspections/views.py` | `@partner_required` |
| `fa_review_queue` | `inspections/views.py` | `@inspector_required` |
| `fa_review_queue_primary` | `inspections/views.py` | `@primary_inspector_required` |
| `fa_review_queue_final` | `inspections/views.py` | `@final_inspector_required` |
| `fa_review` | `inspections/views.py` | `@inspector_required` |
| `lot_review_queue` | `inspections/views.py` | `@primary_inspector_required` |
| `lot_review` | `inspections/views.py` | `@primary_inspector_required` |
| `accounting_reports_queue` | `inspections/views.py` | `@admin_required` |
| `accounting_review` | `inspections/views.py` | `@admin_required` |
| `admin_marketing_queue` | `core/views.py` | `@admin_required` |
| `admin_marketing_process` | `core/views.py` | `@admin_required` |

### Views Using Model Managers / Access Helpers ✅

These views don't need route-level decorators because they use access control at the data level:

| View | Access Control Method |
|------|----------------------|
| `fa_list` | `build_fa_queryset(profile, filters)` |
| `fa_detail` | `get_fa_for_user(profile, fai_id)` |
| `fa_evaluation_history` | `get_fa_for_user(profile, fai_id)` |
| `lot_list` | `build_lot_queryset(profile, filters)` |
| `lot_detail` | `get_lot_for_user(profile, lot_id)` |
| `report_list` | Filters by `partner=profile` |
| `report_detail` | Filters by `partner=profile` |

### Inline Checks That Are Appropriate ✅

Some inline permission checks are appropriate because they determine UI behavior, not route access:

```python
# Determining which filter options to show (UI logic)
submitted_by_options = submitted_by_options_for_partner(profile) if profile.is_partner() else submitted_by_options_for_inspector()

# Determining if action is available (business logic)
can_resubmit = fa.can_resubmit() and profile.is_partner()
can_review = profile.is_primary_inspector() and lot.status == 'pending'
```

---

## File Reference

| File | Purpose |
|------|---------|
| `accounts/utils.py` | Centralized helpers (get_or_create_profile, access helpers) |
| `accounts/decorators.py` | Permission decorators |
| `accounts/context_processors.py` | Template context (profile) |
| `core/middleware.py` | ProfileMiddleware |
| `inspections/managers.py` | Custom model managers |
| `inspections/listing.py` | List filtering and queryset building |

