"""
Tests for accounts/decorators.py

Tests the role-based permission decorators.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpResponse

from accounts.decorators import (
    partner_required,
    inspector_required,
    primary_inspector_required,
    final_inspector_required,
    staff_required,
    admin_required,
    permission_required,
)

User = get_user_model()


def dummy_view(request):
    """Simple view that returns 200 OK"""
    return HttpResponse('OK')


class DecoratorTestMixin:
    """Mixin with common test setup for decorator tests."""
    
    def setUp(self):
        self.factory = RequestFactory()
        
        # Create partner user
        self.partner_user = User.objects.create_user('partner', 'p@test.com', 'pass')
        self.partner_user.profile.user_functionality = 'partner'
        self.partner_user.profile.save()
        
        # Create primary inspector
        self.primary_inspector = User.objects.create_user('primary', 'pi@test.com', 'pass')
        self.primary_inspector.profile.user_functionality = 'admin'
        self.primary_inspector.profile.admin_role = 'primary_inspector'
        self.primary_inspector.profile.save()
        
        # Create final inspector
        self.final_inspector = User.objects.create_user('final', 'fi@test.com', 'pass')
        self.final_inspector.profile.user_functionality = 'admin'
        self.final_inspector.profile.admin_role = 'final_inspector'
        self.final_inspector.profile.save()
        
        # Create staff user
        self.staff_user = User.objects.create_user('staff', 's@test.com', 'pass')
        self.staff_user.profile.user_functionality = 'admin'
        self.staff_user.profile.admin_role = 'staff_executive'
        self.staff_user.profile.save()
        
        # Create full admin
        self.full_admin = User.objects.create_user('admin', 'a@test.com', 'pass')
        self.full_admin.profile.user_functionality = 'admin'
        self.full_admin.profile.admin_role = 'full_admin'
        self.full_admin.profile.save()
    
    def _get_request(self, user):
        """Create a request with the given user and message support."""
        request = self.factory.get('/test/')
        request.user = user
        # Add session and messages support
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        return request


class PartnerRequiredTests(DecoratorTestMixin, TestCase):
    """Tests for @partner_required decorator."""
    
    def test_partner_allowed(self):
        """Partner user should be allowed access."""
        decorated = partner_required(dummy_view)
        request = self._get_request(self.partner_user)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'OK')
    
    def test_inspector_denied(self):
        """Inspector should be denied access."""
        decorated = partner_required(dummy_view)
        request = self._get_request(self.primary_inspector)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_profile_injected(self):
        """Profile should be injected into request."""
        def check_profile_view(request):
            self.assertTrue(hasattr(request, 'profile'))
            self.assertEqual(request.profile.user, request.user)
            return HttpResponse('OK')
        
        decorated = partner_required(check_profile_view)
        request = self._get_request(self.partner_user)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)


class InspectorRequiredTests(DecoratorTestMixin, TestCase):
    """Tests for @inspector_required decorator."""
    
    def test_primary_inspector_allowed(self):
        """Primary inspector should be allowed access."""
        decorated = inspector_required(dummy_view)
        request = self._get_request(self.primary_inspector)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_final_inspector_allowed(self):
        """Final inspector should be allowed access."""
        decorated = inspector_required(dummy_view)
        request = self._get_request(self.final_inspector)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_full_admin_allowed(self):
        """Full admin should be allowed access."""
        decorated = inspector_required(dummy_view)
        request = self._get_request(self.full_admin)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_partner_denied(self):
        """Partner should be denied access."""
        decorated = inspector_required(dummy_view)
        request = self._get_request(self.partner_user)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_staff_denied(self):
        """Staff (non-inspector) should be denied access."""
        decorated = inspector_required(dummy_view)
        request = self._get_request(self.staff_user)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 302)  # Redirect


class PrimaryInspectorRequiredTests(DecoratorTestMixin, TestCase):
    """Tests for @primary_inspector_required decorator."""
    
    def test_primary_inspector_allowed(self):
        """Primary inspector should be allowed access."""
        decorated = primary_inspector_required(dummy_view)
        request = self._get_request(self.primary_inspector)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_full_admin_allowed(self):
        """Full admin should be allowed access."""
        decorated = primary_inspector_required(dummy_view)
        request = self._get_request(self.full_admin)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_final_inspector_denied(self):
        """Final inspector should be denied access."""
        decorated = primary_inspector_required(dummy_view)
        request = self._get_request(self.final_inspector)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 302)


class FinalInspectorRequiredTests(DecoratorTestMixin, TestCase):
    """Tests for @final_inspector_required decorator."""
    
    def test_final_inspector_allowed(self):
        """Final inspector should be allowed access."""
        decorated = final_inspector_required(dummy_view)
        request = self._get_request(self.final_inspector)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_full_admin_allowed(self):
        """Full admin should be allowed access."""
        decorated = final_inspector_required(dummy_view)
        request = self._get_request(self.full_admin)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_primary_inspector_denied(self):
        """Primary inspector should be denied access."""
        decorated = final_inspector_required(dummy_view)
        request = self._get_request(self.primary_inspector)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 302)


class StaffRequiredTests(DecoratorTestMixin, TestCase):
    """Tests for @staff_required decorator."""
    
    def test_staff_allowed(self):
        """Staff user should be allowed access."""
        decorated = staff_required(dummy_view)
        request = self._get_request(self.staff_user)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_full_admin_allowed(self):
        """Full admin should be allowed access."""
        decorated = staff_required(dummy_view)
        request = self._get_request(self.full_admin)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_partner_denied(self):
        """Partner should be denied access."""
        decorated = staff_required(dummy_view)
        request = self._get_request(self.partner_user)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 302)


class PermissionRequiredTests(DecoratorTestMixin, TestCase):
    """Tests for @permission_required decorator."""
    
    def test_partner_with_permission_allowed(self):
        """Partner with required permission should be allowed."""
        self.partner_user.profile.can_submit_fa = True
        self.partner_user.profile.save()
        
        decorated = permission_required('can_submit_fa')(dummy_view)
        request = self._get_request(self.partner_user)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_partner_without_permission_denied(self):
        """Partner without required permission should be denied."""
        self.partner_user.profile.can_submit_fa = False
        self.partner_user.profile.save()
        
        decorated = permission_required('can_submit_fa')(dummy_view)
        request = self._get_request(self.partner_user)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 302)
    
    def test_admin_always_allowed(self):
        """Admin users should always be allowed regardless of permission flag."""
        decorated = permission_required('can_submit_fa')(dummy_view)
        request = self._get_request(self.primary_inspector)
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)


class ProfileInjectionTests(DecoratorTestMixin, TestCase):
    """Tests that decorators properly inject request.profile."""
    
    def test_profile_available_after_decorator(self):
        """request.profile should be available in the view."""
        profile_found = []
        
        def capture_profile_view(request):
            profile_found.append(hasattr(request, 'profile'))
            profile_found.append(request.profile.user.username)
            return HttpResponse('OK')
        
        decorated = partner_required(capture_profile_view)
        request = self._get_request(self.partner_user)
        
        decorated(request)
        
        self.assertTrue(profile_found[0])
        self.assertEqual(profile_found[1], 'partner')
    
    def test_profile_not_duplicated_if_already_present(self):
        """If request.profile already exists, should not recreate."""
        def check_same_profile_view(request):
            # Profile should be the same object
            self.assertIs(request.profile, request.user.profile)
            return HttpResponse('OK')
        
        decorated = partner_required(check_same_profile_view)
        request = self._get_request(self.partner_user)
        # Pre-inject profile
        request.profile = self.partner_user.profile
        
        response = decorated(request)
        
        self.assertEqual(response.status_code, 200)

