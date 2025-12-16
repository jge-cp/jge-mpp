"""
Permission decorators for user type and feature-based access control.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden


def get_user_profile(user):
    """Helper to get user profile safely"""
    if not user.is_authenticated:
        return None
    return getattr(user, 'profile', None)


def user_type_required(allowed_types):
    """
    Decorator to require specific user types.
    
    Usage:
        @user_type_required(['printer', 'admin'])
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            profile = get_user_profile(request.user)
            
            if not profile:
                messages.error(request, 'User profile not found.')
                return redirect('accounts:login')
            
            if profile.user_functionality not in allowed_types:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard:dashboard_router')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def printer_required(view_func):
    """Decorator to require printer user type"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        
        if not profile:
            messages.error(request, 'User profile not found.')
            return redirect('accounts:login')
        
        if profile.user_functionality != 'printer':
            messages.error(request, 'This feature is only available to print partners.')
            return redirect('dashboard:dashboard_router')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def rm_supplier_required(view_func):
    """Decorator to require RM supplier user type"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        
        if not profile:
            messages.error(request, 'User profile not found.')
            return redirect('accounts:login')
        
        if profile.user_functionality not in ['rm_supplier', 'admin']:
            messages.error(request, 'This feature is only available to RM suppliers.')
            return redirect('dashboard:dashboard_router')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def fp_supplier_required(view_func):
    """Decorator to require FP supplier user type"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        
        if not profile:
            messages.error(request, 'User profile not found.')
            return redirect('accounts:login')
        
        if profile.user_functionality not in ['fp_supplier', 'admin']:
            messages.error(request, 'This feature is only available to FP suppliers.')
            return redirect('dashboard:dashboard_router')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    """Decorator to require admin/staff user type"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        
        if not profile or (profile.user_functionality != 'admin' and not request.user.is_staff):
            messages.error(request, 'This feature requires administrator access.')
            return redirect('dashboard:dashboard_router')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def inspector_required(view_func):
    """Decorator to require inspector role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        
        if not profile:
            messages.error(request, 'User profile not found.')
            return redirect('accounts:login')
        
        if not profile.is_inspector() and not request.user.is_staff:
            messages.error(request, 'This feature requires inspector access.')
            return redirect('dashboard:dashboard_router')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def accounting_required(view_func):
    """Decorator to require accounting role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = get_user_profile(request.user)
        
        if not profile:
            messages.error(request, 'User profile not found.')
            return redirect('accounts:login')
        
        if not profile.is_accounting() and not request.user.is_staff:
            messages.error(request, 'This feature requires accounting access.')
            return redirect('dashboard:dashboard_router')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# Feature-based decorators

def permission_required(permission_flag):
    """
    Decorator to require a specific permission flag.
    
    Usage:
        @permission_required('can_submit_fa')
        def submit_fa_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            profile = get_user_profile(request.user)
            
            if not profile:
                messages.error(request, 'User profile not found.')
                return redirect('accounts:login')
            
            # Check if user has the required permission flag
            has_permission = getattr(profile, permission_flag, False)
            
            # Admins and staff always have access
            if not has_permission and not request.user.is_staff and profile.user_functionality != 'admin':
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


def can_submit_reports(view_func):
    """Decorator to check if user can submit reports"""
    return permission_required('can_submit_reports')(view_func)


def can_review_fa(view_func):
    """Decorator to check if user can review FA"""
    return permission_required('can_review_fa')(view_func)


def can_review_lots(view_func):
    """Decorator to check if user can review lots"""
    return permission_required('can_review_lots')(view_func)


def can_register_articles(view_func):
    """Decorator to check if user can register articles"""
    return permission_required('can_register_articles')(view_func)


def can_upload_tds(view_func):
    """Decorator to check if user can upload TDS"""
    return permission_required('can_upload_tds')(view_func)


def can_view_printer_list(view_func):
    """Decorator to check if user can view printer list"""
    return permission_required('can_view_printer_list')(view_func)


def can_browse_rm_library(view_func):
    """Decorator to check if user can browse RM library"""
    return permission_required('can_browse_rm_library')(view_func)


def can_order_marketing(view_func):
    """Decorator to check if user can order marketing"""
    return permission_required('can_order_marketing')(view_func)


def can_manage_users(view_func):
    """Decorator to check if user can manage users"""
    return permission_required('can_manage_users')(view_func)

