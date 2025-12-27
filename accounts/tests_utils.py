"""
Tests for accounts/utils.py

Tests the centralized profile management utility functions.

Note: UserProfile is auto-created by a signal when User is created (see accounts/signals.py).
Tests must account for this behavior.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.models import UserProfile
from accounts.utils import get_or_create_profile

User = get_user_model()


class GetOrCreateProfileTests(TestCase):
    """Tests for get_or_create_profile helper function."""
    
    def test_returns_existing_profile(self):
        """Should return existing profile created by signal."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Signal auto-creates profile - verify it exists
        self.assertTrue(hasattr(user, 'profile'))
        original_profile = user.profile
        
        result = get_or_create_profile(user)
        
        self.assertEqual(result.pk, original_profile.pk)
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)
    
    def test_returns_same_profile_on_multiple_calls(self):
        """Multiple calls should return same profile without creating duplicates."""
        user = User.objects.create_user(
            username='multiuser',
            email='multi@example.com',
            password='testpass123'
        )
        
        result1 = get_or_create_profile(user)
        result2 = get_or_create_profile(user)
        result3 = get_or_create_profile(user)
        
        self.assertEqual(result1.pk, result2.pk)
        self.assertEqual(result2.pk, result3.pk)
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)
    
    def test_signal_creates_profile_with_email_derived_company_name(self):
        """Company name should default to email prefix (via signal)."""
        user = User.objects.create_user(
            username='emailuser',
            email='mycompany@example.com',
            password='testpass123'
        )
        
        result = get_or_create_profile(user)
        
        self.assertEqual(result.company_name, 'mycompany')
    
    def test_signal_creates_profile_with_username_when_no_email(self):
        """Company name should default to username if no email (via signal)."""
        user = User.objects.create_user(
            username='noemailuser',
            email='',
            password='testpass123'
        )
        
        result = get_or_create_profile(user)
        
        self.assertEqual(result.company_name, 'noemailuser')
    
    def test_staff_user_gets_admin_functionality(self):
        """Staff users should get admin user_functionality (via signal)."""
        user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        
        result = get_or_create_profile(user)
        
        self.assertEqual(result.user_functionality, 'admin')
    
    def test_regular_user_gets_partner_functionality(self):
        """Regular users should get partner user_functionality (via signal)."""
        user = User.objects.create_user(
            username='partneruser',
            email='partner@example.com',
            password='testpass123',
            is_staff=False
        )
        
        result = get_or_create_profile(user)
        
        self.assertEqual(result.user_functionality, 'partner')
    
    def test_creates_profile_if_deleted(self):
        """Should create profile if somehow deleted after user creation."""
        user = User.objects.create_user(
            username='deletedprofile',
            email='deleted@example.com',
            password='testpass123'
        )
        # Delete the auto-created profile
        UserProfile.objects.filter(user=user).delete()
        # Refresh user from db to clear cached profile relation
        user.refresh_from_db()
        
        # Now get_or_create_profile should create a new one
        result = get_or_create_profile(user)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.user, user)
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)
    
    def test_default_permissions_set_for_partner(self):
        """Partner users should have submit permissions set by default."""
        user = User.objects.create_user(
            username='permuser',
            email='perm@example.com',
            password='testpass123',
            is_staff=False
        )
        
        result = get_or_create_profile(user)
        
        # Partner users should have submit permissions set by default
        self.assertTrue(result.can_submit_fa)
        self.assertTrue(result.can_submit_lots)
