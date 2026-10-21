"""
Middleware to enforce proper cache control for authenticated users and sensitive dashboards.
Prevents browsers from storing and displaying cached protected pages when clicking the Back button after logout.
"""

from django.utils.cache import add_never_cache_headers


class NoCacheAuthenticatedMiddleware:
    """
    Applies 'Cache-Control: no-cache, no-store, must-revalidate, max-age=0'
    to responses for authenticated sessions and protected path prefixes.
    """

    PROTECTED_PREFIXES = (
        "/admin-portal/",
        "/providers/",
        "/marketplace/dashboard/",
        "/marketplace/orders/",
        "/marketplace/checkout/",
        "/marketplace/payment/",
        "/users/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Apply no-cache headers if user is authenticated or visiting protected sections
        is_authenticated = bool(hasattr(request, "user") and request.user.is_authenticated)
        is_protected_path = request.path_info.startswith(self.PROTECTED_PREFIXES)

        if is_authenticated or is_protected_path:
            add_never_cache_headers(response)
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        return response
