"""
Tests for the notifications app.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Notification
from .services import NotificationService


class NotificationModelTest(TestCase):
    """Tests for the Notification model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_notification_creation(self):
        """Test creating a notification."""
        notification = Notification.objects.create(
            recipient=self.user,
            channel='in_app',
            notification_type='fa_submitted',
            title='Test Notification',
            message='This is a test message.'
        )
        
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.channel, 'in_app')
        self.assertEqual(notification.status, 'pending')
        self.assertFalse(notification.is_read)
    
    def test_mark_as_read(self):
        """Test marking a notification as read."""
        notification = Notification.objects.create(
            recipient=self.user,
            channel='in_app',
            notification_type='fa_submitted',
            title='Test Notification',
            message='This is a test message.',
            status='sent'
        )
        
        notification.mark_as_read()
        
        self.assertTrue(notification.is_read)
        self.assertEqual(notification.status, 'read')
        self.assertIsNotNone(notification.read_at)


class NotificationServiceTest(TestCase):
    """Tests for the NotificationService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_get_unread_count(self):
        """Test getting unread notification count."""
        # Create some notifications
        for i in range(3):
            Notification.objects.create(
                recipient=self.user,
                channel='in_app',
                notification_type='fa_submitted',
                title=f'Test {i}',
                message='Test',
                status='sent'
            )
        
        # Mark one as read
        Notification.objects.filter(title='Test 0').update(
            status='read',
            read_at='2024-01-01'
        )
        
        count = NotificationService.get_unread_count(self.user)
        self.assertEqual(count, 2)
    
    def test_mark_all_as_read(self):
        """Test marking all notifications as read."""
        for i in range(3):
            Notification.objects.create(
                recipient=self.user,
                channel='in_app',
                notification_type='fa_submitted',
                title=f'Test {i}',
                message='Test',
                status='sent'
            )
        
        count = NotificationService.mark_all_as_read(self.user)
        self.assertEqual(count, 3)
        
        unread = NotificationService.get_unread_count(self.user)
        self.assertEqual(unread, 0)


class NotificationViewTest(TestCase):
    """Tests for notification views."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_notification_list_view(self):
        """Test the notification list view."""
        response = self.client.get(reverse('notifications:list'))
        self.assertEqual(response.status_code, 200)
    
    def test_notification_dropdown_view(self):
        """Test the notification dropdown HTMX endpoint."""
        response = self.client.get(reverse('notifications:dropdown'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Notifications')

    def test_notification_dropdown_shows_mark_all_read_when_unread(self):
        """Dropdown should show 'Mark all read' link when unread notifications exist."""
        Notification.objects.create(
            recipient=self.user,
            channel='in_app',
            notification_type='fa_submitted',
            title='Test',
            message='Test',
            status='sent'
        )
        response = self.client.get(reverse('notifications:dropdown'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mark all read')

    def test_notification_badge_view(self):
        """Test the notification badge HTMX endpoint."""
        Notification.objects.create(
            recipient=self.user,
            channel='in_app',
            notification_type='fa_submitted',
            title='Test',
            message='Test',
            status='sent'
        )
        response = self.client.get(reverse('notifications:badge'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bg-red-500')
    
    def test_mark_all_read_view(self):
        """Test the mark all read view."""
        # Create a notification
        Notification.objects.create(
            recipient=self.user,
            channel='in_app',
            notification_type='fa_submitted',
            title='Test',
            message='Test',
            status='sent'
        )
        
        response = self.client.post(reverse('notifications:mark_all_read'))
        self.assertEqual(response.status_code, 302)  # Redirect
        
        # Verify notification is marked as read
        notification = Notification.objects.first()
        self.assertEqual(notification.status, 'read')
