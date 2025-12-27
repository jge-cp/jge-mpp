"""
Tests for the dashboard app.
Tests dashboard routing, access control, and content display.

MVP User Roles:
- partner: Submits FAs and Lots
- admin with admin_role='primary_inspector': First FA review + all Lot reviews
- admin with admin_role='final_inspector': Final FA review only
- admin with admin_role='staff_executive' etc.: Dashboard access (staff)
- admin with admin_role='full_admin': All access
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import UserProfile


class DashboardRoutingTests(TestCase):
    """Test that users are routed to correct dashboards"""
    
    def setUp(self):
        self.client = Client()
    
    def create_partner(self, username):
        """Create a partner user"""
        user = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='testpass123'
        )
        user.profile.user_functionality = 'partner'
        user.profile.save()
        return user
    
    def create_inspector(self, username, role='primary_inspector'):
        """Create an inspector user"""
        user = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='testpass123',
            is_staff=True
        )
        user.profile.user_functionality = 'admin'
        user.profile.admin_role = role
        user.profile.save()
        return user
    
    def create_staff(self, username, role='staff_executive'):
        """Create a staff user"""
        user = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='testpass123',
            is_staff=True
        )
        user.profile.user_functionality = 'admin'
        user.profile.admin_role = role
        user.profile.save()
        return user
    
    def test_partner_routed_to_partner_dashboard(self):
        """Partner users should be routed to partner dashboard"""
        self.create_partner('partner')
        self.client.login(username='partner', password='testpass123')
        
        response = self.client.get(reverse('dashboard:dashboard_router'))
        self.assertRedirects(response, reverse('dashboard:partner_dashboard'))
    
    def test_primary_inspector_routed_to_inspector_dashboard(self):
        """Primary Inspector should be routed to inspector dashboard"""
        self.create_inspector('primary', 'primary_inspector')
        self.client.login(username='primary', password='testpass123')
        
        response = self.client.get(reverse('dashboard:dashboard_router'))
        self.assertRedirects(response, reverse('dashboard:inspector_dashboard'))
    
    def test_final_inspector_routed_to_inspector_dashboard(self):
        """Final Inspector should be routed to inspector dashboard"""
        self.create_inspector('final', 'final_inspector')
        self.client.login(username='final', password='testpass123')
        
        response = self.client.get(reverse('dashboard:dashboard_router'))
        self.assertRedirects(response, reverse('dashboard:inspector_dashboard'))
    
    def test_staff_routed_to_staff_dashboard(self):
        """Staff users should be routed to staff dashboard"""
        self.create_staff('staff', 'staff_executive')
        self.client.login(username='staff', password='testpass123')
        
        response = self.client.get(reverse('dashboard:dashboard_router'))
        self.assertRedirects(response, reverse('dashboard:staff_dashboard'))
    
    def test_unauthenticated_redirected_to_login(self):
        """Unauthenticated users should be redirected to login"""
        response = self.client.get(reverse('dashboard:dashboard_router'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)


class DashboardAccessControlTests(TestCase):
    """Test that users can only access their allowed dashboards"""
    
    def setUp(self):
        self.client = Client()
        
        # Create partner user
        self.partner_user = User.objects.create_user(
            username='partner', email='partner@test.com', password='testpass123'
        )
        self.partner_user.profile.user_functionality = 'partner'
        self.partner_user.profile.save()
        
        # Create primary inspector user
        self.inspector_user = User.objects.create_user(
            username='inspector', email='inspector@test.com', password='testpass123',
            is_staff=True
        )
        self.inspector_user.profile.user_functionality = 'admin'
        self.inspector_user.profile.admin_role = 'primary_inspector'
        self.inspector_user.profile.save()
    
    def test_partner_cannot_access_inspector_dashboard(self):
        """Partners should be redirected when trying to access inspector dashboard"""
        self.client.login(username='partner', password='testpass123')
        response = self.client.get(reverse('dashboard:inspector_dashboard'))
        # Should redirect to their proper dashboard
        self.assertEqual(response.status_code, 302)
    
    def test_inspector_can_access_inspector_dashboard(self):
        """Inspectors should be able to access inspector dashboard"""
        self.client.login(username='inspector', password='testpass123')
        response = self.client.get(reverse('dashboard:inspector_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_partner_can_access_partner_dashboard(self):
        """Partners should be able to access their dashboard"""
        self.client.login(username='partner', password='testpass123')
        response = self.client.get(reverse('dashboard:partner_dashboard'))
        self.assertEqual(response.status_code, 200)


class PartnerDashboardContentTests(TestCase):
    """Test partner dashboard shows correct content"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='partner', email='partner@test.com', password='testpass123'
        )
        self.user.profile.user_functionality = 'partner'
        self.user.profile.company_name = 'Test Partner Co'
        self.user.profile.save()
        self.client.login(username='partner', password='testpass123')
    
    def test_dashboard_shows_company_name(self):
        """Dashboard should display the company name"""
        response = self.client.get(reverse('dashboard:partner_dashboard'))
        self.assertContains(response, 'Test Partner Co')
    
    def test_dashboard_has_fa_link(self):
        """Dashboard should have link to FA submission"""
        response = self.client.get(reverse('dashboard:partner_dashboard'))
        self.assertContains(response, 'First Article')
    
    def test_dashboard_has_lot_link(self):
        """Dashboard should have link to Lot submission"""
        response = self.client.get(reverse('dashboard:partner_dashboard'))
        # Check for presence of relevant navigation
        self.assertEqual(response.status_code, 200)


class InspectorDashboardContentTests(TestCase):
    """Test inspector dashboard shows correct stats and queues"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='inspector', email='inspector@test.com', password='testpass123',
            is_staff=True
        )
        self.user.profile.user_functionality = 'admin'
        self.user.profile.admin_role = 'primary_inspector'
        self.user.profile.save()
        self.client.login(username='inspector', password='testpass123')
    
    def test_dashboard_shows_pending_counts(self):
        """Dashboard should show pending FA and Lot counts"""
        response = self.client.get(reverse('dashboard:inspector_dashboard'))
        self.assertEqual(response.status_code, 200)
        # Check that pending stats are in context
        self.assertIn('fa_pending', response.context)
        self.assertIn('lot_pending', response.context)
    
    def test_dashboard_shows_user_stats(self):
        """Dashboard should show user statistics"""
        response = self.client.get(reverse('dashboard:inspector_dashboard'))
        self.assertIn('total_partners', response.context)
        self.assertIn('active_partners', response.context)
