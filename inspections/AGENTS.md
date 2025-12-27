# Inspections App

Core FA and Lot submission workflows, models, and review logic.

## Philosophy

**ALWAYS use model managers for queries:**
```python
# ✅ DO: Use manager methods
fas = FirstArticleInspection.objects.for_user(profile).pending()

# ❌ DON'T: Raw filter queries
fas = FirstArticleInspection.objects.filter(company=profile.company, status='pending')
```

**EXTEND existing code:**
- Add manager methods to `managers.py` vs. new queryset logic in views
- Add fields to existing models vs. new tracking tables
- Add to `emails.py` for new notification types vs. inline email code

**REUSE HTMX partials:**
- `_results.html` for any list with sorting/filtering
- `_list_filters.html` for filter forms
- `_row_table.html` / `_row_card.html` for list items

## Two-Stage FA Workflow

```
Partner submits → pending
    ↓
Primary Inspector reviews
    ↓ approve              ↓ reject
pending_final           rejected
    ↓
Final Inspector reviews
    ↓ approve              ↓ reject
approved                rejected
```

## Status Choices

```python
FA_STATUS_CHOICES = [
    ('pending', 'Pending Primary Review'),
    ('pending_final', 'Pending Final Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]

LOT_STATUS_CHOICES = [
    ('pending', 'Pending Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]
```

## Model Managers

```python
# Access-controlled queries
fas = FirstArticleInspection.objects.for_user(profile)
fas = FirstArticleInspection.objects.pending().with_related()

# Chaining
fas = FirstArticleInspection.objects.for_user(profile).pending_any().with_related()

# Lot queries
lots = LotAcceptance.objects.for_user(profile).pending()
```

**Manager methods:**
- `.for_user(profile)` - Filter by user access
- `.pending()`, `.pending_final()`, `.pending_any()` - Status filters
- `.approved()`, `.rejected()` - Status filters
- `.with_related()` - Optimized queries
- `.get_stats()` - Returns counts dict

## Notification Functions

All in `emails.py`:

| Function | Trigger | Recipients |
|----------|---------|------------|
| `send_fa_submitted_notification(fa)` | FA submitted | Primary Inspector |
| `send_fa_pending_final_notification(fa)` | Primary approved | Final Inspector |
| `send_fa_approved_notification(fa)` | Final approved | Partner |
| `send_fa_rejected_notification(fa)` | Rejected | Partner (+Primary if final) |
| `send_lot_submitted_notification(lot)` | Lot submitted | Primary Inspector |
| `send_lot_approved_notification(lot)` | Approved | Partner |
| `send_lot_rejected_notification(lot)` | Rejected | Partner |

## Key Files

| File | Purpose |
|------|---------|
| `models.py` | FA, Lot, Evaluation models |
| `managers.py` | Custom managers with `for_user()` |
| `views.py` | Submit, list, review views |
| `emails.py` | Notification triggers |
| `forms.py` | Submission forms |
| `listing.py` | Filter/sort helpers |

## Patterns

✅ **DO**: Use model managers for queries
```python
fas = FirstArticleInspection.objects.for_user(profile).pending()
```

❌ **DON'T**: Raw filter queries
```python
fas = FirstArticleInspection.objects.filter(company=profile.company)
```

