"""
Context processors for accounts.
Adds user profile data to all template contexts.
"""


def profile(request):
    """
    Add user profile to template context.
    This enables the sidebar to show the correct navigation based on user role.
    """
    if request.user.is_authenticated:
        user_profile = getattr(request.user, 'profile', None)
        if user_profile is None:
            # Create profile on the fly if it doesn't exist
            from .models import UserProfile
            user_profile, _ = UserProfile.objects.get_or_create(
                user=request.user,
                defaults={
                    'company_name': request.user.email.split('@')[0] if '@' in request.user.email else request.user.username,
                    'technical_email': request.user.email,
                }
            )
        return {'profile': user_profile}
    return {'profile': None}

