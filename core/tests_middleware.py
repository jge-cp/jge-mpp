"""
Tests for core/middleware.py

Tests the ProfileMiddleware that injects request.profile.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse

from core.middleware import ProfileMiddleware

User = get_user_model()


class ProfileMiddlewareTests(TestCase):
    """Tests for ProfileMiddleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
        
        # Create a simple get_response callable
        self.get_response = lambda r: HttpResponse('OK')
        
        # Create the middleware instance
        self.middleware = ProfileMiddleware(self.get_response)
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
    
    def test_authenticated_user_gets_profile(self):
        """Authenticated user should have request.profile set."""
        request = self.factory.get('/test/')
        request.user = self.user
        
        self.middleware(request)
        
        self.assertTrue(hasattr(request, 'profile'))
        self.assertIsNotNone(request.profile)
        self.assertEqual(request.profile.user, self.user)
    
    def test_anonymous_user_gets_none(self):
        """Anonymous user should have request.profile set to None."""
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        
        self.middleware(request)
        
        self.assertTrue(hasattr(request, 'profile'))
        self.assertIsNone(request.profile)
    
    def test_profile_is_same_instance(self):
        """Profile should be the actual UserProfile instance."""
        request = self.factory.get('/test/')
        request.user = self.user
        
        self.middleware(request)
        
        # Profile should be the same instance as user.profile
        self.assertIs(request.profile, self.user.profile)
    
    def test_response_passes_through(self):
        """Middleware should not modify the response."""
        request = self.factory.get('/test/')
        request.user = self.user
        
        response = self.middleware(request)
        
        self.assertEqual(response.content, b'OK')
        self.assertEqual(response.status_code, 200)
    
    def test_request_without_user_attribute(self):
        """Request without user attribute should get profile=None."""
        request = self.factory.get('/test/')
        # Don't set request.user
        
        self.middleware(request)
        
        self.assertTrue(hasattr(request, 'profile'))
        self.assertIsNone(request.profile)
    
    def test_multiple_requests_get_correct_profiles(self):
        """Different users should get their own profiles."""
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass2'
        )
        
        # First request
        request1 = self.factory.get('/test/')
        request1.user = self.user
        self.middleware(request1)
        
        # Second request
        request2 = self.factory.get('/test/')
        request2.user = user2
        self.middleware(request2)
        
        # Each request should have correct profile
        self.assertEqual(request1.profile.user.username, 'testuser')
        self.assertEqual(request2.profile.user.username, 'testuser2')

