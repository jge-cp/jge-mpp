"""
Custom authentication backend for email or username login.

Allows users to authenticate using either their username or email address.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """
    Authenticate using either username or email address.
    
    Tries username first, then falls back to email (case-insensitive).
    
    Usage:
        Add to settings.py:
        AUTHENTICATION_BACKENDS = ['accounts.backends.EmailOrUsernameBackend']
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        # Try to find user by username first
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Try by email (case-insensitive)
            try:
                user = User.objects.get(email__iexact=username)
            except User.DoesNotExist:
                # No user found with this username or email
                return None
            except User.MultipleObjectsReturned:
                # Multiple users with same email (shouldn't happen but handle it)
                return None
        
        # Check password and return user if valid
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

