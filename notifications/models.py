"""
Notification models for tracking email and in-app notifications.
"""
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


class Notification(models.Model):
    """
    Tracks all notifications sent through the system.
    Supports both email and in-app notification channels.
    """
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('in_app', 'In-App'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    ]
    
    # Notification types for different workflow events
    TYPE_CHOICES = [
        ('fa_submitted', 'First Article Submitted'),
        ('fa_pending_final', 'FA Pending Final Review'),
        ('fa_approved', 'First Article Approved'),
        ('fa_rejected', 'First Article Rejected'),
        ('lot_submitted', 'Lot Submitted'),
        ('lot_approved', 'Lot Approved'),
        ('lot_rejected', 'Lot Rejected'),
        ('report_submitted', 'Report Submitted'),
        ('system', 'System Notification'),
    ]
    
    # Core fields
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    notification_type = models.CharField(
        max_length=50, 
        choices=TYPE_CHOICES,
        db_index=True
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        db_index=True
    )
    
    # Generic foreign key for linking to related objects (FA, Lot, etc.)
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    object_id = models.CharField(max_length=100, null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # URL to navigate to when notification is clicked
    action_url = models.CharField(max_length=500, blank=True)
    
    # Email-specific fields
    email_to = models.EmailField(blank=True)
    email_subject = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking for failed notifications
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'channel', 'status']),
            models.Index(fields=['recipient', 'read_at']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.recipient.username}"
    
    def mark_as_read(self):
        """Mark this notification as read"""
        if not self.read_at:
            self.read_at = timezone.now()
            if self.status == 'sent':
                self.status = 'read'
            self.save(update_fields=['read_at', 'status'])
    
    def mark_as_sent(self):
        """Mark this notification as successfully sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_as_failed(self, error_message=''):
        """Mark this notification as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.retry_count += 1
        self.save(update_fields=['status', 'error_message', 'retry_count'])
    
    @property
    def is_read(self):
        return self.read_at is not None
    
    @property
    def is_email(self):
        return self.channel == 'email'
    
    @property
    def is_in_app(self):
        return self.channel == 'in_app'
