"""
Context processors for accounts.
Adds user profile data to all template contexts.
"""


def profile(request):
    """
    Add user profile to template context.
    This enables the sidebar to show the correct navigation based on user role.
    
    Note: ProfileMiddleware already sets request.profile, so we just pass it through.
    """
    return {'profile': getattr(request, 'profile', None)}
