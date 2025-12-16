"""
Context processors for notifications.
Adds notification data to all template contexts.
"""


def notifications(request):
    """
    Add unread notification count to template context.
    This enables the notification bell badge across all pages.
    """
    if request.user.is_authenticated:
        from .services import NotificationService
        return {
            'unread_notification_count': NotificationService.get_unread_count(request.user)
        }
    return {'unread_notification_count': 0}

