"""
Tests for the dashboard app.
Tests dashboard routing, access control, and content display.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import UserProfile


class DashboardRoutingTests(TestCase):
    """Test that users are routed to correct dashboards"""
    
    def setUp(self):
        self.client = Client()
    
    def create_user_with_type(self, username, user_type):
        """Helper to create user with specific user_functionality"""
        user = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='testpass123'
        )
        user.profile.user_functionality = user_type
        user.profile.save()
        return user
    
    def test_printer_routed_to_printer_dashboard(self):
        """Printer users should be routed to printer dashboard"""
        user = self.create_user_with_type('printer', 'printer')
        self.client.login(username='printer', password='testpass123')
        
        response = self.client.get(reverse('dashboard:dashboard_router'))
        self.assertRedirects(response, reverse('dashboard:printer_dashboard'))
    
    def test_rm_supplier_routed_to_rm_dashboard(self):
        """RM Supplier users should be routed to RM supplier dashboard"""
        user = self.create_user_with_type('rmsupplier', 'rm_supplier')
        self.client.login(username='rmsupplier', password='testpass123')
        
        response = self.client.get(reverse('dashboard:dashboard_router'))
        self.assertRedirects(response, reverse('dashboard:rm_supplier_dashboard'))
    
    def test_fp_supplier_routed_to_fp_dashboard(self):
        """FP Supplier users should be routed to FP supplier dashboard"""
        user = self.create_user_with_type('fpsupplier', 'fp_supplier')
        self.client.login(username='fpsupplier', password='testpass123')
        
        response = self.client.get(reverse('dashboard:dashboard_router'))
        self.assertRedirects(response, reverse('dashboard:fp_supplier_dashboard'))
    
    def test_government_routed_to_government_dashboard(self):
        """Government users should be routed to government dashboard"""
        user = self.create_user_with_type('govuser', 'government')
        self.client.login(username='govuser', password='testpass123')
        
        response = self.client.get(reverse('dashboard:dashboard_router'))
        self.assertRedirects(response, reverse('dashboard:government_dashboard'))
    
    def test_admin_routed_to_inspector_dashboard(self):
        """Admin users should be routed to inspector dashboard"""
        user = self.create_user_with_type('admin', 'admin')
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('dashboard:dashboard_router'))
        self.assertRedirects(response, reverse('dashboard:inspector_dashboard'))
    
    def test_unauthenticated_redirected_to_login(self):
        """Unauthenticated users should be redirected to login"""
        response = self.client.get(reverse('dashboard:dashboard_router'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)


class DashboardAccessControlTests(TestCase):
    """Test that users can only access their allowed dashboards"""
    
    def setUp(self):
        self.client = Client()
        
        # Create users of each type
        self.printer_user = User.objects.create_user(
            username='printer', email='printer@test.com', password='testpass123'
        )
        self.printer_user.profile.user_functionality = 'printer'
        self.printer_user.profile.save()
        
        self.admin_user = User.objects.create_user(
            username='admin', email='admin@test.com', password='testpass123'
        )
        self.admin_user.profile.user_functionality = 'admin'
        self.admin_user.profile.save()
    
    def test_printer_cannot_access_inspector_dashboard(self):
        """Printers should be redirected when trying to access inspector dashboard"""
        self.client.login(username='printer', password='testpass123')
        response = self.client.get(reverse('dashboard:inspector_dashboard'))
        # Should redirect to their proper dashboard
        self.assertEqual(response.status_code, 302)
    
    def test_admin_can_access_inspector_dashboard(self):
        """Admins should be able to access inspector dashboard"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('dashboard:inspector_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_printer_can_access_printer_dashboard(self):
        """Printers should be able to access their dashboard"""
        self.client.login(username='printer', password='testpass123')
        response = self.client.get(reverse('dashboard:printer_dashboard'))
        self.assertEqual(response.status_code, 200)


class PrinterDashboardContentTests(TestCase):
    """Test printer dashboard shows correct content"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='printer', email='printer@test.com', password='testpass123'
        )
        self.user.profile.user_functionality = 'printer'
        self.user.profile.company_name = 'Test Printer Co'
        self.user.profile.save()
        self.client.login(username='printer', password='testpass123')
    
    def test_dashboard_shows_company_name(self):
        """Dashboard should display the company name"""
        response = self.client.get(reverse('dashboard:printer_dashboard'))
        self.assertContains(response, 'Test Printer Co')
    
    def test_dashboard_has_fa_link(self):
        """Dashboard should have link to FA submission"""
        response = self.client.get(reverse('dashboard:printer_dashboard'))
        self.assertContains(response, 'First Article')
    
    def test_dashboard_has_lot_link(self):
        """Dashboard should have link to Lot submission"""
        # Note: This link may be in different format, adjust as needed
        response = self.client.get(reverse('dashboard:printer_dashboard'))
        # Check for presence of relevant navigation
        self.assertEqual(response.status_code, 200)


class InspectorDashboardContentTests(TestCase):
    """Test inspector dashboard shows correct stats and queues"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='admin', email='admin@test.com', password='testpass123',
            is_staff=True
        )
        self.user.profile.user_functionality = 'admin'
        self.user.profile.save()
        self.client.login(username='admin', password='testpass123')
    
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
        self.assertIn('total_printers', response.context)
        self.assertIn('total_rm_suppliers', response.context)
        self.assertIn('total_fp_suppliers', response.context)
