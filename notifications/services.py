"""
Notification Service - Central service for sending notifications.
Provides a clean API for sending email and in-app notifications.
"""
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.contrib.auth.models import User

from .models import Notification


class NotificationService:
    """
    Service class for creating and sending notifications.
    
    Usage:
        NotificationService.notify(
            recipients=[user1, user2],
            notification_type='fa_submitted',
            title='New First Article',
            message='A new FA has been submitted...',
            related_object=fa,
            channels=['email', 'in_app']
        )
    """
    
    @classmethod
    def notify(cls, recipients, notification_type, title, message, 
               related_object=None, action_url='', channels=None,
               email_subject=None):
        """
        Send notification through specified channels.
        
        Args:
            recipients: User instance, list of Users, or list of email strings
            notification_type: Type of notification (e.g., 'fa_submitted')
            title: Notification title
            message: Notification message body
            related_object: Optional related Django model instance (FA, Lot, etc.)
            action_url: URL to navigate to when notification is clicked
            channels: List of channels ['email', 'in_app']. Default is both.
            email_subject: Custom email subject (defaults to title)
        
        Returns:
            List of created Notification objects
        """
        if channels is None:
            channels = ['email', 'in_app']
        
        # Normalize recipients to list
        if isinstance(recipients, User):
            recipients = [recipients]
        
        # Get content type for related object
        content_type = None
        object_id = None
        if related_object:
            content_type = ContentType.objects.get_for_model(related_object)
            object_id = str(related_object.pk)
        
        notifications = []
        
        for recipient in recipients:
            # Handle both User objects and email strings
            if isinstance(recipient, str):
                # Email-only recipient (no user account)
                if 'email' in channels:
                    notification = cls._create_email_notification(
                        email_to=recipient,
                        notification_type=notification_type,
                        title=title,
                        message=message,
                        email_subject=email_subject or title,
                        content_type=content_type,
                        object_id=object_id,
                        action_url=action_url
                    )
                    notifications.append(notification)
            else:
                # User recipient
                for channel in channels:
                    if channel == 'email' and hasattr(recipient, 'profile') and recipient.profile.technical_email:
                        notification = cls._create_notification(
                            recipient=recipient,
                            channel='email',
                            notification_type=notification_type,
                            title=title,
                            message=message,
                            email_to=recipient.profile.technical_email,
                            email_subject=email_subject or title,
                            content_type=content_type,
                            object_id=object_id,
                            action_url=action_url
                        )
                        notifications.append(notification)
                    elif channel == 'in_app':
                        notification = cls._create_notification(
                            recipient=recipient,
                            channel='in_app',
                            notification_type=notification_type,
                            title=title,
                            message=message,
                            content_type=content_type,
                            object_id=object_id,
                            action_url=action_url
                        )
                        notifications.append(notification)
        
        # Send email notifications immediately
        for notification in notifications:
            if notification.channel == 'email':
                cls.send_email(notification)
            elif notification.channel == 'in_app':
                # In-app notifications are "sent" immediately
                notification.mark_as_sent()
        
        return notifications
    
    @classmethod
    def _create_notification(cls, recipient, channel, notification_type, title, message,
                             email_to='', email_subject='', content_type=None, 
                             object_id=None, action_url=''):
        """Create a notification record"""
        return Notification.objects.create(
            recipient=recipient,
            channel=channel,
            notification_type=notification_type,
            title=title,
            message=message,
            email_to=email_to,
            email_subject=email_subject,
            content_type=content_type,
            object_id=object_id,
            action_url=action_url
        )
    
    @classmethod
    def _create_email_notification(cls, email_to, notification_type, title, message,
                                   email_subject='', content_type=None, object_id=None,
                                   action_url=''):
        """Create an email-only notification (no user account)"""
        # For email-only notifications, we still need a recipient user
        # Use the first superuser or create a system user
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            system_user = User.objects.first()
        
        notification = Notification.objects.create(
            recipient=system_user,  # System placeholder
            channel='email',
            notification_type=notification_type,
            title=title,
            message=message,
            email_to=email_to,
            email_subject=email_subject,
            content_type=content_type,
            object_id=object_id,
            action_url=action_url
        )
        
        # Send immediately
        cls.send_email(notification)
        return notification
    
    @classmethod
    def send_email(cls, notification):
        """
        Send email for a notification and update its status.
        
        Args:
            notification: Notification instance with channel='email'
        """
        if not notification.email_to:
            notification.mark_as_failed('No email address provided')
            return False
        
        try:
            send_mail(
                subject=notification.email_subject or notification.title,
                message=notification.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.email_to],
                fail_silently=False,
            )
            notification.mark_as_sent()
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Email send failed to {notification.email_to}: {e}", exc_info=True)
            notification.mark_as_failed(str(e))
            return False
    
    @classmethod
    def get_unread_count(cls, user):
        """
        Get count of unread in-app notifications for a user.
        
        Args:
            user: User instance
            
        Returns:
            Integer count of unread notifications
        """
        return Notification.objects.filter(
            recipient=user,
            channel='in_app',
            read_at__isnull=True,
            status='sent'
        ).count()
    
    @classmethod
    def get_recent_notifications(cls, user, limit=10):
        """
        Get recent in-app notifications for a user.
        
        Args:
            user: User instance
            limit: Maximum number of notifications to return
            
        Returns:
            QuerySet of Notification objects
        """
        return Notification.objects.filter(
            recipient=user,
            channel='in_app'
        ).select_related('content_type')[:limit]
    
    @classmethod
    def get_all_notifications(cls, user):
        """
        Get all in-app notifications for a user.
        
        Args:
            user: User instance
            
        Returns:
            QuerySet of Notification objects
        """
        return Notification.objects.filter(
            recipient=user,
            channel='in_app'
        ).select_related('content_type')
    
    @classmethod
    def mark_as_read(cls, notification_id, user):
        """
        Mark a specific notification as read.
        
        Args:
            notification_id: ID of notification to mark as read
            user: User who owns the notification
            
        Returns:
            True if successful, False otherwise
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=user
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    @classmethod
    def mark_all_as_read(cls, user):
        """
        Mark all in-app notifications as read for a user.
        
        Args:
            user: User instance
            
        Returns:
            Number of notifications marked as read
        """
        return Notification.objects.filter(
            recipient=user,
            channel='in_app',
            read_at__isnull=True
        ).update(
            read_at=timezone.now(),
            status='read'
        )


# Helper functions to get users by role (used by notification senders)
def get_primary_inspectors():
    """Get all active Primary Inspector users"""
    from accounts.models import UserProfile
    profiles = UserProfile.objects.filter(
        user_functionality='admin',
        admin_role__in=['primary_inspector', 'full_admin'],
        status='active'
    ).select_related('user')
    return [p.user for p in profiles if p.user]


def get_final_inspectors():
    """Get all active Final Inspector users"""
    from accounts.models import UserProfile
    profiles = UserProfile.objects.filter(
        user_functionality='admin',
        admin_role__in=['final_inspector', 'full_admin'],
        status='active'
    ).select_related('user')
    return [p.user for p in profiles if p.user]


def get_staff_users():
    """Get all active Staff users"""
    from accounts.models import UserProfile
    profiles = UserProfile.objects.filter(
        user_functionality='admin',
        admin_role__in=['staff_executive', 'staff_finance', 'staff_operations', 'full_admin'],
        status='active'
    ).select_related('user')
    return [p.user for p in profiles if p.user]

