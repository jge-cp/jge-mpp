# Accounts App

User authentication, profiles, and permission management.

## Philosophy

**ALWAYS prefer decorators over inline checks:**
```python
# ✅ DO: Use decorator
@login_required
@partner_required
def my_view(request): ...

# ❌ DON'T: Inline permission check
def my_view(request):
    if profile.user_functionality != 'partner':
        return redirect(...)
```

**EXTEND existing helpers vs. new functions:**
- Add to `accounts/utils.py` for access control
- Add to `accounts/decorators.py` for new permissions
- Add methods to `UserProfile` model for role checks

## Role Checking

```python
# Use request.profile (injected by ProfileMiddleware)
profile = request.profile
profile.is_partner()           # Partner user
profile.is_primary_inspector() # Primary Inspector
profile.is_final_inspector()   # Final Inspector
profile.is_any_inspector()     # Any inspector type
profile.is_staff()             # Staff (executive/finance/operations)
```

## Permission Decorators

```python
from accounts.decorators import partner_required, inspector_required

@login_required
@partner_required
def my_view(request):
    profile = request.profile  # Guaranteed to exist
```

**Available decorators:**
- `@partner_required` - Partner users only
- `@inspector_required` - Any inspector type
- `@primary_inspector_required` - Primary Inspector only
- `@final_inspector_required` - Final Inspector only
- `@staff_required` - Staff users only
- `@admin_required` - Any admin user

## Access Control Helpers

```python
from accounts.utils import get_fa_for_user, get_lot_for_user

fa = get_fa_for_user(profile, fai_id)   # Raises 404 if no access
lot = get_lot_for_user(profile, lot_id)  # Raises 404 if no access
```

## Key Files

| File | Purpose |
|------|---------|
| `decorators.py` | Permission decorators |
| `utils.py` | `get_or_create_profile`, access helpers |
| `models.py` | `UserProfile` model with role methods |
| `context_processors.py` | Injects `profile` into templates |

## Patterns

✅ **DO**: Use decorators for route protection
```python
@login_required
@partner_required
def fa_submit(request): ...
```

❌ **DON'T**: Inline permission checks
```python
if profile.user_functionality != 'partner':
    return redirect(...)  # Use decorator instead
```

✅ **DO**: Use `request.profile`
❌ **DON'T**: Use `request.user.profile` (may not exist)

