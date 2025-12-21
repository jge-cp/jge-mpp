from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.views.decorators.http import require_POST


@require_POST
def custom_logout(request):
    """
    Custom logout view - POST only for CSRF protection.
    
    Use a form with CSRF token to logout:
        <form method="post" action="{% url 'accounts:logout' %}">
            {% csrf_token %}
            <button type="submit">Logout</button>
        </form>
    """
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('core:home')
