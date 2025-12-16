from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def custom_logout(request):
    """
    Custom logout view that accepts GET requests for easier logout links
    """
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('core:home')
