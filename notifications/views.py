"""
Views for notification management.
Handles listing, viewing, and marking notifications as read.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from .models import Notification
from .services import NotificationService


@login_required
def notification_list(request):
    """Display paginated list of all in-app notifications for the user."""
    notifications_qs = NotificationService.get_all_notifications(request.user)
    paginator = Paginator(notifications_qs, 20)  # 20 per page
    
    page_number = request.GET.get('page', 1)
    notifications = paginator.get_page(page_number)
    
    unread_count = NotificationService.get_unread_count(request.user)
    
    return render(request, 'notifications/list.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required
def notification_dropdown(request):
    """
    HTMX endpoint for the notification dropdown.
    Returns recent notifications for the bell dropdown menu.
    """
    notifications = NotificationService.get_recent_notifications(request.user, limit=5)
    
    return render(request, 'notifications/dropdown.html', {
        'notifications': notifications,
    })


@login_required
def notification_detail(request, notification_id):
    """
    View a specific notification and mark it as read.
    Redirects to the action URL if available.
    """
    notification = get_object_or_404(
        Notification, 
        id=notification_id, 
        recipient=request.user
    )
    
    # Mark as read
    notification.mark_as_read()
    
    # Redirect to action URL if available, otherwise to notification list
    if notification.action_url:
        return redirect(notification.action_url)
    return redirect('notifications:list')


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """
    HTMX endpoint to mark a single notification as read.
    """
    success = NotificationService.mark_as_read(notification_id, request.user)
    
    if request.headers.get('HX-Request'):
        return HttpResponse(status=204)  # No content
    
    return JsonResponse({'success': success})


@login_required
@require_POST
def mark_all_read(request):
    """
    Mark all notifications as read for the current user.
    """
    count = NotificationService.mark_all_as_read(request.user)
    
    if request.headers.get('HX-Request'):
        return HttpResponse(status=204)  # No content
    
    return redirect('notifications:list')
