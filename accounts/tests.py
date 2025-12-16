"""
Tests for the accounts app.
Tests user creation, profiles, permissions, and MVP user roles.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import UserProfile


class UserProfileCreationTests(TestCase):
    """Test that UserProfile is auto-created with correct defaults"""
    
    def test_profile_created_on_user_creation(self):
        """When a User is created, a UserProfile should be auto-created"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)
    
    def test_staff_user_gets_admin_profile(self):
        """Staff users should get admin user_functionality"""
        user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        self.assertEqual(user.profile.user_functionality, 'admin')
    
    def test_regular_user_gets_partner_profile(self):
        """Regular users should get partner user_functionality by default"""
        user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='testpass123'
        )
        self.assertEqual(user.profile.user_functionality, 'partner')


class MVPUserRoleTests(TestCase):
    """Test MVP user roles: partner, primary_inspector, final_inspector, staff"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile
    
    def test_partner_role(self):
        """Partner users should have correct permissions"""
        self.profile.user_functionality = 'partner'
        self.profile.save()
        
        self.assertTrue(self.profile.is_partner())
        self.assertFalse(self.profile.is_admin())
        self.assertFalse(self.profile.is_any_inspector())
        
        # Partner permissions
        self.assertTrue(self.profile.can_submit_fa)
        self.assertTrue(self.profile.can_submit_lots)
        self.assertTrue(self.profile.can_submit_reports)
        self.assertFalse(self.profile.can_review_fa)
        self.assertFalse(self.profile.can_review_lots)
    
    def test_primary_inspector_role(self):
        """Primary Inspector should be able to review FAs and Lots"""
        self.profile.user_functionality = 'admin'
        self.profile.admin_role = 'primary_inspector'
        self.profile.save()
        
        self.assertTrue(self.profile.is_admin())
        self.assertTrue(self.profile.is_primary_inspector())
        self.assertFalse(self.profile.is_final_inspector())
        self.assertTrue(self.profile.is_any_inspector())
        
        # Primary Inspector permissions
        self.assertTrue(self.profile.can_review_fa)
        self.assertTrue(self.profile.can_review_lots)
    
    def test_final_inspector_role(self):
        """Final Inspector should only review FAs (no lots)"""
        self.profile.user_functionality = 'admin'
        self.profile.admin_role = 'final_inspector'
        self.profile.save()
        
        self.assertTrue(self.profile.is_admin())
        self.assertFalse(self.profile.is_primary_inspector())
        self.assertTrue(self.profile.is_final_inspector())
        self.assertTrue(self.profile.is_any_inspector())
        
        # Final Inspector permissions - can review FA but not lots
        self.assertTrue(self.profile.can_review_fa)
        self.assertFalse(self.profile.can_review_lots)
    
    def test_staff_executive_role(self):
        """Staff Executive should have dashboard access but no review permissions"""
        self.profile.user_functionality = 'admin'
        self.profile.admin_role = 'staff_executive'
        self.profile.save()
        
        self.assertTrue(self.profile.is_admin())
        self.assertTrue(self.profile.is_staff())
        self.assertTrue(self.profile.is_staff_executive())
        self.assertFalse(self.profile.is_any_inspector())
        
        # Staff should not have review permissions
        self.assertFalse(self.profile.can_review_fa)
        self.assertFalse(self.profile.can_review_lots)
    
    def test_full_admin_role(self):
        """Full Admin should have all permissions and be any inspector type"""
        self.profile.user_functionality = 'admin'
        self.profile.admin_role = 'full_admin'
        self.profile.save()
        
        self.assertTrue(self.profile.is_admin())
        self.assertTrue(self.profile.is_primary_inspector())
        self.assertTrue(self.profile.is_final_inspector())
        self.assertTrue(self.profile.is_any_inspector())
        self.assertTrue(self.profile.is_staff())
        
        # Full Admin should have all permissions
        self.assertTrue(self.profile.can_submit_fa)
        self.assertTrue(self.profile.can_review_fa)
        self.assertTrue(self.profile.can_review_lots)
        self.assertTrue(self.profile.can_manage_users)


class DashboardRoutingTests(TestCase):
    """Test that users are routed to correct dashboards based on role"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile
    
    def test_partner_dashboard_url(self):
        """Partners should be routed to partner dashboard"""
        self.profile.user_functionality = 'partner'
        self.profile.save()
        self.assertEqual(self.profile.get_dashboard_url(), 'dashboard:partner_dashboard')
    
    def test_primary_inspector_dashboard_url(self):
        """Primary Inspector should be routed to inspector dashboard"""
        self.profile.user_functionality = 'admin'
        self.profile.admin_role = 'primary_inspector'
        self.profile.save()
        self.assertEqual(self.profile.get_dashboard_url(), 'dashboard:inspector_dashboard')
    
    def test_final_inspector_dashboard_url(self):
        """Final Inspector should be routed to inspector dashboard"""
        self.profile.user_functionality = 'admin'
        self.profile.admin_role = 'final_inspector'
        self.profile.save()
        self.assertEqual(self.profile.get_dashboard_url(), 'dashboard:inspector_dashboard')
    
    def test_staff_dashboard_url(self):
        """Staff should be routed to staff dashboard"""
        self.profile.user_functionality = 'admin'
        self.profile.admin_role = 'staff_executive'
        self.profile.save()
        self.assertEqual(self.profile.get_dashboard_url(), 'dashboard:staff_dashboard')
    
    def test_full_admin_dashboard_url(self):
        """Full Admin should be routed to inspector dashboard"""
        self.profile.user_functionality = 'admin'
        self.profile.admin_role = 'full_admin'
        self.profile.save()
        self.assertEqual(self.profile.get_dashboard_url(), 'dashboard:inspector_dashboard')


class BackwardsCompatibilityTests(TestCase):
    """Test backwards compatibility aliases"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile
    
    def test_is_printer_alias(self):
        """is_printer() should be alias for is_partner()"""
        self.profile.user_functionality = 'partner'
        self.profile.save()
        self.assertTrue(self.profile.is_printer())  # Backwards compat alias
        self.assertTrue(self.profile.is_partner())
    
    def test_is_inspector_alias(self):
        """is_inspector() should be alias for is_any_inspector()"""
        self.profile.user_functionality = 'admin'
        self.profile.admin_role = 'primary_inspector'
        self.profile.save()
        self.assertTrue(self.profile.is_inspector())  # Backwards compat alias
        self.assertTrue(self.profile.is_any_inspector())


class LastAdminProtectionTests(TestCase):
    """Test that the last admin cannot be demoted"""
    
    def test_cannot_remove_last_admin(self):
        """Should raise error when trying to change last admin to non-admin"""
        from django.core.exceptions import ValidationError
        
        # Create single admin user
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True
        )
        admin_user.profile.user_functionality = 'admin'
        admin_user.profile.save()
        
        # Try to change to partner - should raise error
        admin_user.profile.user_functionality = 'partner'
        with self.assertRaises(ValidationError):
            admin_user.profile.save()
    
    def test_can_remove_admin_if_others_exist(self):
        """Should allow changing admin to non-admin if other admins exist"""
        # Create two admin users
        admin1 = User.objects.create_user(
            username='admin1', email='admin1@example.com', password='testpass123'
        )
        admin1.profile.user_functionality = 'admin'
        admin1.profile.save()
        
        admin2 = User.objects.create_user(
            username='admin2', email='admin2@example.com', password='testpass123'
        )
        admin2.profile.user_functionality = 'admin'
        admin2.profile.save()
        
        # Should be able to change first admin to partner
        admin1.profile.user_functionality = 'partner'
        admin1.profile.save()  # Should not raise
        self.assertEqual(admin1.profile.user_functionality, 'partner')


class AuthenticationTests(TestCase):
    """Test login/logout functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_login_page_loads(self):
        """Login page should be accessible"""
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
    
    def test_successful_login(self):
        """Valid credentials should log user in"""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
    
    def test_failed_login(self):
        """Invalid credentials should show error"""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # Stay on login page
    
    def test_logout(self):
        """Logout should clear session and redirect"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        # User should no longer be authenticated
        response = self.client.get(reverse('dashboard:dashboard_router'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
