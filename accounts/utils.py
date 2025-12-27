"""
Utility functions for user profile management.
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

