# Dashboard App

Role-based dashboard views and routing.

## Philosophy

**USE model managers for all queries:**
```python
# ✅ DO: Use manager chain
fas = FirstArticleInspection.objects.for_user(profile).pending().with_related()

# ❌ DON'T: Build queryset manually
fas = FirstArticleInspection.objects.filter(...).select_related(...)
```

**REUSE listing helpers:**
- `build_fa_queryset()` / `build_lot_queryset()` from `inspections/listing.py`
- Use `_results.html` partial for HTMX list responses

## Dashboard Routing

The `dashboard_router` view redirects users to their appropriate dashboard:

```python
profile.get_dashboard_url()  # Returns correct dashboard URL
```

| User Type | Dashboard URL |
|-----------|---------------|
| Partner | `/portal/dashboard/partner/` |
| Primary/Final Inspector | `/portal/admin/dashboard/` |
| Staff | `/portal/admin/staff/` |

## Dashboard Views

| View | Users | Content |
|------|-------|---------|
| `partner_dashboard` | Partners | FA/Lot lists, stats, filters |
| `inspector_dashboard` | Inspectors | Review queues, pending counts |
| `staff_dashboard` | Staff | High-level stats, analytics |

## Filter/Sort Patterns

Dashboard views support HTMX filtering:

```python
# Parse filters from request
fa_filters = parse_list_filters(request.GET)

# Build filtered queryset
fas = build_fa_queryset(profile, fa_filters)

# Return partial for HTMX
if request.headers.get('HX-Request'):
    return render(request, 'dashboard/_partner_dashboard_live.html', context)
```

## Key Files

| File | Purpose |
|------|---------|
| `views.py` | Dashboard views with filtering |
| `urls.py` | Dashboard URL routing |

## Templates

- `partner_dashboard.html` - Full page wrapper
- `_partner_dashboard_live.html` - HTMX partial for updates
- `inspector_dashboard.html` / `_inspector_dashboard_live.html`
- `staff_dashboard.html` / `_staff_dashboard_live.html`

