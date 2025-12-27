"""
Context processors for accounts.
Adds user profile data to all template contexts.
"""
from accounts.utils import get_or_create_profile


def profile(request):
    """
    Add user profile to template context.
    This enables the sidebar to show the correct navigation based on user role.
    """
    if request.user.is_authenticated:
        return {'profile': get_or_create_profile(request.user)}
    return {'profile': None}
