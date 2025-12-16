"""
Admin configuration for Notifications app.
Provides interface to view notification logs and manage notifications.
"""
from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    """Admin interface for viewing and managing notifications."""
    
    list_display = [
        'id',
        'recipient',
        'notification_type',
        'channel',
        'status',
        'title_preview',
        'email_to',
        'created_at',
        'sent_at',
        'read_at',
    ]
    
    list_filter = [
        'channel',
        'status',
        'notification_type',
        'created_at',
    ]
    
    search_fields = [
        'recipient__username',
        'recipient__email',
        'title',
        'message',
        'email_to',
        'email_subject',
    ]
    
    readonly_fields = [
        'created_at',
        'sent_at',
        'read_at',
        'error_message',
        'retry_count',
    ]
    
    ordering = ['-created_at']
    
    date_hierarchy = 'created_at'
    
    list_per_page = 50
    
    fieldsets = (
        ('Notification Details', {
            'fields': (
                'recipient',
                'channel',
                'notification_type',
                'status',
            )
        }),
        ('Content', {
            'fields': (
                'title',
                'message',
                'action_url',
            )
        }),
        ('Email Details', {
            'fields': (
                'email_to',
                'email_subject',
            ),
            'classes': ('collapse',),
        }),
        ('Related Object', {
            'fields': (
                'content_type',
                'object_id',
            ),
            'classes': ('collapse',),
        }),
        ('Status & Timestamps', {
            'fields': (
                'created_at',
                'sent_at',
                'read_at',
                'error_message',
                'retry_count',
            ),
            'classes': ('collapse',),
        }),
    )
    
    def title_preview(self, obj):
        """Show truncated title."""
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_preview.short_description = 'Title'
    
    def has_add_permission(self, request):
        """Notifications should be created programmatically, not via admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Allow viewing but limit editing."""
        return True
    
    actions = ['mark_as_sent', 'mark_as_failed', 'retry_failed']
    
    @admin.action(description='Mark selected as sent')
    def mark_as_sent(self, request, queryset):
        for notification in queryset:
            notification.mark_as_sent()
        self.message_user(request, f'{queryset.count()} notifications marked as sent.')
    
    @admin.action(description='Mark selected as failed')
    def mark_as_failed(self, request, queryset):
        for notification in queryset:
            notification.mark_as_failed('Manually marked as failed')
        self.message_user(request, f'{queryset.count()} notifications marked as failed.')
    
    @admin.action(description='Retry failed notifications')
    def retry_failed(self, request, queryset):
        from .services import NotificationService
        count = 0
        for notification in queryset.filter(status='failed', channel='email'):
            if NotificationService.send_email(notification):
                count += 1
        self.message_user(request, f'{count} notifications retried successfully.')
