from __future__ import annotations

from django.http import HttpRequest, HttpResponse


class NoStoreAuthenticatedHtmlMiddleware:
    """
    Prevent browser/proxy caching for authenticated HTML pages.

    This mitigates stale views caused by the browser back/forward cache and intermediate caches,
    especially important for workflow state (FA/Lot queues, detail pages, notifications).

    We apply to:
    - authenticated users
    - HTML responses (including HTMX fragments)
    - non-streaming responses only
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # Only for authenticated sessions
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return response

        # Only for HTML responses
        content_type = (response.get("Content-Type") or "").lower()
        if "text/html" not in content_type:
            return response

        # Avoid touching streaming responses
        if getattr(response, "streaming", False):
            return response

        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"

        # Fragments vs full pages can differ. Make caches keep them distinct.
        vary = response.get("Vary")
        if vary:
            if "HX-Request" not in vary:
                response["Vary"] = f"{vary}, HX-Request"
        else:
            response["Vary"] = "HX-Request"

        return response


