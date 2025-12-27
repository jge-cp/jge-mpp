"""
Utility functions for user profile management and access control.
Centralizes profile creation and access patterns used across the application.

This module eliminates repeated profile creation/access code scattered across views.
"""
from django.shortcuts import get_object_or_404


def get_or_create_profile(user):
    """
    Get or create a UserProfile for the given user.
    
    This is the single source of truth for profile creation logic.
    Used by middleware, decorators, and views.
    
    Args:
        user: Django User instance (must be authenticated)
        
    Returns:
        UserProfile instance
        
    Example:
        profile = get_or_create_profile(request.user)
    """
    from accounts.models import UserProfile
    
    # Try to get existing profile via related name
    profile = getattr(user, 'profile', None)
    if profile:
        return profile
    
    # Create profile with sensible defaults
    profile = UserProfile.objects.create(
        user=user,
        company_name=user.email.split('@')[0] if '@' in user.email else user.username,
        technical_email=user.email or f"{user.username}@example.com",
        user_functionality='admin' if user.is_staff else 'partner',
    )
    profile.set_default_permissions()
    profile.save()
    
    return profile


# =============================================================================
# Access Control Helpers
# =============================================================================

def get_fa_for_user(profile, fai_id):
    """
    Get a FirstArticleInspection with appropriate access control.
    
    Partners can only access their company's FAs.
    Inspectors/staff can access all FAs.
    
    Args:
        profile: UserProfile instance
        fai_id: The FA ID to retrieve
        
    Returns:
        FirstArticleInspection instance
        
    Raises:
        Http404 if FA not found or access denied
        
    Example:
        fa = get_fa_for_user(profile, fai_id)
    """
    from inspections.models import FirstArticleInspection
    
    if profile.is_partner():
        if profile.company:
            return get_object_or_404(
                FirstArticleInspection, 
                fai_id=fai_id, 
                company=profile.company
            )
        # Fallback for legacy users without company FK
        return get_object_or_404(
            FirstArticleInspection, 
            fai_id=fai_id, 
            vendor=profile
        )
    # Inspectors/staff can see all
    return get_object_or_404(FirstArticleInspection, fai_id=fai_id)


def get_lot_for_user(profile, lot_id):
    """
    Get a LotAcceptance with appropriate access control.
    
    Partners can only access their company's Lots.
    Inspectors/staff can access all Lots.
    
    Args:
        profile: UserProfile instance
        lot_id: The Lot ID to retrieve
        
    Returns:
        LotAcceptance instance
        
    Raises:
        Http404 if Lot not found or access denied
        
    Example:
        lot = get_lot_for_user(profile, lot_id)
    """
    from inspections.models import LotAcceptance
    
    if profile.is_partner():
        if profile.company:
            return get_object_or_404(
                LotAcceptance, 
                lot_id=lot_id, 
                company=profile.company
            )
        # Fallback for legacy users without company FK
        return get_object_or_404(
            LotAcceptance, 
            lot_id=lot_id, 
            vendor=profile
        )
    # Inspectors/staff can see all
    return get_object_or_404(LotAcceptance, lot_id=lot_id)


# =============================================================================
# Statistics Helpers
# =============================================================================

def get_fa_stats(queryset):
    """
    Calculate FA statistics from a queryset.
    
    Args:
        queryset: FirstArticleInspection queryset (pre-filtered by user access)
        
    Returns:
        dict with pending, approved, rejected counts
        
    Example:
        stats = get_fa_stats(FirstArticleInspection.objects.filter(company=company))
    """
    return {
        'pending': queryset.filter(status__in=['pending', 'pending_final']).count(),
        'approved': queryset.filter(status='approved').count(),
        'rejected': queryset.filter(status='rejected').count(),
    }


def get_lot_stats(queryset):
    """
    Calculate Lot statistics from a queryset.
    
    Args:
        queryset: LotAcceptance queryset (pre-filtered by user access)
        
    Returns:
        dict with pending, approved, rejected counts
        
    Example:
        stats = get_lot_stats(LotAcceptance.objects.filter(company=company))
    """
    return {
        'pending': queryset.filter(status='pending').count(),
        'approved': queryset.filter(status='approved').count(),
        'rejected': queryset.filter(status='rejected').count(),
    }
