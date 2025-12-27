"""
Permission decorators for user type and feature-based access control.

MVP Role System:
- Partner: user_functionality='partner' - submits FAs and Lots
- Primary Inspector: user_functionality='admin', admin_role='primary_inspector'
- Final Inspector: user_functionality='admin', admin_role='final_inspector'
- Staff: user_functionality='admin', admin_role in ['staff_executive', 'staff_finance', 'staff_operations']
- Full Admin: user_functionality='admin', admin_role='full_admin'

Usage:
    from accounts.decorators import partner_required, inspector_required
    
    @login_required
    @partner_required
    def my_partner_view(request):
        # request.profile is automatically available
        profile = request.profile
        ...

Note: Always use @login_required before role decorators.
"""
import warnings
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .utils import get_or_create_profile


def _inject_profile(request):
    """
    Inject profile into request if not already present.
    Returns the profile or None if user not authenticated.
    """
    if not request.user.is_authenticated:
        return None
    
    # Check if already injected (by middleware or previous decorator)
    if hasattr(request, 'profile') and request.profile:
        return request.profile
    
    # Get or create and inject
    profile = get_or_create_profile(request.user)
    request.profile = profile
    return profile


def partner_required(view_func):
    """
    Decorator to require partner user type.
    Injects request.profile for use in the view.
    
    Usage:
        @login_required
        @partner_required
        def my_view(request):
            profile = request.profile  # Already available
            ...
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = _inject_profile(request)
        
        if not profile:
            messages.error(request, 'User profile not found.')
            return redirect('accounts:login')
        
        if not profile.is_partner():
            messages.error(request, 'This feature is only available to partners.')
            return redirect('dashboard:dashboard_router')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    """
    Decorator to require admin/staff user type.
    Injects request.profile for use in the view.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = _inject_profile(request)
        
        if not profile or (profile.user_functionality != 'admin' and not request.user.is_staff):
            messages.error(request, 'This feature requires administrator access.')
            return redirect('dashboard:dashboard_router')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def inspector_required(view_func):
    """
    Decorator to require any inspector role (primary or final).
    Injects request.profile for use in the view.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = _inject_profile(request)
        
        if not profile:
            messages.error(request, 'User profile not found.')
            return redirect('accounts:login')
        
        if not profile.is_any_inspector() and profile.admin_role != 'full_admin':
            messages.error(request, 'This feature requires inspector access.')
            return redirect('dashboard:dashboard_router')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def primary_inspector_required(view_func):
    """
    Decorator to require primary inspector role.
    Injects request.profile for use in the view.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = _inject_profile(request)
        
        if not profile:
            messages.error(request, 'User profile not found.')
            return redirect('accounts:login')
        
        if not profile.is_primary_inspector() and profile.admin_role != 'full_admin':
            messages.error(request, 'This feature requires primary inspector access.')
            return redirect('dashboard:dashboard_router')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def final_inspector_required(view_func):
    """
    Decorator to require final inspector role.
    Injects request.profile for use in the view.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = _inject_profile(request)
        
        if not profile:
            messages.error(request, 'User profile not found.')
            return redirect('accounts:login')
        
        if not profile.is_final_inspector() and profile.admin_role != 'full_admin':
            messages.error(request, 'This feature requires final inspector access.')
            return redirect('dashboard:dashboard_router')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def staff_required(view_func):
    """
    Decorator to require staff role (executive, finance, operations).
    Injects request.profile for use in the view.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = _inject_profile(request)
        
        if not profile:
            messages.error(request, 'User profile not found.')
            return redirect('accounts:login')
        
        if not profile.is_staff() and profile.admin_role != 'full_admin':
            messages.error(request, 'This feature requires staff access.')
            return redirect('dashboard:dashboard_router')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def user_type_required(allowed_types):
    """
    Decorator to require specific user types.
    Injects request.profile for use in the view.
    
    Usage:
        @login_required
        @user_type_required(['partner', 'admin'])
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            profile = _inject_profile(request)
            
            if not profile:
                messages.error(request, 'User profile not found.')
                return redirect('accounts:login')
            
            if profile.user_functionality not in allowed_types:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard:dashboard_router')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# =============================================================================
# FEATURE-BASED DECORATORS
# These check specific permission flags on the UserProfile model.
# =============================================================================

def permission_required(permission_flag):
    """
    Decorator to require a specific permission flag.
    Injects request.profile for use in the view.
    
    Usage:
        @login_required
        @permission_required('can_submit_fa')
        def submit_fa_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            profile = _inject_profile(request)
            
            if not profile:
                messages.error(request, 'User profile not found.')
                return redirect('accounts:login')
            
            # Check if user has the required permission flag
            has_permission = getattr(profile, permission_flag, False)
            
            # Admins always have access
            if not has_permission and profile.user_functionality != 'admin':
                messages.error(request, 'You do not have permission to perform this action.')
                return redirect('dashboard:dashboard_router')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def can_submit_fa(view_func):
    """Decorator to check if user can submit FA"""
    return permission_required('can_submit_fa')(view_func)


def can_submit_lots(view_func):
    """Decorator to check if user can submit lots"""
    return permission_required('can_submit_lots')(view_func)


def can_review_fa(view_func):
    """Decorator to check if user can review FA"""
    return permission_required('can_review_fa')(view_func)


def can_review_lots(view_func):
    """Decorator to check if user can review lots"""
    return permission_required('can_review_lots')(view_func)


# =============================================================================
# DEPRECATED DECORATORS
# The following decorators reference user types that were removed from the MVP.
# They are kept for backwards compatibility but will emit deprecation warnings.
# =============================================================================

def _deprecated_decorator(name, replacement=None):
    """Factory for creating deprecated decorator wrappers"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            msg = f"The '{name}' decorator is deprecated and references a removed user type."
            if replacement:
                msg += f" Use '{replacement}' instead."
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            # Fall through to allow the request (to avoid breaking existing code)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def printer_required(view_func):
    """
    DEPRECATED: 'printer' user type was renamed to 'partner'.
    Use @partner_required instead.
    """
    warnings.warn(
        "printer_required is deprecated. Use partner_required instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return partner_required(view_func)


def rm_supplier_required(view_func):
    """
    DEPRECATED: 'rm_supplier' user type was removed from MVP.
    """
    return _deprecated_decorator('rm_supplier_required')(view_func)


def fp_supplier_required(view_func):
    """
    DEPRECATED: 'fp_supplier' user type was removed from MVP.
    """
    return _deprecated_decorator('fp_supplier_required')(view_func)


def accounting_required(view_func):
    """
    DEPRECATED: 'accounting' role was removed from MVP.
    Use @staff_required for general staff access.
    """
    return _deprecated_decorator('accounting_required', 'staff_required')(view_func)
